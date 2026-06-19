# kvidai-skills

Agent skills for the kvidai video platform — works with Claude Code, Codex, Goose, Copilot, and [50+ agents](https://github.com/vercel-labs/skills).

## Skills

| Skill | Description |
|-------|-------------|
| [`kvidai-video-project`](skills/kvidai-video-project/) | Create projects, generate videos via AI agent (SSE), poll status |
| [`kvidai-media`](skills/kvidai-media/) | Upload media, presigned URL, list/delete assets |
| [`kvidai-preset`](skills/kvidai-preset/) | Create, list, update, delete presets |
| [`kvidai-video-use`](skills/kvidai-video-use/) | Conversation-driven video editor: transcribe, cut, grade, subtitle, composite |

## When to use this vs the kvidai CLI

| Situation | Use |
|---|---|
| Manage video projects, presets, media — or edit video by conversation — **any agent, no CLI needed** | **kvidai-skills** (this repo) |
| Generate images/video/audio with a kvid.ai model, **kvidai CLI installed locally** | [kvidai CLI](https://github.com/kvidai/kvidai-cli) bundled skills (`kvidai init`) |

These skills call `api.kvid.ai` directly via Node.js — the kvidai CLI binary is **not required**.
The kvidai CLI bundled skills teach agents how to call CLI commands and require the binary to be present on the same machine.

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
