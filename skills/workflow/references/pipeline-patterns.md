# Pipeline patterns

kvidai has no chaining/compositing capability between calls — every
pattern below is a way to *organize independent* `image generate` /
`video t2v` calls, not a real data pipeline. Patterns that require passing
one generation's output into another as structured input (compositing,
frame bridging, start/end-frame interpolation, multi-modal audio assembly)
are **not possible** with this CLI and are omitted below — if the user
needs one of those, say so and suggest an external tool.

## Fan-out batch

Use for multi-scene video, batches, datasets, and variant exploration.

```text
planner -> structured plan (list of assets)
generate asset 1 -> save
generate asset 2 -> save
generate asset N -> save
all outputs -> return manifest
```

Rules:

- Planner output must be a structured list: id, command, prompt, output path.
- Each generation is fully independent — nothing carries over automatically
  between calls except what you repeat in the prompt text.
- Record each asset's output path.

## Systematic variation matrix

Use for product sets, style exploration, character sheets, and A/B testing.

```text
base prompt + angle A + light A -> output 1
base prompt + angle B + light A -> output 2
base prompt + angle A + light B -> output 3
```

Rules:

- Vary one controlled axis per call when analyzing results.
- Keep all identity and product constraints (the anchor text) identical
  across every call in the matrix.
- Avoid random changes when the user needs comparable outputs.
- This is the pattern that maps most directly onto kvidai's capabilities
  — it's just repeated independent calls with a controlled prompt diff.

## Multi-expert planning

Use for complex briefs with strategy, art direction, motion, and format
variation — a planning pattern, not an execution pattern.

```text
brief -> brand analysis
brand analysis -> strategist
brand analysis -> art director
brand analysis -> motion director
experts -> master prompt plan -> independent generate calls
```

Rules:

- Each expert output must be structured.
- Master plan removes repetition across angles, backgrounds, and lighting.
- Generation still means calling `image generate` / `video t2v` once per
  planned asset — this pattern only changes how you arrive at the prompts.
