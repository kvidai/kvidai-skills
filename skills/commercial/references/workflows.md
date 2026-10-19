# Commercial workflows

## Hero image from a product description

1. Collect the product invariant: exact object, material, color, packaging,
   scale, logo rules.
2. Prompt for surface, lighting, crop, and background. Keep the product
   invariant short and exact.
3. Generate:
   ```bash
   kvidai image generate "<prompt>" --size square --output ./outputs/commercial/hero.png --json
   ```
4. Reject outputs with altered logos, warped packaging, or invented text.

If the user has an actual product photo and needs the output to match it
exactly, be upfront that `image generate` has no reference-image input —
see the "Important limitation" note in `SKILL.md`.

## Text-to-image product concept

Use when no reference exists or the user wants early creative exploration.

1. Ask or infer product category, materials, and brand tone.
2. Generate 2 to 4 controlled variants with `--num <n>` (single prompt) or
   by repeating the command with a slightly reworded prompt.
3. Keep each variant different by one dimension only: background, lighting,
   camera angle, or prop set.
4. Pick the strongest frame before moving to video or a batch.

## Product reveal video

1. Write a motion prompt: opening frame, camera movement, what the product
   does (rotate, reveal, pour, unwrap), lighting change.
2. Generate:
   ```bash
   kvidai video t2v "<motion prompt>" --duration 8 --wait --output ./outputs/commercial/reveal.mp4 --json
   ```
   Omit `--wait --output` to get a `jobId` back immediately instead, then
   poll with `kvidai task status <jobId> --wait --output <path> --json`.
3. Keep motion simple: push-in, turntable, parallax, reveal, pour, unwrap.
4. If the product changes shape or identity across the clip, simplify the
   motion description and make the product invariant more specific.

## E-commerce batch

There's no batch/matrix command — run `image generate` once per variant.

1. Build a base prompt with exact product invariants.
2. Create a small matrix: white background, brand-color background, lifestyle,
   scale/detail, packaging close-up.
3. Use a distinct `--output` path per variant (e.g. `v1-white.png`,
   `v2-brand.png`).
4. Return a table of output path, concept, and notable defects.

## Ad creative set

Produce separate assets for:

- Hook frame: product and benefit visible in under one second.
- Proof frame: product detail, ingredient, feature, texture, or before-after.
- Lifestyle frame: human or environmental context.
- Conversion frame: clean safe-zone layout for external text and CTA.

Generate each as its own `image generate` call with its own `--output` path.
Do not generate legal claims, pricing, discounts, or health claims unless the
user supplies the exact copy.
