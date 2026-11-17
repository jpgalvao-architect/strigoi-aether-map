// SPDX-License-Identifier: GPL-3.0-only
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { setTimeout as pause } from 'node:timers/promises';
import { http, listen, publish, room, sample, sign, token } from './local-client.mjs';

test('deploy template includes current preset schema and SQLite binding', async () => {
  const read = path => readFile(new URL(path, import.meta.url), 'utf8');
  const sourceSchema = await read('../../schemas/siege-preset.schema.json').catch(error => {
    if (error.code !== 'ENOENT') throw error;
    return null; // The Cloudflare template also runs by itself.
  });
  if (sourceSchema) {
    assert.deepEqual(JSON.parse(await read('./preset.schema.json')), JSON.parse(sourceSchema));
  }
  assert.deepEqual(JSON.parse(await read('./wrangler.jsonc')).migrations[0].new_sqlite_classes, ['SiegeSession']);
});

test('verifies deployed protocol, ownership, Durable Objects, and WSS', async () => {
  const health = await http('/v1/health');
  assert.deepEqual(await health.json(), { protocol: 1, configured: true, ring_catalogue: 1 });
  assert.equal((await http('/v1/health', { headers: { Origin: 'https://example.test' } })).status, 403);
  const nonce = token();
  const watch = listen('/v1/setup/' + nonce);
  try {
    assert.deepEqual((await watch.next()).value, {
      type: 'ready', protocol: 1, proof: sign('setup-v1:' + nonce),
    });
  } finally {
    watch.stop();
  }
});

test('manual publish, read-only peers, validation, reconnect, rotation and close', async t => {
  const session = await room();
  t.after(session.close);
  const { path, reader, publisher } = session;
  const watch = listen(path + '/watch', reader);
  t.after(watch.stop);
  assert.equal((await watch.next()).value.version, 0);
  assert.equal((await http(path + '/snapshot', { key: reader })).status, 204);
  assert.equal((await http(path + '/snapshot', { key: token() })).status, 401);
  assert.equal((await http(path, { key: reader, method: 'DELETE' })).status, 403);
  assert.equal((await http('/v1/sessions/' + token(16), { key: reader, method: 'POST',
    body: JSON.stringify({ reader, publisher, time: Date.now() }) })).status, 401);
  assert.equal((await http(path + '/snapshot', { key: reader, method: 'PUT', body: sample('Fake') })).status, 403);
  assert.equal((await publish(session, '{}', 0)).status, 422);
  assert.equal((await publish(session, 'x'.repeat(512 * 1024 + 1), 0)).status, 413);
  assert.equal((await publish(session, sample('bad\nlabel'), 0)).status, 422);
  const data = sample('First');
  const response = await publish(session, data, 0);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).participants, 1);
  const first = (await watch.next()).value;
  assert.equal(first.version, 1);
  assert.equal(first.hash, createHash('sha256').update(data).digest('hex'));
  const snapshot = await http(path + '/snapshot', { key: reader });
  assert.equal(await snapshot.text(), data);
  assert.equal(snapshot.headers.get('etag'), '"' + first.hash + '"');
  const match = await http(path + '/snapshot', { key: reader, headers: { 'If-None-Match': snapshot.headers.get('etag') } });
  assert.equal(match.status, 304);
  assert.equal((await publish(session, data, 0)).status, 200);
  assert.equal((await publish(session, sample('Stale'), 0)).status, 409);
  assert.equal((await publish(session, sample('Throttled'), 1)).status, 429);
  watch.stop();
  await pause(1550);
  assert.equal((await publish(session, sample('Second'), 1)).status, 200);
  const rejoined = listen(path + '/watch', reader);
  t.after(rejoined.stop);
  assert.equal((await rejoined.next()).value.version, 2);
  const newKey = token();
  assert.equal((await http(path + '/invite', { key: publisher, method: 'PUT', body: newKey })).status, 200);
  assert.equal((await rejoined.next()).value.type, 'revoked');
  assert.equal((await http(path + '/snapshot', { key: reader })).status, 401);
  const revived = listen(path + '/watch', newKey);
  t.after(revived.stop);
  assert.equal((await revived.next()).value.version, 2);
  assert.equal((await session.close()).status, 204);
  assert.equal((await revived.next()).value.type, 'closed');
  assert.equal((await http(path + '/snapshot', { key: newKey })).status, 410);
});

test('rooms reject each other’s reader and publisher credentials', async t => {
  const first = await room();
  t.after(first.close);
  const second = await room();
  t.after(second.close);
  assert.equal((await publish(first, sample('First room'), 0)).status, 200);
  assert.equal((await http(second.path + '/snapshot', { key: first.reader })).status, 401);
  assert.equal((await http(first.path, { key: second.publisher, method: 'DELETE' })).status, 401);
  assert.equal((await http(second.path + '/snapshot', { key: second.reader })).status, 204);
  assert.equal((await http(first.path + '/snapshot', { key: first.reader })).status, 200);
});
