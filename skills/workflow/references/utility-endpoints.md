# Utility endpoints — not available on kvidai

This file used to list fal.ai `workflowutils/*` / `workflow-utilities/*`
endpoint IDs (resize, crop, composite, segmentation, subtitles, audio
mix, etc.). None of these exist on kvidai — the CLI has exactly two
generation commands (`image generate`, `video t2v` / `video generate`) and
no utility-endpoint layer at all.

If a task needs resize, crop, composite, overlay, grid layout,
segmentation, background removal, subtitles, transcription, TTS, audio
mixing, upscaling, compression, or format conversion: **tell the user this
CLI can't do it** and suggest an appropriate external tool (ffmpeg, an
image library, a captioning tool) for that specific step. Don't invent an
endpoint ID to fill the gap.

See `SKILL.md`'s "Important limitation" section and `node-rules.md`'s
"What does NOT exist" list for the full picture.
