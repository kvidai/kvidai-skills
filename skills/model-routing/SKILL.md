---
name: model-routing
description: >
  Explains kvidai's --model handling for image/video generation. Use this
  with commercial, character-design, cinematography, storytelling, and
  workflow when deciding whether to pass --model.
---

# kvidai model handling

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

kvidai does **not** expose a model catalog or per-model schema through the
CLI — there is no `models`/`schema`/`pricing` command and no list of valid
`--model` IDs to browse or verify. `kvidai image generate` and
`kvidai video t2v` / `video generate` all accept an optional `--model <id>`
string that is passed through as-is to the server.

## Rule

1. **Default**: omit `--model` entirely. The server picks a sensible
   default for the command.
2. **Only** pass `--model <id>` if the user explicitly names a specific
   model ID they already know (e.g. from the kvid.ai dashboard or product
   docs) — never invent or guess one.
3. There is no way to verify a `--model` value ahead of time from the CLI.
   If an invalid ID is passed, the command fails with a normal error (see
   `kvidai`'s "Handling errors" section) — surface that to the user rather
   than retrying with a guessed alternative.

## What the other production skills should do instead

The domain skills (`commercial`, `character-design`, `cinematography`,
`storytelling`, `workflow`) previously routed to specific fal.ai endpoint
IDs per use case (text-heavy image work, premium stills, fast drafts,
highest-quality video, lip-sync, etc.). None of that applies to kvidai:
there's no equivalent tier of selectable models exposed via this CLI.

When those skills need a "which model" decision, the answer is simply:
don't pass `--model` unless the user names one. Any quality/style guidance
belongs in the **prompt** (`image generate <prompt>`, `video t2v <prompt>`)
instead of a model choice — e.g. describe "high detail, sharp text" in the
prompt rather than picking a text-optimized model, since there isn't one to
pick via this CLI.
