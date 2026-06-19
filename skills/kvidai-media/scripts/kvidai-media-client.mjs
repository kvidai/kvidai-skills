#!/usr/bin/env node
/**
 * kvidai-media CLI — upload local files to kvidai CDN via presigned URL.
 *
 * Talks to api.kvid.ai/media (Azure APIM) which rewrites to Strapi
 * /api/media-management/*. Auth: APIM subscription key in `KVIDAI_API_KEY`.
 * APIM injects the caller's email as X-Kvidai-User-Email on the backend hop,
 * so this client carries only the key.
 *
 * Usage:
 *   node kvidai-media-client.mjs upload-file <local-path>
 *   node kvidai-media-client.mjs get-presigned-url <filename> <mimeType> [size]
 *   node kvidai-media-client.mjs list-files
 *   node kvidai-media-client.mjs get-file <fileId>
 *   node kvidai-media-client.mjs delete-file <fileId>
 *   node kvidai-media-client.mjs stats
 */

import fs from 'node:fs';
import path from 'node:path';

const API_KEY = process.env.KVIDAI_API_KEY;
const BASE_URL = process.env.KVIDAI_BASE_URL || 'https://api.kvid.ai';
const PREFIX = '/media';

if (!API_KEY) {
  console.error('KVIDAI_API_KEY environment variable is required.');
  process.exit(1);
}

function headers(extra = {}) {
  return {
    'Ocp-Apim-Subscription-Key': API_KEY,
    'Content-Type': 'application/json',
    ...extra,
  };
}

async function apimRequest(method, subPath, body) {
  const url = `${BASE_URL}${PREFIX}${subPath}`;
  const res = await fetch(url, {
    method,
    headers: headers(),
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json;
  try { json = text ? JSON.parse(text) : null; } catch { json = text; }
  if (!res.ok) {
    console.error(`${method} ${url} → ${res.status}`);
    if (json) console.error(JSON.stringify(json, null, 2));
    process.exit(1);
  }
  return json;
}

function print(result) {
  console.log(JSON.stringify(result, null, 2));
}

// MIME type heuristic from extension — fallback when caller doesn't pass one.
function inferMime(filename) {
  const ext = path.extname(filename).toLowerCase();
  const map = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml',
    '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.webm': 'video/webm',
    '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4',
    '.pdf': 'application/pdf',
    '.txt': 'text/plain', '.md': 'text/markdown', '.json': 'application/json',
  };
  return map[ext] || 'application/octet-stream';
}

async function getPresignedUrl(filename, mimeType, size) {
  const body = { filename, mimeType };
  if (typeof size === 'number') body.size = size;
  const res = await apimRequest('POST', '/presigned-upload-url', body);
  return res?.data ?? res;
}

async function uploadFile(localPath) {
  const stat = fs.statSync(localPath);
  const filename = path.basename(localPath);
  const mimeType = inferMime(filename);
  const size = stat.size;

  const presigned = await getPresignedUrl(filename, mimeType, size);
  const { uploadUrl, headers: putHeaders, cdnUrl, key, expiresInSeconds } = presigned;

  const fileBuffer = fs.readFileSync(localPath);
  const putRes = await fetch(uploadUrl, {
    method: 'PUT',
    headers: putHeaders,
    body: fileBuffer,
  });
  if (!putRes.ok) {
    const errText = await putRes.text();
    console.error(`PUT ${uploadUrl.split('?')[0]} → ${putRes.status}`);
    console.error(errText.slice(0, 500));
    process.exit(1);
  }

  return { ok: true, cdnUrl, key, uploadUrl, expiresInSeconds, size, mimeType, filename };
}

const [, , cmd, ...args] = process.argv;

switch (cmd) {
  case 'upload-file': {
    const localPath = args[0];
    if (!localPath) { console.error('upload-file requires <local-path>'); process.exit(1); }
    if (!fs.existsSync(localPath)) { console.error(`File not found: ${localPath}`); process.exit(1); }
    print(await uploadFile(localPath));
    break;
  }
  case 'get-presigned-url': {
    const [filename, mimeType, sizeStr] = args;
    if (!filename || !mimeType) {
      console.error('get-presigned-url requires <filename> <mimeType> [size]');
      process.exit(1);
    }
    const size = sizeStr ? Number(sizeStr) : undefined;
    print(await getPresignedUrl(filename, mimeType, size));
    break;
  }
  case 'list-files': {
    print(await apimRequest('GET', '/files'));
    break;
  }
  case 'get-file': {
    const id = args[0];
    if (!id) { console.error('get-file requires <fileId>'); process.exit(1); }
    print(await apimRequest('GET', `/files/${id}`));
    break;
  }
  case 'delete-file': {
    const id = args[0];
    if (!id) { console.error('delete-file requires <fileId>'); process.exit(1); }
    print(await apimRequest('DELETE', `/files/${id}`));
    break;
  }
  case 'stats': {
    print(await apimRequest('GET', '/stats'));
    break;
  }
  default: {
    console.error('unknown command:', cmd);
    console.error('try: upload-file <path> | get-presigned-url <filename> <mime> [size] | list-files | get-file <id> | delete-file <id> | stats');
    process.exit(1);
  }
}
