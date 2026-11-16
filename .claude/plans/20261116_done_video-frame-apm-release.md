# Publish video-frame-analysis and verify the consumer

> **Last Updated**: 2026-11-16
> **Version**: v1.1.0
> **Status**: done
> **Created In**: C:\workspace\kvidai-skills

## Command Clarity Check

**Runnable**: ✅ User authorized push of kvidai-skills and APM installation/testing in marketing-studio-custom. Commit only the reviewed feature files in kvidai-skills. Preserve unrelated consumer changes; do not publish the consumer repository.

## Changelog

| Date | Version | Changes | Directory | Author |
|---|---|---|---|---|
| 2026-11-16 | v1.0.0 | Start publication and consumer integration | C:\workspace\kvidai-skills | Codex |
| 2026-11-16 | v1.1.0 | Publication, remote APM update, consumer smoke tests and frozen replay passed | C:\workspace\kvidai-skills | Codex |

## Implementation & Test Status

| Component | Impl | Unit Test | Integration Test |
|---|---|---|---|
| Published skill | ✅ | ✅ | ✅ |
| Consumer APM installation | ✅ | ⏭️ | ✅ |

## Test Execution Results

- Published feature commit `c81a609ec42f566fc47d2271486bd08227f7916e` to origin/main and verified remote revision with git ls-remote.
- Consumer: `apm update kvidai/kvidai-skills --yes` successfully fetched that commit and deployed 13 skills to claude/codex using the existing apm.yml remote dependency and targets. No local source override or force flag used.
- Both installed CLI dependency checks passed. Source and both installed scripts have identical SHA-256 `705bdfe6b3ade1e9dcc3d084204dd56e124e2bb3516b9309b3054a26128b3dea`.
- Ran installed Codex path in motion/dense modes and installed Claude path in scene mode against the campaign reference. Results are in campaign `out/frame-analysis-apm-{motion,scene,dense}`. Motion: 74 PNG/4 sheets; scene: 4 PNG/1 sheet; dense: 39 PNG/2 sheets.
- Verified JSON/CSV/image counts, file references, first/last source frames (0/220), contact sheets and original source hash for all three outputs. Visually inspected installed motion contact sheet 4, including HERE, date/end card and final frame. No playback/audio QA claim.
- `apm install --frozen` succeeded for both targets using the remote lock revision, confirming repeated installation.
- APM policy-discovery warning for the inaccessible/missing optional kvidai/.github-private repository and the unpinned-main notice remain nonfatal. Existing unrelated consumer changes are preserved, and consumer repository was not committed or pushed.

## Remaining Tasks

- [x] Review changed files, verify checks and publish feature commit `c81a609ec42f566fc47d2271486bd08227f7916e` to origin/main; confirmed with ls-remote.
- [x] Refresh consumer APM installation from the remote and verify both targets.
- [x] Run installed CLI on the reference video, validate artifacts and repeated install.
- [x] Record results and complete plan.

## Research Log

Existing consumer apm.yml declares kvidai/kvidai-skills and claude,codex targets. Its working tree contains earlier APM changes; preserve these and do not stage or commit the consumer.

Feature commit includes only reviewed source/docs/tests/index and its completed implementation plan. Eight Windows tests, index check and git diff checks passed before publication.

## Decision Log

Use the existing remote dependency, not a local path, to validate actual distribution. Refresh its resolved revision when needed; avoid force and manual lockfile edits.

## Decision Conversation Summary

User requested publication and a real consumer installation test after local development tests passed.
