---
name: kvidai-media
description: Use when you need to upload a media file (image, video, audio, pdf, text) to kvidai CDN so that an agent / video-project can reference it by URL. Triggers on media upload, file upload, attach file, cdnUrl, presigned URL, 이미지 업로드, 영상 업로드, 첨부, 파일 업로드. Wraps api.kvid.ai/media — issues a presigned PUT URL, performs the PUT direct to DO Spaces, then returns the public cdnUrl. The cdnUrl can be passed to kvidai-video-project agent-generate as an attachedFile.
metadata:
  tags: kvidai, media, upload, presigned, cdn, apim
---

The kvidai Media API is a public REST surface on `api.kvid.ai/media` (Azure APIM) that wraps the Strapi `media-management` controller. Unlike the legacy multipart upload, this Skill uses a **presigned URL** pattern — the client requests a short-lived signed PUT URL, uploads the file binary directly to CDN storage (DigitalOcean Spaces), and gets back a public cdnUrl that any other kvidai API can reference.

The client lives at `.claude/skills/kvidai-media/scripts/kvidai-media-client.mjs` and runs with plain `node` (no tsx required).

All paths below are relative to the **kvidai monorepo root**.

## Why presigned URL

| Aspect | Multipart (legacy) | Presigned (this Skill) |
|---|---|---|
| Network hops | client → APIM → Strapi → DO Spaces (3 hops, all bytes traverse each) | client → APIM (small JSON) + client → DO Spaces direct (1 large hop) |
| APIM body limit | bound to APIM/proxy limit (~hundreds MB) | only the JSON metadata goes through APIM |
| Auth | api-key on every byte | api-key on the URL request only; PUT uses the signed URL |
| Best for | small base64 inline from browser | external clients (Skills, CLI, server-to-server) |

## Environment variables

```bash
export KVIDAI_API_KEY="<prod-media-apim-key>"            # APIM subscription key, scope = media product
export KVIDAI_BASE_URL="https://api.kvid.ai"             # default if not set; staging: https://staging-api.kvid.ai
```

The API auto-scopes uploads to the subscription owner — no need to pass an email in the body.

## Run

```bash
SKILL=.claude/skills/kvidai-media/scripts/kvidai-media-client.mjs

# Upload a local file → prints { cdnUrl, key, ... }
node $SKILL upload-file ./my-image.jpg

# Get presigned URL only (advanced — you handle the PUT yourself)
node $SKILL get-presigned-url my-image.jpg image/jpeg 102400

# List files owned by the caller (paginated)
node $SKILL list-files

# Get a single file by Strapi file id
node $SKILL get-file 42

# Delete a file
node $SKILL delete-file 42

# Stats (count + total size per type)
node $SKILL stats
```

## Compose with kvidai-video-project

```bash
# 1. Upload an image
CDN_URL=$(node .claude/skills/kvidai-media/scripts/kvidai-media-client.mjs upload-file ./logo.png | jq -r '.cdnUrl')

# 2. Generate a video that references it
node .claude/skills/kvidai-video-project/scripts/kvidai-client.mjs \
  agent-generate <projectId> "이 로고로 영상 인트로 만들어줘" \
  --cdn-url "$CDN_URL" --mime image/png --filename logo.png
```

## Response shape

`upload-file` and `get-presigned-url` both return:

```json
{
  "uploadUrl": "https://...digitaloceanspaces.com/...?X-Amz-...",
  "headers": {
    "Content-Type": "image/jpeg",
    "x-amz-acl": "public-read"
  },
  "key": "presigned-uploads/{email-hash}/{uuid}/{filename}",
  "cdnUrl": "https://cdn.kvid.ai/...",
  "expiresInSeconds": 1800
}
```

`upload-file` additionally performs the PUT internally; the final terminal output contains both the response above and `{ ok: true }` confirming the PUT succeeded.

## Constraints

- File size: server enforces a 200 MB cap on the metadata request (`size` field). Actual PUT to DO Spaces can be larger, but expect timeouts for very large files — split into chunks or extend `expiresInSeconds` (default 1800s = 30min).
- Presigned URL is **single-use within TTL** for PUT. Do not retry the same URL across processes — request a fresh one.
- PUT **must** include the `x-amz-acl: public-read` header (also returned in `headers`). Without it the object is private and cdnUrl returns 403.
