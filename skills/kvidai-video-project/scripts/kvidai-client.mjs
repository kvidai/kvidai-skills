#!/usr/bin/env node
// kvidai API client — create project, agent-generate (SSE), poll status, get project.
// Usage: node kvidai-client.mjs <command> [args...]

const BASE_URL = process.env.KVIDAI_BASE_URL ?? 'https://api.kvid.ai';
const API_KEY = process.env.KVIDAI_API_KEY ?? '';

if (!API_KEY) throw new Error('KVIDAI_API_KEY not set');

const log = (...args) => console.error('[kvidai]', ...args);

// ── Project CRUD ──────────────────────────────────────────────────────────────

/**
 * @param {string} name
 * @param {Object} [options]
 * @param {string} [options.presetId]  Preset 의 presetId (e.g. "review-owl"). prod 에 등록된 presetId 사용. 미지정 시 system_default fallback.
 */
export async function createProject(name, options = {}) {
  const { presetId } = options;
  const body = { name };
  if (presetId) body.presetId = presetId;
  const r = await fetch(`${BASE_URL}/video-project/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'api-key': API_KEY },
    body: JSON.stringify(body),
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

/**
 * @param {number}   projectId
 * @param {string}   message
 * @param {Function} [onTool]
 * @param {Object}   [options]
 * @param {string[]} [options.filePaths]      Legacy: 멀티파트 업로드 (서버가 받아서 처리). 큰 파일에는 비효율
 * @param {Array}    [options.attachedFiles]  Recommended: kvidai-media 로 미리 업로드한 cdnUrl 배열.
 *                                            Shape: [{ name, type:'image|video|audio'|'pdf'|'text', mimeType, size, cdnUrl }]
 */
export async function agentGenerate(projectId, message, onTool, options = {}) {
  const { filePaths, attachedFiles } = options;

  let fetchInit;
  if (filePaths?.length) {
    // Legacy multipart 흐름 — kvidai-media presigned 사용을 권장하나 호환성 위해 유지
    const { readFile } = await import('node:fs/promises');
    const { basename } = await import('node:path');
    const fd = new FormData();
    fd.append('data', JSON.stringify({ projectId, message, chatHistory: [] }));
    for (const fp of filePaths) {
      const buf = await readFile(fp);
      fd.append('files', new Blob([buf]), basename(fp));
    }
    // NO Content-Type header — let fetch set multipart boundary automatically
    fetchInit = { method: 'POST', headers: { 'api-key': API_KEY }, body: fd };
  } else {
    const body = { projectId, message, chatHistory: [] };
    if (attachedFiles?.length) body.attachedFiles = attachedFiles;
    fetchInit = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'api-key': API_KEY },
      body: JSON.stringify(body),
    };
  }

  const r = await fetch(`${BASE_URL}/agent/generate`, {
    ...fetchInit,
    signal: AbortSignal.timeout(15 * 60 * 1000),
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

// ── Asset upload ──────────────────────────────────────────────────────────────

/**
 * Upload local files to Strapi via /api/media-management/upload.
 * No JWT required — uses email-based public role endpoint.
 * @param {Object}   opts
 * @param {string[]} opts.filePaths  Absolute or relative paths to local files
 * @param {string}   opts.email      User email (must exist in Strapi DB)
 * @returns {Promise<Array<{id: number, url: string, name: string}>>}
 */
export async function uploadAssets({ filePaths, email }) {
  const { readFile } = await import('node:fs/promises');
  const { basename } = await import('node:path');

  const formData = new FormData();
  formData.append('email', email);
  for (const filePath of filePaths) {
    const buf = await readFile(filePath);
    formData.append('files', new Blob([buf]), basename(filePath));
  }

  const r = await fetch(`${BASE_URL}/api/media-management/upload`, {
    method: 'POST',
    headers: { 'api-key': API_KEY },
    body: formData,
  });
  if (!r.ok) throw new Error(`uploadAssets ${r.status}: ${await r.text()}`);
  const d = await r.json();
  if (!d.success) throw new Error(`uploadAssets failed: ${JSON.stringify(d)}`);
  return d.data.map((f) => ({ id: f.id, url: f.url, name: f.name }));
}

/**
 * Add an asset to a project's composition so the agent can reference it on the timeline.
 * Uses PATCH /video-project/:id/composition with operation "add_asset".
 * @param {number} projectId
 * @param {string} email
 * @param {{ id: string, type: string, remoteUrl: string, [key: string]: any }} asset
 */
export async function addCompositionAsset(projectId, email, asset) {
  const r = await fetch(`${BASE_URL}/video-project/${projectId}/composition`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'api-key': API_KEY },
    body: JSON.stringify({ email, operation: 'add_asset', data: { asset } }),
  });
  if (!r.ok) throw new Error(`addCompositionAsset ${r.status}: ${await r.text()}`);
  return r.json();
}

/**
 * Attach uploaded file IDs to a project's media relation (Strapi morph relation — origin archive).
 * Requires STRAPI_TOKEN (Bearer) env var — the standard /api/video-projects PUT needs auth.
 * Optional: composition.assets is sufficient for the agent; this is for the library/archive side.
 * @param {number}   projectId
 * @param {number[]} fileIds
 */
export async function attachMediaToProject(projectId, fileIds) {
  const token = process.env.STRAPI_TOKEN;
  if (!token) {
    log('STRAPI_TOKEN not set — skipping media field attach (composition.assets is sufficient for agent)');
    return null;
  }
  const r = await fetch(`${BASE_URL}/api/video-projects/${projectId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'api-key': API_KEY,
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ data: { media: fileIds } }),
  });
  if (!r.ok) throw new Error(`attachMediaToProject ${r.status}: ${await r.text()}`);
  return r.json();
}

// ── CLI entry ─────────────────────────────────────────────────────────────────

const [cmd, ...args] = process.argv.slice(2);
switch (cmd) {
  case 'create-project': {
    // usage: node kvidai-client.mjs create-project <name> [--preset-id <presetId>]
    const positional = [];
    const opts = {};
    for (let i = 0; i < args.length; i++) {
      if (args[i] === '--preset-id' || args[i] === '--presetId') opts.presetId = args[++i];
      else positional.push(args[i]);
    }
    const id = await createProject(positional[0] ?? 'New Project', opts);
    console.log(id);
    break;
  }
  case 'get-project': {
    const data = await getProject(Number(args[0]));
    console.log(JSON.stringify(data, null, 2));
    break;
  }
  case 'agent-generate': {
    // usage:
    //   node kvidai-client.mjs agent-generate <projectId> <message> [file1] [file2...]
    //   node kvidai-client.mjs agent-generate <projectId> <message> --cdn-url <url> [--mime <type>] [--filename <name>] [--size <bytes>]
    //
    // --cdn-url 사용 시 kvidai-media 로 미리 업로드한 URL 직접 첨부 (recommended for large files).
    // multipart filePaths 와 cdnUrl 은 mutually exclusive — cdnUrl 있으면 JSON body 흐름.
    const positional = [];
    const cdnAttachments = [];
    let pending = {};
    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '--cdn-url') {
        if (pending.cdnUrl) { cdnAttachments.push(pending); pending = {}; }
        pending.cdnUrl = args[++i];
      } else if (a === '--mime') pending.mimeType = args[++i];
      else if (a === '--filename') pending.name = args[++i];
      else if (a === '--size') pending.size = Number(args[++i]);
      else positional.push(a);
    }
    if (pending.cdnUrl) cdnAttachments.push(pending);

    const [pid, msg, ...filePaths] = positional;
    log(`Streaming agent for project ${pid}...`);

    let opts = {};
    if (cdnAttachments.length) {
      // mime/type 추정 (사용자가 안 주면 url 으로 추측)
      const inferType = (mime) => {
        if (!mime) return 'image';
        if (mime.startsWith('image/')) return 'image';
        if (mime.startsWith('video/')) return 'video';
        if (mime.startsWith('audio/')) return 'audio';
        if (mime === 'application/pdf') return 'pdf';
        return 'text';
      };
      opts.attachedFiles = cdnAttachments.map((a) => ({
        name: a.name ?? a.cdnUrl.split('/').pop() ?? 'attachment',
        type: inferType(a.mimeType),
        mimeType: a.mimeType ?? 'application/octet-stream',
        size: a.size ?? 0,
        cdnUrl: a.cdnUrl,
      }));
    } else if (filePaths.length) {
      opts.filePaths = filePaths;
    }

    const tools = await agentGenerate(Number(pid), msg ?? '', (t) => log(`  ▸ ${t}`), opts);
    log(`\nDone. Tools: ${tools.join(', ')}`);
    console.log(`https://kvid.ai/en/editor/${pid}`);
    break;
  }
  case 'poll-status': {
    const result = await pollStatus(args[0] ?? '');
    console.log(JSON.stringify(result, null, 2));
    break;
  }
  case 'upload-assets': {
    // usage: node kvidai-client.mjs upload-assets <email> <file1> [file2] [file3]
    const [email, ...files] = args;
    if (!email || files.length === 0) {
      console.error('Usage: node kvidai-client.mjs upload-assets <email> <file1> [file2...]');
      process.exit(1);
    }
    log(`Uploading ${files.length} file(s) for ${email}...`);
    const uploaded = await uploadAssets({ filePaths: files, email });
    uploaded.forEach((f) => log(`  ✓ ${f.name} → id=${f.id} url=${f.url}`));
    console.log(JSON.stringify(uploaded, null, 2));
    break;
  }
  case 'add-composition-asset': {
    // usage: node kvidai-client.mjs add-composition-asset <projectId> <email> <assetJson>
    // assetJson: '{"id":"asset_1","type":"image","remoteUrl":"https://..."}'
    const [pid, email, assetJson] = args;
    if (!pid || !email || !assetJson) {
      console.error('Usage: node kvidai-client.mjs add-composition-asset <projectId> <email> <assetJson>');
      process.exit(1);
    }
    const asset = JSON.parse(assetJson);
    const result = await addCompositionAsset(Number(pid), email, asset);
    console.log(JSON.stringify(result, null, 2));
    break;
  }
  case 'attach-media': {
    // usage: node kvidai-client.mjs attach-media <projectId> <fileId1> [fileId2...]
    // requires STRAPI_TOKEN env var
    const [pid, ...ids] = args;
    if (!pid || ids.length === 0) {
      console.error('Usage: node kvidai-client.mjs attach-media <projectId> <fileId1> [fileId2...]');
      process.exit(1);
    }
    const result = await attachMediaToProject(Number(pid), ids.map(Number));
    console.log(result ? JSON.stringify(result, null, 2) : 'skipped (STRAPI_TOKEN not set)');
    break;
  }
  default:
    console.error('Usage: node kvidai-client.mjs create-project|get-project|agent-generate|poll-status|upload-assets|add-composition-asset|attach-media [args]');
    console.error('  agent-generate <projectId> <message> [file1] [file2...]  — files sent as multipart alongside generate request');
    process.exit(1);
}
