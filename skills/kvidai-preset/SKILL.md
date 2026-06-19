---
name: kvidai-preset
description: Use when you need to call the kvidai Preset API (api.kvid.ai/preset) — list, get, create, update, delete, or duplicate the reusable presets that seed new video projects (voice, tone, color palette, scene defaults). Triggers on preset CRUD, presetId lookup, system_default fallback, default preset toggle, 프리셋 등록, 프리셋 조회, 프리셋 수정. Replaces the older video-template skill — Strapi has split video_template into video_preset (this) plus shared_composition (gallery).
metadata:
  tags: kvidai, preset, video, crud, apim
---

The kvidai Preset API is a public REST surface on `api.kvid.ai/preset` (Azure APIM) that wraps the Strapi `video_preset` collection. Presets seed new video projects with voice / tone / color / scene defaults — they're what makes an empty project start with sensible AI behavior instead of generic defaults.

The client lives at `.claude/skills/kvidai-preset/scripts/kvidai-preset-client.mjs` and runs with plain `node` (no tsx required).

All paths below are relative to the **kvidai monorepo root**.

## Concepts

| Field | Meaning |
|-------|---------|
| `presetId` | Human-friendly external identifier (e.g. `review-owl`, `system_default`). Used by clients in URLs and agent body. Unique. |
| `isDefault` | When true, this preset is the system fallback for new projects with no template specified. Exactly one preset per locale should be marked as the default. |
| `isPublic` | Owner can publish a preset so other users can pick it from the storyboard "preset" dropdown. |
| `email` | Owner. Regular users only see their own + `isPublic` + `isDefault` rows. |
| `thumbnailUrl` | Optional preview image shown in the preset picker. |
| `tags` | Free-form labels for search/filtering. |
| `config` | The actual JSON config (voice settings, tone guides, color palette, scene-composition rules). Format described in `apps/web-service/src/lib/templates/profiles.json`. |

## Environment variables

```bash
export KVIDAI_API_KEY="<prod-preset-apim-key>"          # APIM subscription key, scope = preset product
export KVIDAI_BASE_URL="https://api.kvid.ai"            # default if not set; use https://staging-api.kvid.ai for staging
export KVIDAI_USER_EMAIL="user@example.com"             # required for some operations; scoped automatically from the APIM subscription key
```

## Run (agent path)

```bash
SKILL=.claude/skills/kvidai-preset/scripts/kvidai-preset-client.mjs

# List presets the caller can see (own + isPublic + isDefault)
node $SKILL list

# Get a single preset by numeric id
node $SKILL get 42

# Get by presetId (the human-friendly external id)
node $SKILL get-by-preset-id review-owl

# Create — pass a JSON file with { name, presetId?, description?, language?, isPublic?, thumbnailUrl?, tags?, config }
node $SKILL create ./my-preset.json

# Update fields
node $SKILL update 42 '{"name":"Renamed","isPublic":true}'

# Duplicate as a new owned preset
node $SKILL duplicate 42 "My copy"

# Delete
node $SKILL delete 42
```

## Authorization model

Auth is handled by the APIM subscription key — just carry the `KVIDAI_API_KEY`. The API auto-scopes each operation to the subscription's owner.

| Operation | What you can access |
|-----------|---------------------|
| List | Your own presets + any `isPublic` presets + the system `isDefault` preset |
| Get / GetByPresetId | Your own + `isPublic` + `isDefault` |
| Create | Owned by you; `isDefault` is always set to false |
| Update | Your own presets only |
| Delete | Your own presets only |
| Duplicate | Any preset visible to you → you own the copy; `isDefault`/`isPublic` reset to false |

## Picking a preset for a new video project

Call the [Project Management API](https://docs.kvid.ai/docs/api-services/project-management)'s `POST /api/video-project` with `templateId: "<presetId>"` (the body field name is kept as `templateId` for backwards compatibility; it accepts a presetId now). When omitted, the agent falls back to the preset marked `isDefault:true` for the project's locale, and then to the in-code locale-aware voice defaults.

## When the older video-template surface still applies

`video_template` is being phased out — its data is backfilled into `video_presets` on first migration run. New callers should use this skill. The old `kvidai-video-project` skill keeps working since the project create body still accepts the same field name (`templateId` → looked up against `video_presets.presetId`).
