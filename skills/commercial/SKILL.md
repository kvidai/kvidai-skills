---
name: commercial
description: >
  Plan and run commercial image or video production with kvidai. Use this
  for product photography, ads, e-commerce batches, product reveals,
  lifestyle commercials, social formats, and brand-safe prompt work.
---

# Commercial production with kvidai

> **Requires**: the [kvidai CLI](https://github.com/kvidai/kvidai-cli) installed locally (`kvidai --version` to check).

Use this skill when the user wants advertising, product, brand, or e-commerce
media. Load the reference files when you need prompt patterns or category
examples:

- `references/prompt-patterns.md`
- `references/workflows.md`
- `references/examples.md`

Keep the output production-focused. Do not add inflated marketing language,
unsupported claims, fake text in the image, or em dashes.

## Important limitation

`kvidai image generate` and `kvidai video t2v` are text-to-media only — no
reference-image input, no background-removal/edit endpoint, no seed. "Keep
the uploaded product exactly unchanged, replace only the background" is a
prompt pattern you can *try*, but nothing in the CLI guarantees the product
in the output actually matches an uploaded reference — there's no mechanism
to feed that reference image into `image generate` at all. Say this
plainly if the user needs guaranteed product fidelity from a real photo;
the closest option is attaching the reference to a project agent turn
(`kvidai video generate <projectId> <message> --cdn-url <url>`), best
effort only.

## Inputs to collect

Only ask when the answer cannot be inferred from the task or the source files.

- Product: exact product name, category, material, color, scale, logo rules.
- Goal: hero shot, PDP image, ad creative, motion reveal, demo, UGC, lifestyle.
- Platform: square, vertical, landscape, banner, transparent background, print.
- Brand: premium, playful, clinical, athletic, minimal, natural, technical.
- Constraints: preserve packaging, avoid new labels, no fake readable copy.

## kvidai workflow

1. Build the prompt using the order below — product invariant first.

2. Still image:
   ```bash
   kvidai image generate "<commercial prompt>" \
     --size square --output ./outputs/commercial/hero.png --json
   ```
   Use `--num <n>` for a few variants of the same concept in one call.

3. Product reveal / motion video:
   ```bash
   kvidai video t2v "<motion prompt>" --duration 8 \
     --wait --output ./outputs/commercial/reveal.mp4 --json
   ```

4. E-commerce batch — no built-in batching, so run the still command once
   per variant, changing only the output path and the one varied dimension
   (background, crop, lighting) in the prompt:
   ```bash
   kvidai image generate "<prompt, white background>" --output ./outputs/commercial/v1-white.png --json
   kvidai image generate "<prompt, brand-color background>" --output ./outputs/commercial/v2-brand.png --json
   ```

Don't pass `--model` unless the user names a specific model ID — see the
`model-routing` skill.

## Prompt build order

Write prompts in this order so commercial intent stays clear:

1. Product invariant: exact object, material, color, packaging, scale.
2. Commercial role: hero image, PDP image, launch teaser, demo shot, social ad.
3. Setting: surface, background, props, environment, distance from product.
4. Lighting: softbox, strip light, rim light, backlight, caustics, practicals.
5. Camera: angle, focal length feel, macro, depth of field, motion if video.
6. Composition: centered, negative space, safe zone, text-free area, platform.
7. Brand tone: premium, clean, clinical, bold, energetic, warm, editorial.
8. Guardrails: preserve logo and packaging, no extra text, no distorted labels.

Do not promise claims like "best", "clinically proven", "50 percent faster",
or celebrity endorsements unless the user provides that copy.

## Quality bar

Before returning, check:

- Product shape, logo, material, and color match what was described in the
  prompt (there's no reference-image constraint to fall back on — if
  fidelity is critical, tell the user this CLI can't guarantee it).
- The composition leaves enough room for platform crop and optional copy.
- Background props support the product and do not compete with it.
- Any generated text is absent or intentionally controlled.
- Lighting makes sense for the product material.

If the result misses product fidelity and the user has a real product
photo, be upfront that text-to-image generation can't lock onto it — the
best available option is the project-agent attachment path above, and even
that isn't a guaranteed edit.
