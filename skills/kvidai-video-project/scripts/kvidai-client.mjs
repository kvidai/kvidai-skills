#!/usr/bin/env node
// kvidai API client — create project, agent-generate (SSE), poll status, get project.
// Usage: node kvidai-client.mjs <command> [args...]

const BASE_URL = process.env.KVIDAI_BASE_URL ?? 'https://api.kvid.ai';
const API_KEY = process.env.KVIDAI_API_KEY ?? '';

if (!API_KEY) throw new Error('KVIDAI_API_KEY not set');

const log = (...args) => console.error('[kvidai]', ...args);

// ── Project CRUD ──────────────────────────────────────────────────────────────

export async function createProject(name) {
  const r = await fetch(`${BASE_URL}/video-project/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'api-key': API_KEY },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error(`createProject ${r.status}: ${await r.text()}`);
  const d = await r.json();
  const id = d?.data?.id ?? d?.id;
  if (typeof id !== 'number') throw new Error(`No projectId: ${JSON.stringify(d)}`);
  return id;
}

export async function getProject(id) {
  const r = await fetch(`${BASE_URL}/video-project/${id}`, {
    headers: { 'api-key': API_KEY },
  });
  if (!r.ok) throw new Error(`getProject ${r.status}: ${await r.text()}`);
  return r.json();
}

// ── Agent generate (SSE) ──────────────────────────────────────────────────────

export async function agentGenerate(projectId, message, onTool) {
  const r = await fetch(`${BASE_URL}/agent/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'api-key': API_KEY },
    body: JSON.stringify({ projectId, message, chatHistory: [] }),
    signal: AbortSignal.timeout(5 * 60 * 1000),
  });
  if (!r.ok || !r.body) throw new Error(`agentGenerate ${r.status}: ${await r.text()}`);

  const tools = [];
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let event = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    for (const line of dec.decode(value, { stream: true }).split('\n')) {
      if (line.startsWith('event: ')) {
        event = line.slice(7).trim();
        continue;
      }
      if (line.startsWith('data: ')) {
        try {
          const d = JSON.parse(line.slice(6));
          if (event === 'tool_start' && d.toolName) {
            tools.push(d.toolName);
            onTool?.(d.toolName);
          }
        } catch {
          /* non-JSON */
        }
      }
    }
  }
  return tools;
}

// ── Async generation status ───────────────────────────────────────────────────

export async function pollStatus(jobId, { intervalMs = 10_000, timeoutMs = 10 * 60 * 1000 } = {}) {
  const key = API_KEY;
  const start = Date.now();
  while (true) {
    const r = await fetch(`${BASE_URL}/ai/generation/status?jobId=${encodeURIComponent(jobId)}`, {
      headers: { 'api-key': key },
    });
    if (!r.ok) throw new Error(`pollStatus ${r.status}: ${await r.text()}`);
    const data = await r.json();
    const status = String(data?.data?.status ?? data?.status ?? '');
    log(`[${Math.round((Date.now() - start) / 1000)}s] status=${status}`);
    if (/^(completed|done|success|finished)$/i.test(status)) return data;
    if (/^(failed|error)$/i.test(status)) throw new Error(`Generation failed: ${JSON.stringify(data)}`);
    if (Date.now() - start > timeoutMs) throw new Error(`Timeout after ${timeoutMs / 1000}s`);
    await new Promise((res) => setTimeout(res, intervalMs));
  }
}

// ── CLI entry ─────────────────────────────────────────────────────────────────

const [cmd, ...args] = process.argv.slice(2);
switch (cmd) {
  case 'create-project': {
    const id = await createProject(args[0] ?? 'New Project');
    console.log(id);
    break;
  }
  case 'get-project': {
    const data = await getProject(Number(args[0]));
    console.log(JSON.stringify(data, null, 2));
    break;
  }
  case 'agent-generate': {
    const [pid, msg] = args;
    log(`Streaming agent for project ${pid}...`);
    const tools = await agentGenerate(Number(pid), msg ?? '', (t) => log(`  ▸ ${t}`));
    log(`\nDone. Tools: ${tools.join(', ')}`);
    console.log(`https://kvid.ai/en/editor/${pid}`);
    break;
  }
  case 'poll-status': {
    const result = await pollStatus(args[0] ?? '');
    console.log(JSON.stringify(result, null, 2));
    break;
  }
  default:
    console.error('Usage: node kvidai-client.mjs create-project|get-project|agent-generate|poll-status [args]');
    process.exit(1);
}
