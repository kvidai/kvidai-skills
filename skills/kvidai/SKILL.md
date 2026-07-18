---
name: kvidai
description: >
  Run a kvid.ai model end-to-end with the kvidai CLI. Use this when the user
  asks to generate an image, video, or audio; convert media; upscale or
  restyle; run any kvid.ai model; or "use kvidai" for a task. Guides
  discovery, schema inspection, input preparation, execution, and result
  handling.
---

# kvidai workflow

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

Use this skill when the user wants to execute a kvid.ai model — either by
task description (e.g. "generate a video of a dog running") or by a specific
`endpoint_id` (e.g. `kvid-ai/flux/dev`). Load `kvidai-ref` alongside this
skill for the full command reference.

## Steps

1. **Discover** — If no endpoint_id is given, search for a suitable model:
   ```
   kvidai models "<task>" --json
   ```

2. **Inspect** — Get the model's input parameters:
   ```
   kvidai schema <endpoint_id> --json
   ```
   Read all required fields before running.

3. **Upload files** (if inputs include images/video/audio):
   ```
   kvidai upload <local_file_or_url> --json
   ```
   Use the returned `url` as the parameter value.

4. **Run** the model:
   - Fast model (completes in seconds):
     ```
     kvidai run <endpoint_id> --<param> <value> ... --json
     ```
   - Slow model (video generation, large jobs):
     ```
     kvidai run <endpoint_id> --<param> <value> ... --async --json
     kvidai status <endpoint_id> <request_id> --result --json
     ```

5. **Save outputs** — when the user expects files on disk, add `--download`
   to `run` or `status`. The CLI writes every media URL from the result to
   the filesystem and returns the local paths in `downloaded_files[]`. Do
   **not** `curl` the URLs yourself; use the flag.
   ```
   kvidai run kvid-ai/flux/dev --prompt "a cat" --download --json                            # cwd, source file names
   kvidai run kvid-ai/flux/dev --prompt "a cat" --num_images 3 --download "./out/{index}.{ext}" --json
   kvidai status <endpoint_id> <request_id> --download ./out/ --json                        # implies --result
   ```
   Use `{index}`, `{name}`, `{ext}`, `{request_id}` placeholders in the
   template when the model returns multiple files (`images[]`,
   `image_urls[]`, etc.) to avoid filename collisions. A trailing `/` or
   an existing directory path saves files under that directory using their
   source names.

6. **Return** the result to the user. If `--download` was used, reference
   the paths from `downloaded_files[]`; otherwise present the URLs from
   `result` clearly.

## Handling errors

When a command exits non-zero, it prints a JSON error object to stderr:

```json
{
  "error": "Validation error — num_images: Input should be less than or equal to 4",
  "details": {
    "endpoint_id": "kvid-ai/flux/schnell",
    "request_id": "019d...",
    "status": 422,
    "error_type": "ValidationError",
    "validation_errors": [
      { "field": "num_images", "message": "Input should be less than or equal to 4", "type": "less_than_equal", "input": 20 }
    ],
    "body": { "detail": [ ... raw FastAPI payload ... ] }
  }
}
```

- `status: 422` / `error_type: "ValidationError"` means the inputs violated
  the model schema. Read `details.validation_errors` — each entry names the
  `field`, a human `message`, the validator `type`, and the `input` that was
  rejected. Re-run `kvidai schema <endpoint_id> --json` if you need the
  allowed values, fix the offending args, and retry.
- Other statuses (401 auth, 403 forbidden, 404 endpoint not found, 429 rate
  limited, 5xx upstream) surface the server message directly in `error` and
  do not contain `validation_errors`. Do not retry 4xx errors blindly —
  correct the request first.
- For in-flight model failures, `details.logs` contains the most recent
  model-side log lines.

## Notes

- Always use `--json` so output is machine-readable.
- Run `kvidai pricing <endpoint_id> --json` first if cost is a concern.
- If unsure which model to pick, run `kvidai docs "<task>" --json` for
  guidance from kvid.ai documentation.
