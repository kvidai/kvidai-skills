---
name: cinematography
description: >
  Design cinematic image and video prompts for kvidai. Use this for shot
  language, camera movement, lighting, lens choices, color grade, film
  texture, scene blocking, and production-ready visual direction.
---

# Cinematography with kvidai

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

Use this skill when the user needs cinematic direction, not generic "make it
cinematic" prompting. Load references as needed:

- `references/shot-language.md`
- `references/lighting-lens-color.md`
- `references/examples.md`

Write concrete visual direction. Avoid empty prestige words and em dashes.

## Important limitation

`kvidai image generate` and `kvidai video t2v` are text-to-media only — no
reference/first-frame image input, no seed. Continuity language like "same
lighting direction throughout" or "continue from the uploaded first frame"
(see `references/shot-language.md`) works only within a *single* prompt's
description of a continuous shot — it cannot bind to a previously generated
image or an uploaded frame the way an image-to-video model would. If the
user needs true first-frame continuity, say so plainly; the closest option
is attaching a frame to a project agent turn (`kvidai video generate
<projectId> <message> --cdn-url <url>`), which is best-effort.

## Inputs to collect

Ask only for what affects the shot:

- Subject and action.
- Medium: still image or video.
- Genre and mood.
- Framing: close-up, medium, wide, overhead, POV, profile, locked-off.
- Camera motion for video: push-in, dolly, tracking, handheld, crane, drone.
- Lens feel: wide, normal, telephoto, macro, shallow or deep focus.
- Lighting: natural, practical, studio, noir, high key, low key, backlit.
- Output: aspect ratio (via `--size` for images), duration (video), output path.

## kvidai workflow

1. Build the prompt using the SCLCAM structure below.

2. Still image:
   ```bash
   kvidai image generate "<cinematography prompt>" \
     --size landscape_16_9 --output ./outputs/cinema/shot.png --json
   ```

3. Video, standalone:
   ```bash
   kvidai video t2v "<shot prompt>" --duration 8 \
     --wait --output ./outputs/cinema/shot.mp4 --json
   ```

4. Video, inside a project (multi-turn, can reference an uploaded frame —
   best effort, see limitation above):
   ```bash
   kvidai upload ./frame.png --json
   kvidai video generate <projectId> "<shot prompt>" \
     --cdn-url <cdnUrl> --mime image/png --verbose --json
   ```

Don't pass `--model` unless the user names a specific model ID — see the
`model-routing` skill.

## Prompt build order

Use the SCLCAM structure:

1. Subject: who or what is in frame.
2. Context: location, time, weather, story moment.
3. Lens/framing: distance, angle, focal length feel, depth of field.
4. Camera motion: only for video or if motion blur is desired.
5. Atmosphere: haze, rain, practicals, reflections, texture.
6. Mood/color: palette, contrast, grade, exposure style.
7. Output controls: aspect ratio, duration.

Example structure:

```text
[subject] in [context], framed as [shot size and angle], [lens feel],
[lighting setup], [camera movement if video], [color grade], [texture],
[duration or aspect ratio], [continuity constraints]
```

## Quality bar

Before returning, check:

- Camera movement is physically plausible for the scene.
- Lens, shot size, and camera angle do not contradict each other.
- Lighting direction is clear and consistent.
- Color grade supports the mood without flattening subject detail.
- Video prompt describes one continuous shot — there's no multi-shot list
  control on this CLI.

If a result looks generic, improve specificity in camera, blocking, light, and
environment before adding more adjectives.
