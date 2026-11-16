// SPDX-License-Identifier: GPL-3.0-only
// A direct loopback socket isolates workerd from Wrangler's development proxy and hot reload.
import { Miniflare, convertV4MiniflareOptions } from 'miniflare';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

export async function startLocalRuntime(port = 0) {
  if (!Number.isInteger(port) || (port !== 0 && (port < 1024 || port > 65535))) {
    throw new Error('Invalid loopback port');
  }
  const config = JSON.parse(await readFile(new URL('./wrangler.jsonc', import.meta.url)));
  const bundle = new URL('./.wrangler/bench-bundle/worker.js', import.meta.url);
  const runtime = new Miniflare(convertV4MiniflareOptions({
    host: '127.0.0.1',
    port: 0,
    workers: [{
      name: config.name,
      compatibilityDate: config.compatibility_date,
      modules: [{ type: 'ESModule', path: 'worker.mjs', contents: await readFile(bundle, 'utf8') }],
      bindings: { LIVE_SYNC_OWNER_KEY: 'a'.repeat(64) },
      durableObjects: { SESSIONS: { className: 'SiegeSession', useSQLite: true } },
      ratelimits: Object.fromEntries(config.ratelimits.map(({ name, ...options }) => [name, options])),
      unsafeDirectSockets: [{ host: '127.0.0.1', port, proxy: false }],
    }],
  }));
  await runtime.ready;
  const url = await runtime.unsafeGetDirectURL(config.name);
  return { runtime, url, name: config.name };
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const { runtime, url } = await startLocalRuntime(Number(process.argv[2] || 8977));
  console.log('Direct workerd: ' + url);
  process.on('SIGINT', () => runtime.dispose());
  process.on('SIGTERM', () => runtime.dispose());
}
