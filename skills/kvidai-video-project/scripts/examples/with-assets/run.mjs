#!/usr/bin/env node
// Example: create project → upload local assets → agent-generate
//
// Prerequisites:
//   export KVIDAI_API_KEY="<your-api-key>"
//   export KVIDAI_USER_EMAIL="user@example.com"  (must exist in kvidai DB)
//   export KVIDAI_BASE_URL="https://api.kvid.ai"  (optional, default)
//   export STRAPI_TOKEN="<token>"                 (optional — for media library attach)
//
// Run:
//   node run.mjs
//
// Replace assets/reference.jpg and assets/broll.mp4 with your own files.

import { readFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  createProject,
  uploadAssets,
  addCompositionAsset,
  attachMediaToProject,
  agentGenerate,
} from '../../kvidai-client.mjs';

const DIR = dirname(fileURLToPath(import.meta.url));
const log = (...a) => console.error('[example]', ...a);

const EMAIL = process.env.KVIDAI_USER_EMAIL;
if (!EMAIL) throw new Error('KVIDAI_USER_EMAIL not set — export it before running');

// ── 1. Create project ────────────────────────────────────────────────────────
log('[1/5] Creating project...');
const projectId = await createProject('Video with Assets Example');
log(`      projectId=${projectId}`);

// ── 2. Read brief (text → agent message) ────────────────────────────────────
log('[2/5] Reading brief.md...');
const brief = await readFile(resolve(DIR, 'assets/brief.md'), 'utf-8');

// ── 3. Upload image + video assets to CDN ───────────────────────────────────
log('[3/5] Uploading assets (reference.jpg + broll.mp4)...');
const uploaded = await uploadAssets({
  filePaths: [
    resolve(DIR, 'assets/reference.jpg'),
    resolve(DIR, 'assets/broll.mp4'),
  ],
  email: EMAIL,
});
uploaded.forEach((f) => log(`      ✓ ${f.name} id=${f.id} → ${f.url}`));

const [refImg, brollVid] = uploaded;

// ── 4. Add assets to composition (agent sees them on the timeline) ────────────
log('[4/5] Adding assets to composition.assets...');
await addCompositionAsset(projectId, EMAIL, {
  id: `asset_${refImg.id}`,
  type: 'image',
  remoteUrl: refImg.url,
  filename: refImg.name,
});
await addCompositionAsset(projectId, EMAIL, {
  id: `asset_${brollVid.id}`,
  type: 'video',
  remoteUrl: brollVid.url,
  filename: brollVid.name,
});

// (Optional) attach to project media library — requires STRAPI_TOKEN
await attachMediaToProject(projectId, uploaded.map((f) => f.id));

// ── 5. Generate video with AI agent ──────────────────────────────────────────
log('[5/5] Running agent-generate (SSE stream, 1-3 min)...');

const message = `${brief}

## Uploaded Assets
- Reference image (asset_${refImg.id}): ${refImg.url}
  → Use this for visual style reference and as the opening hero image.
- B-roll video (asset_${brollVid.id}): ${brollVid.url}
  → Use this footage in the middle section with narration overlay.`;

const tools = await agentGenerate(projectId, message, (t) => log(`      ▸ ${t}`));
log(`\nDone. Tools called: ${tools.join(', ')}`);
console.log(`https://kvid.ai/en/editor/${projectId}`);
