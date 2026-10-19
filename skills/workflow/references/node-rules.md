# Plan item rules

kvidai has no node/pipeline API — "node" here just means one entry in your
plan, i.e. one `image generate` or `video t2v` call. These are guidelines
for writing that plan, not a schema to fill in.

## Planner

- Produce a flat list of assets (not a graph — there are no dependencies
  between kvidai calls beyond order of execution).
- Output must be structured enough to execute without interpretation
  drift: id, command (`image generate` / `video t2v` / `video generate`),
  prompt, output path.
- Keep creative planning separate from the exact prompt text you'll send.

## Image generation

- One prompt, one call, one output file. No aspect-ratio/count control
  beyond `--size` and `--num`.
- Don't route to a specific `--model` unless the user names one — see
  `model-routing`.
- For product or character continuity, repeat the exact anchor/invariant
  text in every prompt — there is no reference-image or seed input to lean
  on instead.

## Video generation

- `video t2v` is text-to-video only — no reference frame, no seed, no
  multi-shot input.
- `video generate <projectId> <message>` is the only way to attach a file
  (`--cdn-url`) as context, and it drives a project-editing AI agent, not
  a deterministic image/video-edit tool. Treat its output as best-effort.
- Keep motion prompts short and physically specific (subject motion,
  camera motion, ambient motion).

## What does NOT exist — don't plan these as steps

- Image editing / background replacement / inpainting.
- Resize, crop, composite, overlay, grid layout.
- Segmentation, masking, edge detection.
- Subtitle generation, transcription, TTS, audio mixing/merging.
- Upscaling, compression, format conversion.
- Stitching/merging separate clips into one file.

If the deliverable needs any of the above, tell the user this CLI can't do
it and suggest an external tool (ffmpeg, an image editor, a captioning
tool) for that specific step.

## QA

Use a manual or vision-based check after each generation:

- Identity preserved (if a character/product anchor was used).
- Text is absent or intentional (there's no way to control in-image text
  precisely).
- Clip duration matches the plan.
- Output file actually exists at the recorded path.

## Manifest

Return a compact manifest at the end:

```json
{
  "asset_id": "shot_03",
  "command": "video t2v",
  "prompt_summary": "short summary",
  "output_path": "./outputs/workflow/shot_03.mp4",
  "status": "accepted | retried | rejected",
  "notes": "short defect or continuity note"
}
```

Keep manifests factual. Do not include promotional copy.
