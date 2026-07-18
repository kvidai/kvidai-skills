---
name: kvidai
description: >
  Generate an image or video with the kvidai CLI. Use this when the user
  asks to generate an image or video, edit an existing kvidai project via
  the AI agent, or "use kvidai" for a generation task. Guides picking the
  right command, uploading inputs, waiting for async jobs, and saving
  outputs.
---

# kvidai workflow

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

kvidai has a small, fixed set of generation commands — there is no model
catalog to search and no per-model schema to inspect. Load `kvidai-ref`
alongside this skill for the full command reference.

## Steps

1. **Pick the right command** for what the user wants:

   | Want | Command |
   |---|---|
   | A single image from a prompt | `kvidai image generate <prompt> ...` |
   | A single video from a prompt, no existing project | `kvidai video t2v <prompt> ...` |
   | Edit/build inside an existing (or new) video project via the AI agent — multi-turn, can attach files | `kvidai project create` then `kvidai video generate <projectId> <message>` |

2. **Upload local files first** if the user gave you a local file to use as
   input (a reference image, a clip to attach to an agent message):
   ```
   kvidai upload <local_file> --json
   ```
   Use the returned `cdnUrl` — for `video generate`, pass it as `--cdn-url`.

3. **Generate**:
   ```
   kvidai image generate "<prompt>" --size landscape_16_9 --output ./out.png --json
   kvidai video t2v "<prompt>" --duration 10 --wait --output ./out.mp4 --json
   kvidai video generate <projectId> "<message>" --cdn-url <url> --mime image/png --verbose --json
   ```
   - `image generate` and `video t2v` return the result directly (or a
     `jobId` if you didn't pass `--wait`/`--output`).
   - `video generate` streams an AI agent editing the project over SSE and
     returns `{ projectId, tools, url }` — `url` is the editor link, not a
     media file. Use it when the user wants to keep iterating on a project,
     not just get one clip back.

4. **Poll async jobs** if you didn't pass `--wait`/`--output` to `video t2v`:
   ```
   kvidai task status <jobId> --wait --output ./out.mp4 --json
   ```

5. **Return the result** to the user. If `--output` was used, reference that
   local path. Otherwise the JSON result contains the media URL(s) directly
   — for `video generate`, point the user at the returned editor `url`
   instead of a raw file.

## Handling errors

Every command exits non-zero on failure and writes a JSON object to stderr:

```json
{
  "error": "image/generate 422: {\"message\":\"prompt is required\"}",
  "details": { "hint": "..." }
}
```

- `error` is a one-line summary — often includes the raw HTTP status and
  response body, since these commands don't do FastAPI-style structured
  validation.
- `details` is present only for some errors (e.g. missing API key includes
  a `hint` with setup instructions). Don't assume a fixed shape beyond
  `error`.
- No API key configured → run `kvidai setup --non-interactive --api-key <key>`
  (agents/CI) or point the user at `kvidai setup` (interactive).

## Notes

- Always use `--json` so output is machine-readable.
- `kvidai docs <query>` does **not** perform a real search — it just prints
  static links to `docs.kvid.ai` and `api.kvid.ai/docs`. Don't rely on its
  output for anything beyond those URLs.
- There is no `--model` catalog to browse: `image generate` / `video t2v`
  accept an optional `--model <id>` but fall back to a server-side default
  if omitted — don't invent endpoint IDs.
