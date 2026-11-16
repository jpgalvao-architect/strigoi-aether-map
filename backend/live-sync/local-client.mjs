// SPDX-License-Identifier: GPL-3.0-only
import { createHmac, randomBytes } from 'node:crypto';
import WebSocket from 'ws';

export const token = (size = 32) => randomBytes(size).toString('hex');
export const sign = message => createHmac('sha256', 'a'.repeat(64)).update(message).digest('hex');
const origin = process.env.LIVE_SYNC_TEST_URL || 'http://127.0.0.1:8976';
if (!/^http:\/\/127\.0\.0\.1:\d{1,5}$/.test(origin)) throw new Error('Use an isolated loopback Worker.');

export function http(path, { key, method = 'GET', body, headers = {} } = {}) {
  const authorization = key ? { Authorization: 'Bearer ' + key } : {};
  return fetch(origin + path, { method, body, headers: { ...authorization, ...headers },
    redirect: 'error', signal: AbortSignal.timeout(20000) });
}

export function listen(path, key) {
  const headers = key ? { Authorization: 'Bearer ' + key } : {};
  const socket = new WebSocket(origin.replace('http', 'ws') + path, { headers, handshakeTimeout: 20000 });
  const queued = [];
  let pending;
  let terminal;
  const stop = error => {
    terminal = error;
    if (pending) pending.reject(error);
  };
  socket.on('error', stop);
  socket.on('close', () => stop(new Error('Socket closed')));
  socket.on('message', data => {
    const text = data.toString();
    const message = { value: JSON.parse(text), bytes: Buffer.byteLength(text) };
    if (pending) pending.resolve(message);
    else queued.push(message);
  });
  const next = () => {
    if (queued.length) return Promise.resolve(queued.shift());
    if (terminal) return Promise.reject(terminal);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => pending.reject(new Error('WebSocket timeout')), 25000);
      const finish = handler => result => {
        pending = undefined;
        clearTimeout(timer);
        handler(result);
      };
      pending = { resolve: finish(resolve), reject: finish(reject) };
    });
  };
  return { socket, next, stop: () => socket.terminate() };
}

export async function room() {
  const id = token(16);
  const reader = token();
  const publisher = token();
  const time = Date.now();
  const path = '/v1/sessions/' + id;
  const key = sign(['create-v1', id, time, reader, publisher].join(':'));
  const response = await http(path, { key, method: 'POST', body: JSON.stringify({ reader, publisher, time }) });
  if (response.status !== 201) throw new Error('Create returned HTTP ' + response.status);
  return { path, reader, publisher, close: () => http(path, { key: publisher, method: 'DELETE' }) };
}

export function sample(name) {
  const start = { x: 0.3, y: 0.4 };
  const end = { x: 0.4, y: 0.5 };
  return JSON.stringify({
    schema_version: 3, map_id: 'lower-reshanta', name,
    markers: [{ id: 'objective-p1', name: 'P1', position: start }],
    drawings: ['rectangle', 'ellipse', 'arrow'].map(kind => ({ id: 'shape-' + kind, kind, start, end })),
  });
}

export const publish = (session, body, version) => http(session.path + '/snapshot', {
  key: session.publisher, method: 'PUT', body, headers: { 'X-Base-Version': String(version) },
});
