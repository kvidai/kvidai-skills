#!/usr/bin/env node
/**
 * kvidai-preset CLI — list / get / create / update / delete / duplicate.
 *
 * Talks to api.kvid.ai/preset (Azure APIM) which rewrites to Strapi /api/video-preset/*.
 * Auth: APIM subscription key in `KVIDAI_API_KEY`. APIM injects the caller's
 * email as `X-Kvidai-User-Email` on the backend hop, so this client only carries
 * the key — it does NOT need to also send the email.
 *
 * Usage:
 *   node kvidai-preset-client.mjs list
 *   node kvidai-preset-client.mjs get <numeric_id>
 *   node kvidai-preset-client.mjs get-by-preset-id <presetId>
 *   node kvidai-preset-client.mjs create <path-to-json-file>
 *   node kvidai-preset-client.mjs update <numeric_id> '<inline-json>'
 *   node kvidai-preset-client.mjs duplicate <numeric_id> [new-name]
 *   node kvidai-preset-client.mjs delete <numeric_id>
 */

import fs from 'node:fs';

const API_KEY = process.env.KVIDAI_API_KEY;
const BASE_URL = process.env.KVIDAI_BASE_URL || 'https://api.kvid.ai';
const PREFIX = '/preset';

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

async function request(method, path, body) {
  const url = `${BASE_URL}${PREFIX}${path}`;
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

const [, , cmd, ...args] = process.argv;

switch (cmd) {
  case 'list': {
    print(await request('GET', '/'));
    break;
  }
  case 'get': {
    const id = args[0];
    if (!id) { console.error('get requires <id>'); process.exit(1); }
    print(await request('GET', `/${id}`));
    break;
  }
  case 'get-by-preset-id': {
    const presetId = args[0];
    if (!presetId) { console.error('get-by-preset-id requires <presetId>'); process.exit(1); }
    print(await request('GET', `/by-preset-id/${encodeURIComponent(presetId)}`));
    break;
  }
  case 'create': {
    const file = args[0];
    if (!file) { console.error('create requires <path-to-json-file>'); process.exit(1); }
    const body = JSON.parse(fs.readFileSync(file, 'utf8'));
    print(await request('POST', '/', body));
    break;
  }
  case 'update': {
    const id = args[0];
    const inline = args[1];
    if (!id || !inline) { console.error('update requires <id> <inline-json>'); process.exit(1); }
    const body = JSON.parse(inline);
    print(await request('PUT', `/${id}`, body));
    break;
  }
  case 'duplicate': {
    const id = args[0];
    const name = args[1];
    if (!id) { console.error('duplicate requires <id> [new-name]'); process.exit(1); }
    print(await request('POST', `/${id}/duplicate`, name ? { name } : {}));
    break;
  }
  case 'delete': {
    const id = args[0];
    if (!id) { console.error('delete requires <id>'); process.exit(1); }
    print(await request('DELETE', `/${id}`));
    break;
  }
  default: {
    console.error('unknown command:', cmd);
    console.error('try: list | get <id> | get-by-preset-id <presetId> | create <file> | update <id> <json> | duplicate <id> [name] | delete <id>');
    process.exit(1);
  }
}
