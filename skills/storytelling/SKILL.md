---
name: storytelling
description: >
  Build multi-shot narrative image and video sequences with kvidai. Use
  this for storyboards, shot lists, social stories, brand films, and
  sequence continuity.
---

# Storytelling with kvidai

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

Use this skill when the user wants a sequence, not a single asset. Load
references as needed:

- `references/shot-planning.md`
- `references/workflows.md`
- `references/examples.md`

The goal is to produce clear story beats and executable kvidai runs. Avoid
generic inspiration copy, fake dialogue, and em dashes.

## Important limitation

kvidai has no multi-shot/timeline API, no first-frame/last-frame input, no
audio generation command, and no way to guarantee cross-shot identity
beyond repeating the same continuity-anchor text in every shot's prompt.
Every shot is a **separate, independent** `image generate` or `video t2v`
call — there is no stitching, no shared seed, and no reference passed
between shots. Set expectations accordingly: this produces a set of
individually strong clips/stills for the user (or an editor) to assemble,
not a single continuous rendered sequence.

## Inputs to collect

Ask only when missing information affects execution.

- Format: ad, short film, music video, documentary, tutorial, social story.
- Duration and aspect ratio per shot.
- Number of shots or allowed range.
- Main subject, character, product, or location.
- Continuity anchors: character, product, wardrobe, environment, color.

## kvidai workflow

1. Plan the sequence as beats (see "Shot planning" below), then write one
   prompt per shot using the anchor + variable structure.

2. Generate each shot independently:
   ```bash
   kvidai video t2v "<shot prompt>" --duration 5 \
     --wait --output ./outputs/story/shot-01.mp4 --json
   kvidai video t2v "<shot prompt>" --duration 4 \
     --wait --output ./outputs/story/shot-02.mp4 --json
   ```
   For a still-image storyboard instead of video, use `kvidai image
   generate "<shot prompt>" --output ./outputs/story/shot-01.png --json`.

3. Return a shot table with duration, prompt summary, local path, and any
   continuity issues. kvidai does not assemble the shots into one file —
   say so, and point the user at an editor if they need one.

Don't pass `--model` unless the user names a specific model ID — see the
`model-routing` skill.

## Shot planning

Plan every sequence as beats first:

1. Hook: immediate visual reason to keep watching.
2. Setup: who, what, where, and why it matters.
3. Development: movement, discovery, proof, or escalation.
4. Turn: reveal, transformation, result, or emotional change.
5. Close: final image, product memory, CTA-safe frame, or unresolved mood.

For each shot, write:

- Shot number and duration.
- Story purpose.
- Visual prompt (including the continuity anchor, repeated verbatim).
- Expected output path.

## Prompt build order

Use this structure for each shot:

```text
SHOT [number], [duration]:
[story purpose]. [subject and action]. [location and time]. [camera framing].
[camera movement]. [lighting and color]. [continuity anchor]. [transition or
relationship to previous shot, described in words — not actually linked].
```

Keep one shot to one clear action — there's no multi-shot prompting on this
CLI.

## Quality bar

Before returning:

- Shot order has a clear narrative function.
- The first shot is strong enough for the platform.
- Continuity anchors are repeated in every shot's prompt, not assumed.
- Camera motion is varied but not random.
- Durations add up to the requested runtime.
- Every output path is recorded and actually exists on disk.
