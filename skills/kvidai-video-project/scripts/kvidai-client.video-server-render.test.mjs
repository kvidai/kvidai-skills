// Run: node --test skills/kvidai-skills/skills/kvidai-video-project/scripts/kvidai-client.video-server-render.test.mjs
// Spawns the CLI against a local stub HTTP server (no dependencies, no network).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const CLIENT = fileURLToPath(new URL('./kvidai-client.mjs', import.meta.url));
let server;
let baseUrl;
let requests; // recorded requests of the current test
let responder; // (req, body) => { status, json }

before(async () => {
  server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      requests.push({ method: req.method, url: req.url, headers: req.headers, body });
      const { status, json } = responder(req, body);
      res.writeHead(status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(json));
    });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});
after(() => server.close());

function run(args, env = {}) {
  requests = [];
  return new Promise((resolve) => {
    const p = spawn(process.execPath, [CLIENT, ...args], {
      env: { PATH: process.env.PATH, KVIDAI_BASE_URL: baseUrl, KVIDAI_API_KEY: 'test-key', ...env },
    });
    let stdout = '';
    let stderr = '';
    p.stdout.on('data', (c) => (stdout += c));
    p.stderr.on('data', (c) => (stderr += c));
    p.on('close', (code) => resolve({ code, stdout, stderr }));
  });
}

test('video-server-render <projectId> posts projectId to /render with api-key and no codec by default', async () => {
  responder = () => ({ status: 200, json: { success: true, projectId: 260, renderRequestId: 'r1' } });
  const r = await run(['video-server-render', '260']);
  assert.equal(r.code, 0, r.stderr);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].method, 'POST');
  assert.equal(requests[0].url, '/video-server-render');
  assert.equal(requests[0].headers['api-key'], 'test-key');
  assert.match(requests[0].headers['content-type'], /application\/json/);
  assert.deepEqual(JSON.parse(requests[0].body), { projectId: 260 });
  assert.equal(JSON.parse(r.stdout).renderRequestId, 'r1');
});

test('video-server-render --codec vp8 sends the codec', async () => {
  responder = () => ({ status: 200, json: { success: true } });
  const r = await run(['video-server-render', '260', '--codec', 'vp8']);
  assert.equal(r.code, 0, r.stderr);
  assert.deepEqual(JSON.parse(requests[0].body), { projectId: 260, codec: 'vp8' });
});

test('video-server-render rejects an unknown codec without sending a request', async () => {
  responder = () => ({ status: 200, json: {} });
  const r = await run(['video-server-render', '260', '--codec', 'gif']);
  assert.equal(r.code, 1);
  assert.equal(requests.length, 0);
  assert.match(r.stderr, /codec/);
});

test('video-server-render without projectId prints usage and exits 1', async () => {
  responder = () => ({ status: 200, json: {} });
  const r = await run(['video-server-render']);
  assert.equal(r.code, 1);
  assert.equal(requests.length, 0);
  assert.match(r.stderr, /Usage/);
});

for (const status of [401, 402, 404, 409]) {
  test(`video-server-render maps HTTP ${status} to an error with status and body, exit 1`, async () => {
    responder = () => ({ status, json: { error: `boom-${status}` } });
    const r = await run(['video-server-render', '260']);
    assert.equal(r.code, 1);
    assert.match(r.stderr, new RegExp(`startVideoServerRender ${status}`));
    assert.match(r.stderr, new RegExp(`boom-${status}`));
  });
}

test('video-server-render-status GETs /video-server-render/status?projectId= with api-key and prints JSON', async () => {
  responder = () => ({ status: 200, json: { projectId: 260, status: 'completed', media: { id: 5, url: 'https://x/y.mp4' } } });
  const r = await run(['video-server-render-status', '260']);
  assert.equal(r.code, 0, r.stderr);
  assert.equal(requests[0].method, 'GET');
  assert.equal(requests[0].url, '/video-server-render/status?projectId=260');
  assert.equal(requests[0].headers['api-key'], 'test-key');
  assert.equal(JSON.parse(r.stdout).media.id, 5);
});

test('video-server-render-status maps non-2xx to an error with status and body', async () => {
  responder = () => ({ status: 404, json: { error: 'no project' } });
  const r = await run(['video-server-render-status', '999']);
  assert.equal(r.code, 1);
  assert.match(r.stderr, /getVideoServerRenderStatus 404/);
  assert.match(r.stderr, /no project/);
});

test('video-server-render --wait polls status until completed and prints the final status JSON', async () => {
  let statusCalls = 0;
  responder = (req) => {
    if (req.method === 'POST') return { status: 200, json: { success: true } };
    statusCalls += 1;
    return statusCalls < 2
      ? { status: 200, json: { projectId: 260, status: 'rendering', progress: 0.5 } }
      : { status: 200, json: { projectId: 260, status: 'completed', media: { id: 5, url: 'u' } } };
  };
  const r = await run(['video-server-render', '260', '--wait'], { KVIDAI_VIDEO_SERVER_RENDER_POLL_INTERVAL_MS: '10' });
  assert.equal(r.code, 0, r.stderr);
  assert.equal(JSON.parse(r.stdout).status, 'completed');
  assert.match(r.stderr, /rendering/);
});

test('video-server-render --wait exits 1 when the render fails', async () => {
  responder = (req) =>
    req.method === 'POST'
      ? { status: 200, json: { success: true } }
      : { status: 200, json: { projectId: 260, status: 'failed', error: 'lambda died' } };
  const r = await run(['video-server-render', '260', '--wait'], { KVIDAI_VIDEO_SERVER_RENDER_POLL_INTERVAL_MS: '10' });
  assert.equal(r.code, 1);
  assert.match(r.stdout + r.stderr, /lambda died/);
});
