# Workflow recipes

Every recipe below only uses independent `image generate` / `video t2v` /
`video generate` calls — no editing, compositing, or utility step exists
on this CLI. Where the original idea needed one of those, the recipe says
so and drops or substitutes it.

## Multi-scene video

Input: concept, style, duration per shot.

```text
1. Planner creates N shots, each with a full prompt (subject, action,
   setting, camera, continuity anchor).
2. Generate each shot independently with `video t2v`.
3. Return a shot manifest in playback order.
```

No start/end-frame interpolation and no clip merging — the user (or an
external editor) assembles the final sequence. Use `storytelling` and
`cinematography` for shot language.

## Product campaign

Input: product description, brand tone, deliverables.

```text
1. Write the product invariant (see `commercial`).
2. Generate the hero image with `image generate`.
3. Generate one variant per platform format by changing `--size` and
   restating the invariant in each prompt (square, portrait, landscape).
4. Generate one product reveal clip with `video t2v`.
5. Return a campaign manifest with all output paths.
```

There is no reference-image edit step — if the user has a real product
photo they need matched exactly, tell them this CLI can't guarantee that
(see `commercial`'s limitation note). Text overlays need an external
design tool, not this CLI.

## Character continuity sequence

Input: character description, scene list.

```text
1. Build the character anchor (see `character-design`).
2. Generate one still or clip per scene, repeating the anchor verbatim in
   every prompt.
3. Reject outputs with face, hair, wardrobe, or age drift.
4. Return shot order and output paths.
```

No image-to-video-from-approved-still — each shot is independently
generated from text.

## Dataset generator

Input: task definition and target count.

```text
1. Planner creates N diverse prompts.
2. Generate one image per prompt with `image generate`.
3. Write captions/metadata by hand from the actual output (no
   auto-captioning command exists).
4. Return pairs: prompt, output path, caption.
```

No original→transformed pairs — there's no edit endpoint to produce the
"transformed" half; only independent original generations.

## Style exploration

Input: target style description.

```text
1. Build a variation matrix with one changed axis per row (see
   `pipeline-patterns.md`).
2. Generate one image per row with `image generate`.
3. Return a selection table: axis, output path, notes.
```

No edit-based variation from a reference asset — every variant is an
independent text-to-image call.

## Social media batch

Input: master creative brief, target platforms.

```text
1. Write the base prompt once.
2. Generate one `image generate` call per platform, using the matching
   `--size` preset (square, portrait_4_3/16_9, landscape_4_3/16_9) instead
   of resizing after the fact.
3. Return outputs grouped by platform.
```

No resize/crop/compress utility — each platform format is a separate
generation, not a post-process of one master asset. Don't rely on
generated in-image text for final ad copy; add text externally.
