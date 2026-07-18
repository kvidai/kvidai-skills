---
name: kvidai-ref
description: >
  Complete kvidai CLI reference for kvid.ai — consult this whenever the user
  asks you to search for models, run inference, upload files, check pricing,
  or manage async jobs on kvid.ai. Use --json on every command to get
  structured output you can parse.
---

# kvidai CLI reference

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

kvidai is an agent-first CLI for kvid.ai. Every command emits structured JSON
when called with `--json` or when stdout is not a TTY.

## Authentication

kvidai reads credentials from (in priority order):

1. `KVIDAI_API_KEY` environment variable
2. `~/.kvidai/config.json` (written by `kvidai setup`)
3. A project `.env` file (if auto-load is enabled via `kvidai setup`)

## Commands

### models — search and inspect models

```
kvidai models [query] [--category <cat>] [--status active|deprecated|all] [--limit <n>] [--cursor <token>] [--endpoint_id <id,...>] [--expand openapi-3.0] [--json]
```

Free-text search across 600+ models. Use `--endpoint_id` to fetch specific
models by ID. Use `--expand openapi-3.0` to get the full OpenAPI schema.
Use `--cursor` from a previous response to page through results.

### schema — inspect model inputs/outputs

```
kvidai schema <endpoint_id> [--format compact|openapi] [--json]
```

Shows the input parameters and output shape for a model.
`--format openapi` returns the full raw OpenAPI spec.
Always run this before `kvidai run` to know what parameters the model accepts.

### run — execute a model

```
kvidai run <endpoint_id> --<param> <value> ... [--async] [--logs] [--download [template]] [--json]
```

Pass any model input parameter as a `--flag value` pair.
Waits for the result by default and returns `{ status, endpoint_id, request_id, result }`.

Use `--async` for long-running models (video generation, etc.).
Returns `{ status: "submitted", request_id, endpoint_id }` immediately.
Then poll with `kvidai status`.

Use `--download` to save every media URL in the result to disk — see
["Downloading output files"](#downloading-output-files) below.

### status — check or retrieve an async job

```
kvidai status <endpoint_id> <request_id> [--result] [--logs] [--cancel] [--download [template]] [--json]
```

Without flags: returns queue position and job status.
`--result`: blocks until complete and returns the full result.
`--cancel`: cancels a queued job.
`--download`: implies `--result`. Writes every media URL from the result to
disk — see below.

## Downloading output files

Agents should **not** `curl` URLs out of the `result` payload. Pass
`--download` to `run` or `status` instead; the CLI handles extraction,
fetching, naming, and concurrency, and emits the saved paths in the JSON
output under `downloaded_files[]`.

```
kvidai run <endpoint_id> ... --download [template] --json
kvidai status <endpoint_id> <request_id> --download [template] --json
```

Behavior:

- `--download` with no value → save to cwd using the source file name
  (from `file_name`, the URL path, or a `content_type`-derived extension).
- `--download <dir>/` (trailing `/`) or an existing directory → save inside
  that directory with source file names. Parent directories are created
  recursively.
- `--download <template>` → substitute placeholders and write to the
  resulting path. Supported placeholders: `{index}` (0-based walk order),
  `{name}` (basename without extension), `{ext}` (extension without dot),
  `{request_id}`.
- Plain filename with multiple outputs → first file keeps the name, later
  files get `_1`, `_2`, … suffixes on collision.

Detection rule: the CLI walks the `result` payload and downloads any object
with a `url: string` starting with `http(s)://`. This matches every
standard kvid.ai media output shape (`images[]`, `image_urls[]`, `video`,
`audio`, etc.).

Successful output (`run` with `--download`):

```json
{
  "status": "completed",
  "endpoint_id": "kvid-ai/flux/dev",
  "request_id": "...",
  "result": { "...": "untouched" },
  "downloaded_files": [
    { "url": "https://...", "path": "/abs/path/cat.png", "size_bytes": 204800, "json_path": "images[0]" }
  ]
}
```

If one or more URLs fail to download, the remaining files still land on
disk and the failures appear under `download_failures[]`:

```json
{
  "downloaded_files": [ ... ],
  "download_failures": [
    { "url": "https://...", "json_path": "images[1]", "error": "404 Not Found" }
  ]
}
```

The command's exit code reflects the model run itself, not individual
download failures. When `download_failures[]` is non-empty, surface the
errors to the user and/or retry those URLs.

Guidance:

- Default to `--download` whenever the user expects files on disk. It
  replaces the old "parse result, then curl each URL" pattern.
- For multi-output models (`num_images > 1`, `image_urls[]`, etc.), use a
  template with `{index}` (e.g. `./out/{request_id}_{index}.{ext}`) to
  guarantee unique paths.
- `--download` on `status` implies `--result` — you do not need to pass
  both. Combining `--download` with `--cancel` is rejected.

### upload — upload a file to kvid.ai CDN

```
kvidai upload <file_path_or_url> [--json]
```

Accepts a local file path or a remote URL. Returns a CDN URL suitable for
use as a model input parameter (e.g. `--image_url`).

### pricing — check model cost

```
kvidai pricing <endpoint_id> [--json]
```

### docs — search kvid.ai documentation

```
kvidai docs <query> [--json]
```

## Error output

Every command exits non-zero on failure and writes a JSON error object to
stderr. The shape is stable across commands:

```json
{
  "error": "<human-readable summary>",
  "details": {
    "endpoint_id": "kvid-ai/flux/schnell",
    "request_id": "019d...",
    "status": 422,
    "error_type": "ValidationError" | "ApiError" | "Error",
    "validation_errors": [
      {
        "field": "num_images",
        "message": "Input should be less than or equal to 4",
        "type": "less_than_equal",
        "input": 20
      }
    ],
    "body": { "detail": [ ... raw server payload ... ] },
    "logs": [ { "level": "ERROR", "message": "...", "timestamp": "..." } ]
  }
}
```

Field meanings:

- `error` — one-line summary you can show the user.
- `details.status` — HTTP status from kvid.ai (`422` input validation, `401`
  unauthenticated, `403` forbidden, `404` endpoint not found, `429` rate
  limited, `5xx` upstream). Missing for local errors (network, parsing).
- `details.error_type` — `ValidationError` for 422 with FastAPI-style
  `detail[]`; `ApiError` for other HTTP failures; `Error` for local errors.
- `details.validation_errors` — present only when the server returned a
  FastAPI validation payload. Each entry is `{ field, message, type, input }`
  and uniquely identifies what the agent needs to fix. Dotted field paths
  like `options.seed` or `images[0].url` point at nested inputs.
- `details.body` — the raw response body, preserved for agents that need
  the full FastAPI `ctx`/`expected` fields or vendor-specific payloads.
- `details.logs` — recent model-side log lines when the failure happened
  during inference (not for pre-flight validation errors).
- `details.request_id` — included when the request reached kvid.ai; pass it
  to `kvidai status <endpoint_id> <request_id> --logs --json` for full
  history.

Agent guidance:

- For `status: 422`, read `validation_errors`, correct the offending args,
  and retry. Re-run `kvidai schema <endpoint_id> --json` if you need
  allowed enum values or numeric bounds.
- For `401`/`403`, check credentials — do not retry.
- For `404`, verify the `endpoint_id` with `kvidai models ... --json`.
- For `429` or `5xx`, a short backoff-and-retry is acceptable; everything
  else should be surfaced to the user.

## Common workflows

### Synchronous inference (fast models)
```
kvidai schema kvid-ai/flux/dev --json
kvidai run kvid-ai/flux/dev --prompt "a cat on the moon" --json
```

### Async inference (slow models — video, etc.)
```
kvidai run kvid-ai/veo3.1 --prompt "a dog running" --async --json
# save the request_id from the response, then:
kvidai status kvid-ai/veo3.1 <request_id> --result --json
```

### Using a local image as input
```
kvidai upload ./photo.jpg --json
# use the returned url as input:
kvidai run kvid-ai/some-model --image_url <cdn_url> --json
```

### Discovering models for a task
```
kvidai models "text to video" --json
kvidai schema <endpoint_id> --json
```

### Saving outputs directly to disk
```
# single file → cwd using source file name
kvidai run kvid-ai/flux/dev --prompt "a cat" --download --json

# multiple images → templated paths
kvidai run kvid-ai/flux/dev --prompt "a cat" --num_images 4 \
  --download "./out/{request_id}_{index}.{ext}" --json

# async job → download on completion (implies --result)
kvidai run kvid-ai/veo3.1 --prompt "a dog running" --async --json
kvidai status kvid-ai/veo3.1 <request_id> --download ./videos/ --json
```
