---
name: kvidai-ref
description: >
  Complete kvidai CLI command reference — consult this whenever the user
  asks you to generate an image or video, upload files, check an async job,
  or manage a kvidai project. Use --json on every command to get structured
  output you can parse.
---

# kvidai CLI reference

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

kvidai is an agent-first CLI for kvid.ai. Every command emits structured JSON
when called with `--json` or when stdout is not a TTY. There is no model
catalog or per-model schema to inspect — the command set below is the
complete, fixed surface.

## Authentication

kvidai reads credentials from (in priority order):

1. `KVIDAI_API_KEY` environment variable
2. `~/.kvidai/config.json` (written by `kvidai setup`)
3. A project `.env` file (if auto-load is enabled via `kvidai setup`)

```
kvidai setup --non-interactive --api-key <key> --json    # agents/CI
kvidai setup                                              # interactive wizard
```

`KVIDAI_USER_EMAIL` is also required for `video t2v` and `assets upload`.

## Commands

### project — create and inspect video projects

```
kvidai project create <name> [--preset-id <id>] [--json]
kvidai project get <id> [--json]
```

`create` returns `{ id }`. Most video work starts by creating a project,
then either driving it with `video generate` (agent, multi-turn) or a
one-off `video t2v` call.

### video — generate video

```
kvidai video generate <projectId> <message> [--cdn-url <url>] [--mime <type>] [--filename <name>] [--verbose] [--json]
kvidai video t2v <prompt> [--model <id>] [--duration <s>] [--wait] [--output <path>] [--interval <ms>] [--timeout <ms>] [--json]
```

`generate` streams an AI agent editing an **existing** project over SSE and
returns `{ projectId, tools, url }` (`url` is the kvid.ai editor link, not a
media file). Use `--cdn-url` to attach a file (from `upload`/`assets upload`)
as context for the agent's instruction. `--verbose` prints tool-call names
to stderr as they happen.

`t2v` is a standalone async text-to-video job — no project required.
Without `--wait`/`--output` it returns immediately with `{ jobId, ... }`;
poll it with `task status`. With `--wait` or `--output` it polls internally
and returns the finished result (or downloads it, respectively).

### image — generate images

```
kvidai image generate <prompt> [--model <id>] [--size <preset>] [--num <n>] [--output <path>] [--json]
```

Synchronous — returns the result directly. `--size` accepts `square`,
`square_hd`, `portrait_4_3`, `portrait_16_9`, `landscape_4_3`,
`landscape_16_9` (default `square`). `--num` sets image count (default 1).
`--output` downloads the first result image to that path.

### task — check or poll an async job

```
kvidai task status <jobId> [--wait] [--interval <ms>] [--timeout <ms>] [--output <path>] [--json]
```

`jobId` comes from `video t2v`. Without `--wait`, returns the current status
once. With `--wait`, polls (default every 5000ms, up to 600000ms) until the
job completes or fails, then returns the full result. `--output` downloads
the result video once complete (implies waiting for completion).

### upload / assets — get files onto kvid.ai CDN

```
kvidai upload <file_path> [--json]
kvidai assets upload <file1> [file2...] [--json]
kvidai assets add-composition <projectId> <email> <assetJson> [--json]
```

`upload` and `assets upload` both do a presigned-URL upload and return
`{ cdnUrl, key, size }` (assets upload returns one such object per file).
Use the `cdnUrl` as `video generate --cdn-url`, or with `add-composition` to
attach an asset directly into a project's composition
(`assetJson` example: `{"id":"asset_1","type":"image","remoteUrl":"..."}`).

### docs — static documentation links (not a real search)

```
kvidai docs [query] [--json]
```

This does **not** perform a search — `query` is accepted but ignored. It
always returns the same static links (`docs.kvid.ai`, `api.kvid.ai/docs`).
Don't build a "discover via docs" step around this command.

## Error output

Every command exits non-zero on failure and writes a JSON object to stderr:

```json
{
  "error": "<one-line summary, often includes raw HTTP status + body>",
  "details": { "...": "shape varies by command, may be absent" }
}
```

There is no standardized `validation_errors`/`endpoint_id`/`request_id`
schema — read `error` for the summary, and `details` (when present) for
extra context such as a `hint` on auth failures. On a 4xx, fix the request
and retry; on 429/5xx, a short backoff-and-retry is reasonable.

## Common workflows

### One-off image
```
kvidai image generate "a cat on the moon" --size landscape_16_9 --output ./cat.png --json
```

### One-off video, wait for it
```
kvidai video t2v "a dog running on a beach" --duration 10 --wait --output ./dog.mp4 --json
```

### One-off video, fire-and-poll
```
kvidai video t2v "a dog running on a beach" --duration 10 --json
# save jobId from the response, then:
kvidai task status <jobId> --wait --output ./dog.mp4 --json
```

### Using a local file as agent context
```
kvidai upload ./reference.jpg --json
# use the returned cdnUrl:
kvidai project create "New scene" --json
kvidai video generate <projectId> "match the lighting from this reference" \
  --cdn-url <cdnUrl> --mime image/jpeg --json
```

### Multi-turn project editing
```
kvidai project create "Product launch" --json
kvidai video generate <projectId> "make a 10s intro for our product" --verbose --json
kvidai video generate <projectId> "make the intro faster-paced" --verbose --json
```
