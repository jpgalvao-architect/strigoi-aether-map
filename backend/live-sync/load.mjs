// SPDX-License-Identifier: GPL-3.0-only
import { fork } from 'node:child_process';
import { once } from 'node:events';
import { availableParallelism } from 'node:os';
import { performance } from 'node:perf_hooks';
import { setTimeout as pause } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import { http, listen, publish, room, sample } from './local-client.mjs';

const CLOSE_MODE = process.env.LIVE_SYNC_LOAD_CLOSE || 'abrupt';
const RECONNECT_ATTEMPTS = Number(process.env.LIVE_SYNC_LOAD_ATTEMPTS || 3);
const millis = () => performance.timeOrigin + performance.now();

function errorInfo(error) {
  return {
    code: error.code || error.cause?.code || error.name,
    message: error.cause?.message || error.message,
  };
}

function summarize(data) {
  const sorted = data.filter(Number.isFinite).sort((a, b) => a - b);
  const at = fraction => Math.round(sorted[Math.max(0, Math.ceil(sorted.length * fraction) - 1)] ?? 0);
  return { samples: sorted.length, p50: at(.5), p95: at(.95), p99: at(.99), max: at(1) };
}

function cohort() {
  const watches = [];
  const errors = [];
  const retries = [];
  const latency = { publications: [], reconnections: [] };
  const stats = { connected: 0, connectedAtPublish: 0, http: 0, sockets: 0, bytes: 0, lost: 0 };
  let session;
  let players;
  let stride;
  let cpu;
  let utilization;
  async function attempt(phase, fn) {
    try {
      return await fn();
    } catch (error) {
      errors.push({ phase, ...errorInfo(error) });
      return undefined;
    }
  }

  function connect() {
    stats.sockets++;
    const watch = listen(session.path + '/watch', session.reader);
    watch.socket.once('open', () => { watch.established = true; });
    watch.socket.once('close', () => {
      if (watch.established && !watch.deliberate) stats.lost++;
    });
    watches.push(watch);
    return watch;
  }

  async function stop(watch) {
    watch.deliberate = true;
    if (CLOSE_MODE === 'graceful' && watch.socket.readyState === 1) {
      const closed = once(watch.socket, 'close', { signal: AbortSignal.timeout(5000) });
      watch.socket.close(1000);
      await closed;
    } else {
      watch.stop();
    }
  }

  async function notice(watch, expected) {
    const { value, bytes } = await watch.next();
    if (value.version !== expected) throw new Error('Unexpected version ' + value.version);
    stats.bytes += bytes;
    return value;
  }

  return {
    async join(payload) {
      session = payload.session;
      stride = payload.stride;
      cpu = process.cpuUsage();
      utilization = performance.eventLoopUtilization();
      players = (await Promise.all(payload.indices.map(index => attempt('join', async () => {
        await pause(index * stride);
        const watch = connect();
        await notice(watch, 0);
        stats.connected++;
        return { watch, index };
      })))).filter(Boolean);
    },
    async publication({ begin, strategy }) {
      stats.connectedAtPublish = players.filter(({ watch }) => watch.socket.readyState === 1).length;
      await Promise.all(players.map(({ watch }) => attempt('publication', async () => {
        const signal = await notice(watch, 1);
        await pause(150 + Math.floor(Math.random() * ((signal.spread || 3500) - 150)));
        stats.http++;
        const response = await http(session.path + '/snapshot', { key: session.reader });
        const bytes = await response.arrayBuffer();
        if (!response.ok) throw new Error('Fetch returned HTTP ' + response.status);
        stats.bytes += bytes.byteLength;
        if (Buffer.from(bytes).toString() !== strategy) throw new Error('Snapshot differs');
        latency.publications.push(millis() - begin);
      })));
    },
    async reconnect() {
      await Promise.all(players.map(({ watch, index }) => attempt('reconnect', async () => {
        await pause(index * stride);
        const begin = millis();
        await stop(watch);
        for (let attempt = 0; ; attempt++) {
          const window = 4000 * 2 ** attempt;
          await pause(window / 2 + Math.floor(Math.random() * window / 2));
          const replacement = connect();
          try {
            await notice(replacement, 1);
            break;
          } catch (error) {
            replacement.deliberate = true;
            replacement.stop();
            if (attempt + 1 >= RECONNECT_ATTEMPTS) throw error;
            retries.push(errorInfo(error));
          }
        }
        latency.reconnections.push(millis() - begin);
      })));
      const memory = process.resourceUsage().maxRSS;
      return { stats, latency, errors, retries, memory, cpu: process.cpuUsage(cpu),
        eventLoop: performance.eventLoopUtilization(utilization).utilization };
    },
    close() {
      for (const watch of watches) {
        watch.deliberate = true;
        watch.stop();
      }
    },
  };
}

if (process.argv[2] === '--cohort') {
  const clients = cohort();
  process.on('message', async ({ name, payload }) => {
    try {
      process.send({ result: await clients[name](payload) });
    } catch (error) {
      process.send({ failure: errorInfo(error) });
    }
  });
  process.on('disconnect', () => clients.close());
} else {
  const count = Number(process.argv[2] || 100);
  const groups = Number(process.argv[3] || Math.min(4, availableParallelism()));
  const stride = Number(process.env.LIVE_SYNC_LOAD_STRIDE || 5);
  if (![100, 250, 500, 750, 1000, 1500, 2000].includes(count)) throw new Error('Invalid participant count');
  if (!Number.isInteger(groups) || groups < 1 || groups > 8) throw new Error('Use 1 to 8 client processes');
  if (!Number.isInteger(stride) || stride < 1 || stride > 25) throw new Error('Invalid stride');
  if (!['abrupt', 'graceful'].includes(CLOSE_MODE)) throw new Error('Invalid close mode');
  if (![1, 2, 3].includes(RECONNECT_ATTEMPTS)) throw new Error('Use 1 to 3 reconnection attempts');
  const session = await room();
  const credentials = { path: session.path, reader: session.reader };
  const children = Array.from({ length: groups }, () =>
    fork(fileURLToPath(import.meta.url), ['--cohort'], { stdio: ['ignore', 'inherit', 'inherit', 'ipc'] }));
  async function send(child, name, payload) {
    const args = { signal: AbortSignal.timeout(100000) };
    const message = once(child, 'message', args);
    child.send({ name, payload });
    const [{ result, failure }] = await message;
    if (failure) throw new Error(failure.message);
    return result;
  }
  try {
    const indices = Array.from({ length: count }, (_, index) => index);
    await Promise.all(children.map((child, group) =>
      send(child, 'join', { session: credentials, stride, indices: indices.filter(index => index % groups === group) })));
    const strategy = sample('Load test');
    const begin = millis();
    const response = await publish(session, strategy, 0);
    if (!response.ok) throw new Error('Publish returned HTTP ' + response.status);
    const status = await response.json();
    await Promise.all(children.map(child => send(child, 'publication', { begin, strategy })));
    const results = await Promise.all(children.map(child => send(child, 'reconnect')));
    const sum = field => results.reduce((total, result) => total + result.stats[field], 0);
    const errors = results.flatMap(result => result.errors);
    const histogram = {};
    for (const { phase, code, message } of errors) {
      const reason = phase + ' / ' + code + ' / ' + message;
      histogram[reason] = (histogram[reason] || 0) + 1;
    }
    const joins = sum('connected');
    const reconnects = summarize(results.flatMap(result => result.latency.reconnections));
    console.log(JSON.stringify({
      participants: count, generators: groups, strideMs: stride, close: CLOSE_MODE, maxAttempts: RECONNECT_ATTEMPTS,
      connected: joins, connectedAtPublish: sum('connectedAtPublish'), workerCountAtPublish: status.participants,
      failedInitialConnections: count - joins, failedReconnects: joins - reconnects.samples,
      publications: summarize(results.flatMap(result => result.latency.publications)), reconnects,
      httpRequests: sum('http') + 3, webSocketUpgrades: sum('sockets'),
      applicationPayloadBytes: sum('bytes'), unexpectedDisconnects: sum('lost'),
      retryableErrors: Object.fromEntries(Object.entries(Object.groupBy(
        results.flatMap(result => result.retries), error => error.code,
      )).map(([code, failures]) => [code, failures.length])),
      generatorCpuMs: Math.round(results.reduce((total, result) => total + result.cpu.user + result.cpu.system, 0) / 1000),
      maxGeneratorRssKiB: Math.max(...results.map(result => result.memory)),
      maxGeneratorEventLoopUsage: Math.max(...results.map(result => result.eventLoop)),
      errors: histogram,
    }, null, 2));
    if (errors.length || sum('lost')) process.exitCode = 1;
  } finally {
    for (const child of children) if (child.connected) child.disconnect();
    try {
      const response = await session.close();
      if (response.status !== 204) throw new Error('HTTP ' + response.status);
    } catch (error) {
      console.error('Room cleanup failed:', error.message);
      process.exitCode = 1;
    }
  }
}
