// SPDX-License-Identifier: GPL-3.0-only
// A direct loopback socket isolates workerd from Wrangler's development proxy and hot reload.
import { Miniflare, convertV4MiniflareOptions } from 'miniflare';
import { readFile } from 'node:fs/promises';

const config = JSON.parse(await readFile(new URL('./wrangler.jsonc', import.meta.url)));
const port = Number(process.argv[2] || 8977);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid loopback port');
const file = new URL('./.wrangler/bench-bundle/worker.js', import.meta.url);
const runtime = new Miniflare(convertV4MiniflareOptions({
  host: '127.0.0.1',
  port: 0,
  workers: [{
    name: config.name,
    compatibilityDate: config.compatibility_date,
    modules: [{ type: 'ESModule', path: 'worker.mjs', contents: await readFile(file, 'utf8') }],
    bindings: { LIVE_SYNC_OWNER_KEY: 'a'.repeat(64) },
    durableObjects: { SESSIONS: { className: 'SiegeSession', useSQLite: true } },
    ratelimits: Object.fromEntries(config.ratelimits.map(({ name, ...options }) => [name, options])),
    unsafeDirectSockets: [{ host: '127.0.0.1', port, proxy: false }],
  }],
}));
await runtime.ready;
console.log('Direct workerd: ' + await runtime.unsafeGetDirectURL(config.name));
process.on('SIGINT', () => runtime.dispose());
process.on('SIGTERM', () => runtime.dispose());
