// SPDX-License-Identifier: GPL-3.0-only
import { DurableObject } from 'cloudflare:workers';
import Ajv from 'ajv';
import schema from './preset.schema.json';

const validate = new Ajv({ strict: false }).compile(schema);
const SESSION_MS = 12 * 3600_000;
const MAX_BYTES = 512 * 1024;
const MAX_PEERS = 2500;
const keyPattern = /^[a-f0-9]{64}$/;
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', { fatal: true });
const privateHeaders = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };

const json = (body, status = 200) => Response.json(body, { status, headers: privateHeaders });
const fail = (status, error) => json({ error }, status);
const hex = buffer => Array.from(new Uint8Array(buffer), b => b.toString(16).padStart(2, '0')).join('');
const hash = async data => hex(await crypto.subtle.digest('SHA-256', data));
const bearer = request => /^Bearer ([a-f0-9]{64})$/.exec(request.headers.get('Authorization'))?.[1];
const equal = (a, b) => typeof a === 'string' && typeof b === 'string' && a.length === b.length
  && crypto.subtle.timingSafeEqual(encoder.encode(a), encoder.encode(b));

async function sign(key, message) {
  const handle = await crypto.subtle.importKey('raw', encoder.encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return hex(await crypto.subtle.sign('HMAC', handle, encoder.encode(message)));
}

async function readBytes(request, limit) {
  if (Number(request.headers.get('Content-Length')) > limit || !request.body) return null;
  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > limit) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.length;
  }
  return bytes;
}

function parse(bytes) {
  try {
    return JSON.parse(decoder.decode(bytes));
  } catch {
    return null;
  }
}

function validText(text) {
  return typeof text === 'string' && !/[^ \p{L}\p{M}\p{N}\p{P}\p{S}]/u.test(text);
}

function distinct(values) {
  return new Set(values).size === values.length;
}

function validPreset(preset) {
  if (preset?.schema_version !== 3 || !validate(preset) || !validText(preset.name) || !preset.name.trim()) return false;
  const { markers, drawings, calibrated_rings: rings = [], aliases = {}, colors = {} } = preset;
  const published = preset.ring_catalogue?.rings ?? [];
  const uniqueRings = list => distinct(list.map(ring => ring.ring_id))
    && distinct(list.map(ring => ring.default_callsign).filter(Boolean));
  if (!distinct(markers.map(pin => pin.id)) || !distinct(drawings.map(shape => shape.id))
      || !uniqueRings(rings) || !uniqueRings(published)
      || !distinct(published.map(ring => ring.display_code).filter(Boolean))) return false;
  return markers.every(pin => validText(pin.name) && pin.name.trim() && validText(pin.category ?? ''))
    && drawings.every(shape => {
      const dx = Math.abs(shape.end.x - shape.start.x);
      const dy = Math.abs(shape.end.y - shape.start.y);
      return validText(shape.label ?? '') && (shape.kind === 'arrow' ? Math.max(dx, dy) : Math.min(dx, dy)) >= 1e-6;
    })
    && [...rings, ...published].every(ring => {
      const prefix = { MID: 'M', BOT: 'B', TOP: 'T' }[ring.sector];
      return (ring.category === 'siege') === Boolean(prefix)
        && (!ring.default_callsign || ring.default_callsign.startsWith(prefix))
        && [ring.display_name, ring.zone_id, ring.source, ring.position?.source ?? '', ring.geographic_description ?? '']
          .every(text => text.length <= 512 && validText(text));
    })
    && Object.entries(aliases).every(([id, alias]) => /^ring-[a-z0-9-]{1,95}$/.test(id)
      && alias.length <= 36 && alias.trim() && validText(alias))
    && Object.values(colors).every(color => /^#[a-fA-F0-9]{6}$/.test(color));
}

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (request.headers.has('Origin') || url.search) return fail(403, 'origin');
      const { pathname } = url;
      const owner = keyPattern.test(env.LIVE_SYNC_OWNER_KEY || '') ? env.LIVE_SYNC_OWNER_KEY : null;
      const ip = request.headers.get('CF-Connecting-IP') || 'local';
      if (!(await env.CLIENT_LIMIT.limit({ key: ip })).success) return fail(429, 'rate');
      if (pathname === '/v1/health' && request.method === 'GET') {
        return json({ protocol: 1, configured: Boolean(owner), ring_catalogue: 1 });
      }
      const setup = /^\/v1\/setup\/([a-f0-9]{64})$/.exec(pathname);
      if (setup && request.method === 'GET') {
        if (!owner) return fail(503, 'unconfigured');
        if (request.headers.get('Upgrade')?.toLowerCase() !== 'websocket') return fail(426, 'upgrade');
        if (!(await env.OWNER_LIMIT.limit({ key: 'verify:' + ip })).success) return fail(429, 'rate');
        return await env.SESSIONS.getByName('setup-v1').fetch(request);
      }
      const route = /^\/v1\/sessions\/([a-f0-9]{32})(?:\/(snapshot|watch|invite))?$/.exec(pathname);
      if (!route) return fail(404, 'unknown');
      if (!owner) return fail(503, 'unconfigured');
      const [, id, action] = route;
      const session = env.SESSIONS.getByName(id);
      if (!action && request.method === 'POST') {
        const bytes = await readBytes(request, 512);
        const params = bytes && parse(bytes);
        if (!params || typeof params.reader !== 'string' || typeof params.publisher !== 'string'
            || !keyPattern.test(params.reader) || !keyPattern.test(params.publisher)
            || params.reader === params.publisher || !Number.isSafeInteger(params.time)
            || Math.abs(Date.now() - params.time) > 5 * 60_000) return fail(400, 'create');
        const expected = await sign(owner, ['create-v1', id, params.time, params.reader, params.publisher].join(':'));
        if (!equal(bearer(request), expected)) return fail(401, 'key');
        if (!(await env.OWNER_LIMIT.limit({ key: 'create' })).success) return fail(429, 'rate');
        return await session.fetch('https://session.internal/create', {
          method: 'POST',
          body: JSON.stringify([await hash(encoder.encode(params.reader)), await hash(encoder.encode(params.publisher))]),
        });
      }
      if (!bearer(request)) return fail(401, 'key');
      return await session.fetch(request);
    } catch {
      return fail(503, 'infrastructure');
    }
  },
};

export class SiegeSession extends DurableObject {
  get sql() {
    return this.ctx.storage.sql;
  }

  async probe(nonce) {
    this.sql.exec('SELECT 1').one();
    const proof = await sign(this.env.LIVE_SYNC_OWNER_KEY, 'setup-v1:' + nonce);
    const [client, socket] = Object.values(new WebSocketPair());
    this.ctx.acceptWebSocket(socket, ['setup']);
    socket.send(JSON.stringify({ type: 'ready', protocol: 1, proof }));
    socket.close(1000, 'verified');
    return new Response(null, { status: 101, webSocket: client });
  }

  async create(reader, publisher) {
    this.sql.exec('CREATE TABLE IF NOT EXISTS room (id INTEGER PRIMARY KEY, reader TEXT, publisher TEXT, expires INTEGER, version INTEGER DEFAULT 0, hash TEXT, snapshot BLOB, published INTEGER DEFAULT 0)');
    this.hasRoom = true;
    const previous = this.room();
    if (previous && (!equal(previous.publisher, publisher) || !equal(previous.reader, reader))) return fail(409, 'exists');
    if (previous && previous.expires <= Date.now()) return fail(410, 'closed');
    if (!previous) {
      this.sql.exec('INSERT INTO room (id, reader, publisher, expires) VALUES (1, ?, ?, ?)', reader, publisher, Date.now() + SESSION_MS);
    }
    const room = this.room();
    await this.ctx.storage.setAlarm(room.expires);
    return json(this.version(room), previous ? 200 : 201);
  }

  room() {
    this.hasRoom ??= Boolean(this.sql.exec("SELECT 1 FROM sqlite_master WHERE name='room'").toArray().length);
    if (!this.hasRoom) return null;
    return this.sql.exec('SELECT reader, publisher, expires, version, hash, published FROM room WHERE id=1').toArray()[0];
  }

  version(room) {
    return { type: 'version', version: room.version, hash: room.hash, expires: room.expires };
  }

  status(room) {
    return { ...this.version(room), participants: this.connections('player').size };
  }

  connections(role) {
    this.socketIds ??= new Map();
    if (!this.socketIds.has(role)) {
      // After hibernation, rebuild once from the runtime's existing connections.
      const ids = this.ctx.getWebSockets(role)
        .filter(socket => socket.readyState === WebSocket.OPEN)
        .map(socket => socket.deserializeAttachment()?.id)
        .filter(Boolean);
      this.socketIds.set(role, new Set(ids));
    }
    return this.socketIds.get(role);
  }

  releaseSocket(socket) {
    const connection = socket.deserializeAttachment();
    if (connection) this.socketIds?.get(connection.role)?.delete(connection.id);
  }

  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (path === '/create') return this.create(...await request.json());
    if (path.startsWith('/v1/setup/')) return this.probe(path.split('/').at(-1));
    const fingerprint = await hash(encoder.encode(bearer(request)));
    const current = this.room();
    if (!current || current.expires <= Date.now()) return fail(410, 'closed');
    const publisher = equal(fingerprint, current.publisher);
    if (!publisher && !equal(fingerprint, current.reader)) return fail(401, 'key');
    const action = new URL(request.url).pathname.split('/')[4];
    const { method } = request;
    if (method === 'GET') {
      if (!action && publisher) return json(this.status(current));
      if (action === 'watch') return this.watch(request, current, publisher);
      if (action === 'snapshot') return this.snapshot(request, current);
    }
    if (!publisher) return fail(403, 'role');
    if (method === 'PUT' && action === 'snapshot') return this.publish(request);
    if (method === 'PUT' && action === 'invite') {
      const bytes = await readBytes(request, 64);
      const key = bytes && new TextDecoder().decode(bytes);
      if (!keyPattern.test(key || '') || equal(await hash(encoder.encode(key)), fingerprint)) return fail(400, 'key');
      const nextReader = await hash(encoder.encode(key));
      const latest = this.room();
      if (!latest || latest.expires <= Date.now()) return fail(410, 'closed');
      if (!equal(latest.reader, nextReader)) {
        this.sql.exec('UPDATE room SET reader=? WHERE id=1', nextReader);
        this.closeSockets('revoked', ['player']);
      }
      return json(this.status(latest));
    }
    if (method === 'DELETE' && !action) {
      await this.remove();
      return new Response(null, { status: 204, headers: privateHeaders });
    }
    return fail(405, 'method');
  }

  watch(request, room, publisher) {
    if (request.headers.get('Upgrade')?.toLowerCase() !== 'websocket') return fail(426, 'upgrade');
    const role = publisher ? 'host' : 'player';
    const connections = this.connections(role);
    if (connections.size >= (publisher ? 4 : MAX_PEERS)) return fail(429, 'capacity');
    const [client, socket] = Object.values(new WebSocketPair());
    this.ctx.acceptWebSocket(socket, [role]);
    const id = crypto.randomUUID();
    socket.serializeAttachment({ id, role });
    connections.add(id);
    socket.send(JSON.stringify(publisher ? this.status(room) : this.version(room)));
    return new Response(null, { status: 101, webSocket: client });
  }

  snapshot(request, room) {
    const headers = { ...privateHeaders, 'X-Siege-Version': String(room.version) };
    if (!room.version) return new Response(null, { status: 204, headers });
    headers.ETag = '"' + room.hash + '"';
    if (request.headers.get('If-None-Match') === headers.ETag) return new Response(null, { status: 304, headers });
    headers['Content-Type'] = 'application/json; charset=utf-8';
    const { snapshot } = this.sql.exec('SELECT snapshot FROM room WHERE id=1').one();
    return new Response(snapshot, { headers });
  }

  async publish(request) {
    const base = request.headers.get('X-Base-Version');
    if (!/^\d{1,10}$/.test(base ?? '')) return fail(400, 'base');
    const bytes = await readBytes(request, MAX_BYTES);
    if (!bytes) return fail(413, 'size');
    if (!validPreset(parse(bytes))) return fail(422, 'preset');
    const digest = await hash(bytes);
    const room = this.room();
    const now = Date.now();
    if (!room || room.expires <= now) return fail(410, 'closed');
    if (room.hash === digest) return json(this.status(room));
    if (room.version !== Number(base)) return json(this.status(room), 409);
    if (now - room.published < 1500) return fail(429, 'publish_rate');
    this.sql.exec('UPDATE room SET version=version+1, hash=?, snapshot=?, published=? WHERE id=1', digest, bytes.buffer, now);
    const next = this.room();
    const status = this.status(next);
    // Larger rooms spread HTTP snapshot requests over a wider window.
    const spread = status.participants >= 1500 ? 10000 : status.participants >= 750 ? 6500 : 3500;
    const notice = JSON.stringify({ ...this.version(next), spread });
    for (const socket of this.ctx.getWebSockets()) {
      try {
        socket.send(notice);
      } catch {
        // The recipient can recover the current revision on reconnect.
      }
    }
    return json(status);
  }

  closeSockets(type, tags) {
    for (const tag of tags) {
      for (const socket of this.ctx.getWebSockets(tag)) {
        try {
          socket.send(JSON.stringify({ type }));
          socket.close(type === 'revoked' ? 4003 : 4004, type);
        } catch {
          // A disconnected recipient will be rejected on the next request.
        }
      }
    }
  }

  async remove() {
    // Make the room inaccessible before any await, including in-flight publications.
    this.sql.exec('DROP TABLE IF EXISTS room');
    this.hasRoom = false;
    this.closeSockets('closed', ['player', 'host']);
    await this.ctx.storage.deleteAlarm();
  }

  alarm() {
    return this.remove();
  }

  webSocketMessage(socket) {
    socket.close(1008, 'read-only');
  }

  webSocketClose(socket, code, reason) {
    this.releaseSocket(socket);
    // An abnormal close has no live peer to acknowledge.
    if (code !== 1006) socket.close(code, reason);
  }

  webSocketError(socket) {
    this.releaseSocket(socket);
    socket.close(1011, 'socket');
  }
}
