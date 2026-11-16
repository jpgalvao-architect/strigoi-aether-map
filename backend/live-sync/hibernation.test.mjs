// SPDX-License-Identifier: GPL-3.0-only
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { setTimeout as pause } from 'node:timers/promises';
import { startLocalRuntime } from './serve-local.mjs';

test('recover capacity and reuse an open socket after Durable Object eviction', async () => {
  const { runtime, url, name } = await startLocalRuntime();
  process.env.LIVE_SYNC_TEST_URL = url.origin;
  const { http, listen, publish, room, sample } = await import('./local-client.mjs');
  let session;
  let watch;
  try {
    session = await room();
    watch = listen(session.path + '/watch', session.reader);
    assert.equal((await watch.next()).value.version, 0);
    assert.equal((await publish(session, sample('Before eviction'), 0)).status, 200);
    assert.equal((await watch.next()).value.version, 1);
    await runtime.unsafeEvictDurableObject(name, 'SiegeSession', {
      name: session.path.split('/').at(-1), webSockets: 'hibernate',
    });
    const status = async () => (await http(session.path, { key: session.publisher })).json();
    assert.equal((await status()).participants, 1);
    await pause(1550);
    assert.equal((await publish(session, sample('After eviction'), 1)).status, 200);
    assert.equal((await watch.next()).value.version, 2);
    watch.stop();
    for (let attempt = 0; attempt < 30; attempt++) {
      if ((await status()).participants === 0) break;
      await pause(50);
    }
    assert.equal((await status()).participants, 0);
  } finally {
    watch?.stop();
    if (session) await session.close();
    await runtime.dispose();
  }
});
