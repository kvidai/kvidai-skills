# Usage

## Dependencies

Python 3.10+ and Pillow (`python -m pip install Pillow`) are required. Install FFmpeg and ffprobe using the operating system's package manager or an FFmpeg distribution and place both executables on PATH. On Linux use `python3` if `python` is unavailable.

Check the runtime before processing:

```sh
python skills/video-frame-analysis/scripts/extract_frames.py --check
```

No shell-specific commands are executed by the script. Subprocess arguments are passed as lists, including paths with spaces or Korean characters.

## Windows PowerShell

From a checkout of kvidai-skills:

```powershell
python .\skills\video-frame-analysis\scripts\extract_frames.py "C:\media\한글 레퍼런스.mp4" --output "C:\media\analysis-motion" --mode motion
python .\skills\video-frame-analysis\scripts\extract_frames.py "C:\media\한글 레퍼런스.mp4" --output "C:\media\analysis-scene" --mode scene
python .\skills\video-frame-analysis\scripts\extract_frames.py "C:\media\한글 레퍼런스.mp4" --output "C:\media\analysis-dense" --mode dense --interval 0.1 --max-frames 200
```

## Linux

```sh
python3 skills/video-frame-analysis/scripts/extract_frames.py '/data/한글 레퍼런스.mp4' --output '/data/analysis-motion' --mode motion
python3 skills/video-frame-analysis/scripts/extract_frames.py '/data/한글 레퍼런스.mp4' --output '/data/analysis-scene' --mode scene
python3 skills/video-frame-analysis/scripts/extract_frames.py '/data/한글 레퍼런스.mp4' --output '/data/analysis-dense' --mode dense --interval 0.1 --max-frames 200
```

Installed skills have the same internal script path. For example, an APM Codex installation typically places it under `.agents/skills/video-frame-analysis/scripts/`. Resolve the actual installed Skill location rather than assuming a fixed harness layout.

## Options and selection

| Option | Default | Behavior |
|---|---|---|
| `--mode` | `motion` | `motion`, `scene`, or `dense` |
| `--interval` | motion: 0.5, dense: 0.25 seconds | Temporal coverage spacing; unused by scene mode |
| `--max-frames` | 80 | Hard output image cap, minimum 2; a one-frame input outputs one image |
| `--scene-threshold` | 0.22 | Normalized adjacent grayscale mean absolute difference in (0,1] |
| `--motion-threshold` | 0.025 | Minimum change for motion peak candidates in (0,1] |
| `--min-gap` | 0.25 seconds | Minimum spacing between detected scene peaks or motion peaks |
| `--check` | off | Print dependency versions without processing a video |

Every decoded frame is compared at 96×54 grayscale resolution. Local maxima above the scene threshold suggest scene changes; lower the threshold for subtle cuts. Fast pans, flashes and transitions may also trigger it, while equal-brightness changes may be missed. This is not an optical-flow or semantic detector. Original-resolution PNGs are extracted after selection, with FFmpeg's normal orientation handling.

For motion mode, the script adds peaks and nearest frames half a `--min-gap` before/after each peak. Scene mode selects a frame nearest each inferred scene's temporal midpoint. Dense/motion coverage uses nearest actual presentation timestamps, so variable frame rates are supported without guessing frame numbers from FPS. Times are normalized to the first decoded video frame; `video.first_pts_seconds` preserves the original PTS offset. Reported stream dimensions are coded dimensions, which can differ from orientation-corrected PNG dimensions.

Duplicates are merged by source frame number. When a cap is reached, priority is first/last, cut candidates, interval samples or scene representatives, motion peaks, then surrounding motion frames. Oversized groups are sampled across time. Read the truncation warning: a cap may omit some transition pairs or motion details. Shorten the interval and raise the cap for more coverage. Dense mode still cannot recover events between its samples unless a transition was detected.

## Outputs

| File | Contents |
|---|---|
| `frames/frame_*.png` | Ordered images; filenames contain order, zero-based source frame number and timecode |
| `contact-sheet-001.jpg`, etc. | Up to 20 numbered, timestamped thumbnails per page |
| `index.md` | Sheet previews and links to each selected image with reasons |
| `frames.json` | Version 1 report: input path and SHA-256, versions, configuration, video metadata, detected scene changes, warnings, and selected frames |
| `frames.csv` | One row per selected frame with order, time, path, change score and reasons |

The input is never modified. The destination must not exist, even if empty. Outputs are prepared in a sibling temporary directory and moved into place only after successful completion. Errors return nonzero with a diagnostic; missing tools, invalid thresholds/intervals, no video stream, unusable timestamps and decoding failures do not produce a successful report. Python JSON/Markdown/CSV output uses UTF-8.

Analysis decodes all frames and probes their timestamps. Runtime scales with video length; `--max-frames` limits exported images, not decoding cost. Do not represent a successful extraction as visual inspection: open the contact sheets and relevant images before giving a visual analysis.

## APM distribution

For another local project to use this unpublished checkout, add a local dependency entry to that project's existing `dependencies.apm` list, then run `apm install` in that project:

```yaml
dependencies:
  apm:
    - path: C:/workspace/kvidai-skills/skills/video-frame-analysis
```

On Linux use the checkout's absolute Linux path instead. Existing dependencies and targets should be preserved. Re-run installation after changing the source; installed files are deployment outputs, not the development source.

The skill is self-contained within `skills/video-frame-analysis/`, following this repository's existing skill bundle layout. Once this change is published to the repository, a consumer can select it with:

```sh
apm install kvidai/kvidai-skills --skill video-frame-analysis --target claude,codex
```

This installs the skill files; Python, Pillow and FFmpeg remain local runtime dependencies. Local development does not automatically update a consumer pinned to an earlier remote commit. Publishing and consumer updates are separate operations.
