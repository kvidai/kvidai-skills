# Storytelling workflows

There is no multi-prompt/timeline API on this CLI — every workflow below
reduces to running `video t2v` (or `image generate`) once per shot,
independently, with continuity carried only by repeating anchor text.

## Manual per-shot video

The only way to build a sequence with this CLI.

1. Create a shot table (see `shot-planning.md`).
2. Write one prompt per shot, repeating the continuity anchor verbatim in
   each.
3. Generate each shot separately, with a distinct `--output` path:
   ```bash
   kvidai video t2v "<shot 1 prompt>" --duration 4 --wait --output ./outputs/story/shot-01.mp4 --json
   kvidai video t2v "<shot 2 prompt>" --duration 5 --wait --output ./outputs/story/shot-02.mp4 --json
   ```
4. Record duration, prompt, local output path, and defects per shot.
5. Return clips in timeline order. Do not claim they are stitched — kvidai
   does not combine them into one file.

## Character narrative

1. Use `character-design` to build the anchor.
2. Repeat the exact anchor text in every shot's prompt (no reference-image
   or seed mechanism exists to enforce this automatically).
3. Compare each result to the anchor before advancing to the next shot —
   drift is likely since nothing binds the shots together besides the text.

## Product narrative

1. Use `commercial` to define product invariants.
2. Plan the sequence around hook, feature, context, proof, final frame.
3. Repeat the exact product-invariant text in every shot's prompt.
4. Keep motion modest when packaging fidelity matters — there's no
   reference image to fall back on if a shot drifts.

## Audio

kvidai's CLI has **no audio generation command** — no narration, music, or
sound-design endpoint. If the user needs a voiceover or soundtrack, say so
plainly and point them to a separate tool; don't imply this skill can
produce it.
