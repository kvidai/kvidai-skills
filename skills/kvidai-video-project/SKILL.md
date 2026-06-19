---
name: kvidai-video-project
description: "Use when you need to call the kvidai API to create video projects, generate videos with AI auto-editing, or check generation status. Triggers on: create video project, generate video, auto-edit video, kvidai API, video-project CRUD, 영상 생성, 프로젝트 생성, 상태 조회, start video generation, poll job status. Use this skill whenever an agent (Claude Code, Codex CLI, Hermes) needs to interact with the kvidai video platform programmatically."
---

The kvidai API auto-generates videos from natural language via an SSE-streaming AI agent. The client lives at `.claude/skills/kvidai-video-project/scripts/kvidai-client.mjs` and runs with plain `node`.

All paths below are relative to the **kvidai monorepo root**.

## Environment variables

```bash
export KVIDAI_API_KEY="<prod-contents-apim-key>"
export KVIDAI_BASE_URL="https://api.kvid.ai" # default if not set
export KVIDAI_USER_EMAIL="user@example.com"  # required for asset upload
```

## Run (agent path)

```bash
SKILL=.claude/skills/kvidai-video-project/scripts/kvidai-client.mjs

# Create a new project → prints projectId
KVIDAI_API_KEY=xxx node $SKILL create-project "My Video"

# Get project details
KVIDAI_API_KEY=xxx node $SKILL get-project 260

# Generate video via AI agent (SSE, 1-3 min)
KVIDAI_API_KEY=xxx node $SKILL agent-generate 260 "고양이가 뛰는 5초짜리 세로형 영상"

# Generate with local files attached (multipart — files uploaded inline with generate request)
KVIDAI_API_KEY=xxx node $SKILL agent-generate 260 "reference.jpg 이미지를 배경으로 활용해" reference.jpg broll.mp4

# Poll async generation status
KVIDAI_API_KEY=xxx node $SKILL poll-status <jobId>

# --- Asset upload (with local files) ---

# Upload files → prints JSON with id + CDN url per file
KVIDAI_API_KEY=xxx node $SKILL upload-assets user@example.com brief.md reference.jpg broll.mp4

# Add uploaded file URL to project composition (agent sees it on timeline)
KVIDAI_API_KEY=xxx node $SKILL add-composition-asset 260 user@example.com \
  '{"id":"asset_ref1","type":"image","remoteUrl":"https://cdn.example.com/reference.jpg"}'

```

## Core workflow

```
1. create-project "name"    → projectId (integer)
2. agent-generate <id> "<message>"  → SSE stream → https://kvid.ai/en/editor/<id>
   (streams tool events: generate_voice → generate_image → update_item → add_solid → add_text)
3. (optional async) poll-status <jobId>  → wait for completed
```

## Asset upload workflow (with local files)

**Important**: `/video-project/create` is JSON-only — files cannot be attached at creation time.

### Option A — inline (files sent with generate request)

```
1. create-project "name"                                              → projectId
2. agent-generate <id> "<message>" file1.jpg file2.mp4               → SSE stream
   (files uploaded to CDN and injected into composition.assets before agent runs)
```

### Option B — separate upload (more control, attach to media library)

```
1. create-project "name"                        → projectId
2. upload-assets <email> file1 file2 file3      → [{ id, url, name }, ...]
3. add-composition-asset <id> <email> <asset>   → adds remoteUrl to composition.assets
   (repeat for each file; agent references these assets on the timeline)
4. agent-generate <id> "<describe use of assets>"  → SSE stream
```

**End-to-end example (Option B)**: see `scripts/examples/with-assets/run.mjs`

## REST API reference

**Create project**

```
POST {KVIDAI_BASE_URL}/video-project/create
api-key: {KVIDAI_API_KEY}
{"name": "My Video"}
→ {"success": true, "data": {"id": 260, ...}}
```

**Agent generate (SSE) — JSON**

```
POST {KVIDAI_BASE_URL}/agent/generate
api-key: {KVIDAI_API_KEY}
Content-Type: application/json
{"projectId": 260, "message": "영상 설명", "chatHistory": []}
→ SSE: event: tool_start/tool_end/heartbeat, data: {toolName, success, ...}
```

**Agent generate with files — multipart (base64 fallback kept)**

```
POST {KVIDAI_BASE_URL}/agent/generate
api-key: {KVIDAI_API_KEY}
Content-Type: multipart/form-data  (boundary set by fetch automatically)

data: {"projectId": 260, "message": "영상 설명", "chatHistory": []}  ← JSON string
files: <binary file 1>
files: <binary file 2>
→ same SSE stream; files are uploaded to CDN and injected into composition.assets before agent runs
```

Note: files in multipart are uploaded to CDN internally — no separate `upload-assets` step needed.

**SSE pattern (Node.js 20+)**

```js
const r = await fetch(url, { method: 'POST', headers, body, signal: AbortSignal.timeout(300_000) });
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
    if (line.startsWith('data: ') && event === 'tool_start') {
      const d = JSON.parse(line.slice(6));
      if (d.toolName) console.log('tool:', d.toolName);
    }
  }
}
```

**Get project**

```
GET {KVIDAI_BASE_URL}/video-project/{id}
api-key: {KVIDAI_API_KEY}
```

**Async t2v**

```
POST {KVIDAI_BASE_URL}/ai/generation/text-to-video/generate-async
api-key: {KVIDAI_API_KEY}
{"email":"user@example.com","prompt":"...","model":"veo3.1","function":"txt2vid","duration":5,"resolution":"720p","aspect_ratio":"16:9"}
→ {"jobId": "..."}
```

**Poll status**

```
GET {KVIDAI_BASE_URL}/ai/generation/status?jobId={jobId}
api-key: {KVIDAI_API_KEY}
```

**Upload assets** (multipart, no JWT — email-based public endpoint)

```
POST {KVIDAI_BASE_URL}/api/media-management/upload
api-key: {KVIDAI_API_KEY}
Content-Type: multipart/form-data

fields:
  email: user@example.com       (must exist in DB)
  files: <binary file>          (repeat per file)

→ { success: true, data: [{ id, url, name, mime, size }, ...] }
```

**Add asset to composition timeline**

```
PATCH {KVIDAI_BASE_URL}/video-project/{id}/composition
api-key: {KVIDAI_API_KEY}
{ "email": "user@example.com",
  "operation": "add_asset",
  "data": { "asset": { "id": "asset_ref1", "type": "image", "remoteUrl": "https://cdn.example.com/img.jpg" } } }

→ { data: { composition: { assets: { "asset_ref1": { ... } } } } }
```

## Import in JavaScript (ESM)

```js
import {
  createProject,
  agentGenerate,
  pollStatus,
  getProject,
} from '.claude/skills/kvidai-video-project/scripts/kvidai-client.mjs';
```

For marketing-studio: use `@marketing-studio/send-video-kvidai` (wraps the same API).

## Gotchas

- **SSE stream runs 1-3 minutes** — always set `AbortSignal.timeout(300_000)`. Do not use a 60-second timeout.
- **heartbeat lines** (`": heartbeat"`) fire between tool calls. Skip them; only parse `event:` + `data:` lines.
- **Async t2v endpoint** unreachable from this dev container (HTTP 000). Works from production environments.
- **`/video-project/create` is JSON-only** — cannot include files in the create call. Upload is always a separate step.
- **`uploadAssets` needs a registered user email** — the email must exist in Strapi DB. Upload will 404 if not found.
- **Content-Type must NOT be set manually for multipart** — let `fetch` set the boundary automatically.

## Troubleshooting

| Symptom                    | Fix                                                              |
| -------------------------- | ---------------------------------------------------------------- |
| `KVIDAI_API_KEY not set`   | Export the env var before running `node`                         |
| `agentGenerate` hangs      | Check `api-key` — 403 closes stream silently; add stderr logging |
| HTTP 000 on async endpoint | Container network issue; works from production                   |
