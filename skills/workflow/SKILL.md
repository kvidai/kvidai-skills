---
name: workflow
description: >
  Plan and execute a sequence of independent kvidai generation calls for a
  multi-asset deliverable (batches, variant sets, campaigns). Use this when
  a single image/video call is not enough.
---

# Workflow production with kvidai

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

Use this skill when the deliverable needs several generated assets planned
and tracked together. Load references as needed:

- `references/pipeline-patterns.md`
- `references/node-rules.md`
- `references/recipes.md`

## Important limitation — read before planning anything

kvidai's CLI has exactly two generation commands (`image generate`,
`video t2v` / `video generate`) and **no utility-endpoint layer at all**:
no resize, crop, composite, overlay, grid, segmentation, background
removal, subtitle, TTS, audio mix/merge, or format-conversion command.
There is no multi-node pipeline API, no shared seed, and no way to pass one
generation's output as another's structured input (only a whole prompt or
a `--cdn-url` attachment to a project agent turn).

This means a "workflow" here is just: **plan a list of independent
`image generate` / `video t2v` calls, run them, and hand the user the raw
outputs.** Anything past that — compositing, cropping, subtitles, audio,
stitching clips together — is **not achievable with this CLI**. Tell the
user plainly and point them to an external tool (ffmpeg, an image editor,
a captioning tool) rather than inventing an endpoint that doesn't exist.
`references/utility-endpoints.md` has been removed for this reason — see
its replacement note if you're looking for it.

## Inputs to collect

Ask only for missing information that changes the plan:

- Final deliverable: image set, batch of clips, variant matrix, campaign
  assets.
- Source description per asset (no file inputs beyond one optional
  `--cdn-url` attachment per `video generate` project turn).
- Runtime limits: number of variants, duration per clip, deadline.
- Continuity requirements: repeat the same anchor/invariant text across
  calls (see `character-design` / `commercial` for anchor patterns).

## Core workflow

1. Write a short plan before running anything: a list of assets, each with
   a purpose, a prompt, and an output path. No graph beyond this list — there
   are no dependent "nodes" to wire up.

2. Generate each asset independently:
   ```bash
   kvidai image generate "<prompt 1>" --output ./outputs/workflow/asset-01.png --json
   kvidai image generate "<prompt 2>" --output ./outputs/workflow/asset-02.png --json
   kvidai video t2v "<prompt 3>" --duration 6 --wait --output ./outputs/workflow/asset-03.mp4 --json
   ```
   Independent assets can be requested one after another — there's no
   parallelism or job queue to manage; each command just runs to
   completion (or returns a `jobId` to poll with `kvidai task status`).

3. Don't pass `--model` unless the user names a specific model ID — see
   the `model-routing` skill.

4. Return a compact manifest:
   ```json
   {
     "goal": "short deliverable description",
     "assets": [
       {
         "id": "asset_01",
         "command": "image generate",
         "prompt_summary": "...",
         "output_path": "./outputs/workflow/asset-01.png",
         "notes": "continuity or defect notes"
       }
     ]
   }
   ```

## Plan rules

- One item in the plan = one `image generate` or `video t2v` call. There
  is no such thing as a resize/crop/composite/subtitle "node" — don't plan
  one.
- For consistency across assets, repeat the exact same anchor/invariant
  text in every prompt (see `character-design`, `commercial`).
- If the user's request genuinely needs post-processing (crop, resize,
  merge, subtitles, audio), say clearly that the kvidai CLI can't do it and
  suggest an external tool for that step — don't fabricate a command.
- Record output path and notes for every asset.

## Quality gate

Before returning, verify:

- The plan matches the requested deliverable using only `image generate` /
  `video t2v` / `video generate`.
- No non-existent command or endpoint was invented.
- All local output paths actually exist on disk.
- Continuity anchors were repeated where identity or product fidelity
  matters.
- Each asset is either accepted, retried, or marked with a defect.
- Any post-processing step the user needs beyond generation was flagged as
  out of scope for this CLI, not silently skipped.
