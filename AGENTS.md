# kvidai-skills

Claude Code Agent Skills for the kvidai video platform.

## Directory Structure

```
kvidai-skills/
├── SKILL.md                       # Root skill hub (discovered via .claude/skills/kvidai-skills symlink)
├── skills/
│   ├── index.json                 # sha256-checksummed manifest, consumed by `kvidai skills install`
│   ├── kvidai-video-project/      # Create projects, generate videos via AI agent (SSE) — no CLI
│   │   ├── SKILL.md
│   │   └── scripts/kvidai-client.mjs
│   ├── kvidai-media/              # Media upload/management (presigned URL, CRUD) — no CLI
│   │   ├── SKILL.md
│   │   └── scripts/kvidai-media-client.mjs
│   ├── kvidai-preset/             # Preset CRUD — no CLI
│   │   ├── SKILL.md
│   │   └── scripts/kvidai-preset-client.mjs
│   ├── kvidai-video-use/          # Conversation-driven video editor — no CLI
│   │   ├── SKILL.md
│   │   ├── install.md
│   │   ├── helpers/
│   │   └── skills/manim-video/
│   ├── kvidai/                    # Core kvidai CLI workflow — requires kvidai CLI
│   ├── kvidai-ref/                # Full kvidai CLI reference — requires kvidai CLI
│   ├── model-routing/             # Default endpoint IDs — requires kvidai CLI
│   ├── character-design/          # Character design production — requires kvidai CLI
│   ├── cinematography/            # Cinematic prompt direction — requires kvidai CLI
│   ├── commercial/                # Commercial/product production — requires kvidai CLI
│   ├── storytelling/              # Multi-shot narrative workflows — requires kvidai CLI
│   └── workflow/                  # Multi-step media pipelines — requires kvidai CLI
├── scripts/build-skills-index.ts  # Regenerates skills/index.json (`bun run scripts/build-skills-index.ts`)
├── AGENTS.md                      # This file (AI guide)
├── CLAUDE.md                      # Symlink → AGENTS.md
└── README.md                      # Human index
```

CLI-dependent skills (bottom 8 above) were merged in from the `kvidai-cli` repo so that `kvidai/kvidai-cli` can go private later without breaking `kvidai skills install` — see [kvidai-cli AGENTS.md](https://github.com/kvidai/kvidai-cli) for the CLI-side install flow. Each of their `SKILL.md` states the CLI requirement right under the title.

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter:
   ```yaml
   ---
   name: <skill-name>
   description: One-line description — used for skill discovery
   metadata:
     tags: tag1, tag2
   ---
   ```
2. Add any helper scripts to `skills/<skill-name>/scripts/`
3. Update `README.md` with the new skill entry
4. In kvidai monorepo, add symlink: `ln -s ../../skills/kvidai-skills/skills/<skill-name> .claude/skills/<skill-name>`

## Updating an Existing Skill

Work inside the submodule directory, then commit and push here.
The parent monorepo (`kvidai/`) will pick up the new ref on next `git submodule update --remote`.

```bash
# From kvidai monorepo root
cd skills/kvidai-skills
# ... edit ...
git add . && git commit -m "feat: ..."
git push

# Update submodule ref in parent
cd ../..
git add skills/kvidai-skills
git commit -m "chore: update kvidai-skills submodule"
```

## Skills Reference

No CLI required — call `api.kvid.ai` directly:

| Skill | Trigger | Description |
|-------|---------|-------------|
| `kvidai-video-project` | generate video, create video project, kvidai API, 영상 생성 | Create project + AI agent SSE generate + status poll |
| `kvidai-media` | upload media, presigned URL | Upload media, presigned URL, list/delete assets |
| `kvidai-preset` | preset CRUD | Create, list, update, delete presets |
| `kvidai-video-use` | edit video, transcribe, cut, grade, subtitle, composite, 영상 편집 | Full conversation-driven editor pipeline; hands off final timeline to kvidai web editor |

Requires the kvidai CLI installed locally:

| Skill | Trigger | Description |
|-------|---------|-------------|
| `kvidai` | run a kvid.ai model, use kvidai | Core CLI workflow: discover, run, poll, download |
| `kvidai-ref` | kvidai CLI reference | Full kvidai CLI command reference |
| `model-routing` | pick a model, no endpoint named | Default endpoint IDs for the production skills below |
| `character-design` | character design, character media | Consistent character designs and character media |
| `cinematography` | cinematic direction, shot language | Cinematic image/video prompt direction |
| `commercial` | product/ad/commercial production | Commercial/product/ad production |
| `storytelling` | storyboard, multi-shot narrative | Multi-shot narrative workflows |
| `workflow` | multi-step media pipeline | Multi-step media pipelines |
