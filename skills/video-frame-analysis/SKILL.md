---
name: video-frame-analysis
description: Extract ordered video frames and contact sheets for visual reference analysis, motion study, scene inspection, or dense sampling of a local video.
metadata:
  tags: video, frames, reference, motion, local
---

# Video frame analysis

Requires Python 3.10+, Pillow, FFmpeg and ffprobe on PATH. Runs locally on Windows and Linux; no kvidai CLI, account or API key is needed.

Use the script shipped with this skill, resolving its path relative to this `SKILL.md`, not a hardcoded project directory:

```text
python <skill-directory>/scripts/extract_frames.py <video> --output <new-directory> --mode motion
```

Choose the mode according to the user's purpose:

- `motion`: temporal coverage plus change peaks and surrounding frames; useful for typography, composition and movement studies.
- `scene`: pixel discontinuities, frames immediately before/after them, and a representative of each inferred scene.
- `dense`: regular time samples plus transition frames. Use a shorter `--interval` when brief events are missed.

Run `--check` to diagnose dependencies. See [usage and output reference](references/usage.md) for setup, platform commands and tuning.

Read `index.md` and the ordered contact sheets first; open individual PNGs to inspect details or ambiguous transitions. `frames.json` provides source frame numbers, timestamps and selection reasons. Inspect consecutive images before describing motion; isolated stills cannot establish its trajectory. These results cover visual analysis, not audio review.

All modes include first/last decoded frames. The frame cap can omit intermediate events; inspect warnings and increase the cap or reduce the interval as needed. Pixel-change scores are candidate heuristics, not semantic action recognition. Report meaningful gaps rather than claiming that every action or cut was detected.

Keep reference outputs beside the user's campaign or in an explicit output directory. The script refuses existing output directories. Use a new directory for each run; do not delete user results to work around the refusal.
