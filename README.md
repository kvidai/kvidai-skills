# kvidai-skills

Agent skills for the kvidai video platform — works with Claude Code, Codex, Goose, Copilot, and [50+ agents](https://github.com/vercel-labs/skills).

This is the single skill registry for kvidai. Some skills call `api.kvid.ai` directly via Node.js and need no CLI; others teach the agent how to call the [kvidai CLI](https://github.com/kvidai/kvidai-cli) and require it installed locally. Each skill's `SKILL.md` states which applies — CLI-dependent skills say so right under the title (`> **Requires**: the kvidai CLI installed locally`).

## Skills — no CLI required (call `api.kvid.ai` directly)

| Skill | Description |
|-------|-------------|
| [`kvidai-video-project`](skills/kvidai-video-project/) | Create projects, generate videos via AI agent (SSE), poll status |
| [`kvidai-media`](skills/kvidai-media/) | Upload media, presigned URL, list/delete assets |
| [`kvidai-preset`](skills/kvidai-preset/) | Create, list, update, delete presets |
| [`kvidai-video-use`](skills/kvidai-video-use/) | Conversation-driven video editor: transcribe, cut, grade, subtitle, composite |

## Skills — require the kvidai CLI installed locally

| Skill | Description |
|-------|-------------|
| [`kvidai`](skills/kvidai/) | Core workflow: run a kvid.ai model end-to-end with the CLI |
| [`kvidai-ref`](skills/kvidai-ref/) | Full kvidai CLI command reference |
| [`model-routing`](skills/model-routing/) | Default endpoint IDs for the production skills below |
| [`character-design`](skills/character-design/) | Consistent character designs and character media |
| [`cinematography`](skills/cinematography/) | Cinematic image/video prompt direction |
| [`commercial`](skills/commercial/) | Commercial/product/ad production |
| [`storytelling`](skills/storytelling/) | Multi-shot narrative workflows |
| [`workflow`](skills/workflow/) | Multi-step media pipelines |

Install these with `kvidai init` / `kvidai skills install <name>` (ships with the CLI, see [kvidai CLI README](https://github.com/kvidai/kvidai-cli)) or via `npx skills add` below like any other skill in this repo.

## Installation

### Option 1 — npx skills (recommended)

```bash
npx skills add kvidai/kvidai-skills
```

Installs all skills into the current project for all detected agents automatically.

### Option 2 — Symlink (kvidai monorepo)

```bash
ln -s ../../skills/kvidai-skills/skills/kvidai-video-project .claude/skills/kvidai-video-project
ln -s ../../skills/kvidai-skills/skills/kvidai-media         .claude/skills/kvidai-media
ln -s ../../skills/kvidai-skills/skills/kvidai-preset        .claude/skills/kvidai-preset
ln -s ../../skills/kvidai-skills/skills/kvidai-video-use     .claude/skills/kvidai-video-use
ln -s ../../skills/kvidai-skills/skills/kvidai               .claude/skills/kvidai
ln -s ../../skills/kvidai-skills/skills/kvidai-ref           .claude/skills/kvidai-ref
ln -s ../../skills/kvidai-skills/skills/model-routing        .claude/skills/model-routing
ln -s ../../skills/kvidai-skills/skills/character-design     .claude/skills/character-design
ln -s ../../skills/kvidai-skills/skills/cinematography       .claude/skills/cinematography
ln -s ../../skills/kvidai-skills/skills/commercial           .claude/skills/commercial
ln -s ../../skills/kvidai-skills/skills/storytelling         .claude/skills/storytelling
ln -s ../../skills/kvidai-skills/skills/workflow             .claude/skills/workflow
```

### Option 3 — Git submodule

```bash
git submodule add https://github.com/kvidai/kvidai-skills skills/kvidai-skills
# then add symlinks as in Option 2
```

## Environment Variables

```bash
export KVIDAI_API_KEY="<your-api-key>"
export KVIDAI_BASE_URL="https://api.kvid.ai"  # default if not set
export KVIDAI_USER_EMAIL="user@example.com"   # optional; used by some media upload APIs
```
