---
name: character-design
description: >
  Build consistent character designs and character media with kvidai. Use
  this for original characters, reference sheets, expression sheets, outfit
  variations, and character-to-video workflows.
---

# Character design with kvidai

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

Use this skill when the user wants to create or refine a character. Load the
reference files when needed:

- `references/anchor-system.md`
- `references/prompt-patterns.md`
- `references/examples.md`

The main objective is consistency. Keep the character anchor stable and change
only the requested scene, expression, outfit, camera, or action.

## Important limitation

`kvidai image generate` and `kvidai video t2v` are **text-to-media only** —
neither accepts a reference image, a seed, or an edit input. There is no
CLI command for "edit this existing character image" or "use this image as
identity reference." Consistency across a series can only be approximated
by **repeating the exact same anchor text** in every prompt — it is not
guaranteed the way a real reference-image workflow would be. Say this
plainly to the user if they ask for a true identity-preserving edit; the
closest available option is attaching an image to a project agent turn
(`kvidai video generate <projectId> <message> --cdn-url <url>`), which is
best-effort and video-project-oriented, not a dedicated image editor.

## Inputs to collect

Only ask for missing inputs that affect identity.

- Character type: realistic human, stylized, anime, mascot, fantasy, sci-fi.
- Identity anchor: age range, face shape, hair, eyes, build, posture, marks.
- Style: photographic, 3D, illustration, manga, comic, game concept art.
- Needed outputs: portrait, full body, turnaround, expression sheet, outfit
  set, action still, video shot.
- Consistency level: exploratory, pitch-ready, production continuity (set
  expectations accordingly — see limitation above).

## kvidai workflow

1. Build the character anchor (see below), then the shot variable for what
   you're generating right now.

2. Generate a still — combine anchor + variable into one prompt:
   ```bash
   kvidai image generate "CHARACTER ANCHOR: ... SHOT VARIABLE: ..." \
     --size portrait_4_3 --output ./outputs/characters/portrait.png --json
   ```
   Use `--num <n>` to get several images from the same prompt in one call
   (e.g. for an expression sheet attempt), and `--size` to match the target
   framing (`square`, `square_hd`, `portrait_4_3`, `portrait_16_9`,
   `landscape_4_3`, `landscape_16_9`).

3. For a turnaround or expression sheet, describe the full grid in one
   prompt (see `references/prompt-patterns.md`) — the CLI has no way to
   guarantee per-panel consistency beyond the anchor text repeating within
   that single prompt.

4. Character video — text-to-video only, no image-to-video from an
   approved still:
   ```bash
   kvidai video t2v "CHARACTER ANCHOR: ... SHOT VARIABLE: <action>" \
     --duration 6 --wait --output ./outputs/characters/shot.mp4 --json
   ```

5. If the user wants to attach a reference image to steer a project (best
   effort, not a guaranteed edit):
   ```bash
   kvidai upload ./character-reference.png --json
   kvidai project create "Character work" --json
   kvidai video generate <projectId> "<anchor> — match this reference" \
     --cdn-url <cdnUrl> --mime image/png --verbose --json
   ```

Don't pass `--model` unless the user names a specific model ID — see the
`model-routing` skill.

## Character anchor

Create a short immutable anchor before generating.

```text
CHARACTER ANCHOR:
[name or codename], [age range], [face shape], [eye shape and color],
[nose and lips], [skin tone and distinguishing marks], [hair color, texture,
style], [body build and posture], [signature clothing or silhouette],
[style target]
```

Then add a variable block for the current shot.

```text
SHOT VARIABLE:
[expression], [pose/action], [outfit changes if allowed], [environment],
[camera/framing], [lighting], [mood]
```

Never rewrite the anchor casually between calls — repeating it verbatim is
the only consistency lever this CLI gives you. If a result changes
identity, strengthen the anchor with more specific, concrete detail rather
than adding vague style words.

## Quality bar

Reject or retry when:

- Face shape, eye spacing, hairstyle, marks, or body build drift.
- Outfit changes when the prompt says only expression or pose should change.
- The sheet mixes styles across panels.
- Hands or props distract from the requested design task.
- Video motion changes age, face, costume, or silhouette.

Return the output path and include the anchor used so future prompts can
reuse the same identity text.
