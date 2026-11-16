# 영상 분석용 프레임 추출 CLI 및 Skill

> **Last Updated**: 2026-11-16
> **Version**: v1.3.0
> **Status**: done
> **Created In**: C:\workspace\marketing-studio-custom

## Command Clarity Check

**Runnable**: ✅ 사용자 구현 승인. 원본 저장소에서 CLI·Skill 개발 및 로컬 검증 진행.

## Changelog

| Date | Version | Changes | Directory | Author |
|---|---|---|---|---|
| 2026-11-16 | v1.0.0 | 대화에서 합의한 계획 저장 및 Skill/APM 배포 구성 추가 | C:\workspace\marketing-studio-custom | Codex |
| 2026-11-16 | v1.1.0 | 개발 저장소 clone 및 원본 개발 경로 확정 | C:\workspace\marketing-studio-custom | Codex |
| 2026-11-16 | v1.1.0 | 개발 저장소에 계획 인계; 이후 구현은 이 저장소에서 진행 | C:\workspace\kvidai-skills | Codex |
| 2026-11-16 | v1.2.0 | 구현 시작; Python/Pillow 및 FFmpeg 사용, 타임스탬프와 선택 이유 기록 | C:\workspace\kvidai-skills | Codex |
| 2026-11-16 | v1.3.0 | CLI/Skill 구현 완료, Windows/Linux 테스트 및 로컬 APM 설치 검증 | C:\workspace\kvidai-skills | Codex |

## 목표

Windows와 Linux에서 영상 경로와 분석 모드를 지정하면, 에이전트가 순서대로 검토할 수 있는 프레임 이미지와 시간 정보를 생성한다. 다른 kvidai 프로젝트에서도 재사용할 수 있도록 한다.

## 구현 계획

- Python CLI와 FFmpeg·ffprobe를 사용하며, 유니코드와 공백이 있는 경로를 지원한다.
- `motion`: 일정 간격 후보와 화면 변화량을 함께 살펴 움직임과 구성 변화가 드러나는 프레임을 선별한다.
- `scene`: 장면 전환 전후와 각 장면의 대표 프레임을 추출한다.
- `dense`: 지정한 시간 간격으로 프레임을 추출하고 장면 전환 프레임을 추가한다.
- 입력 영상, 출력 폴더, 모드, 추출 간격과 최대 프레임 수를 CLI에서 지정한다. 기본 모드는 `motion`이며 첫 프레임과 마지막 유효 프레임을 포함한다.
- 타임스탬프가 포함된 개별 이미지, 시간순 목록, 페이지별 연락처 시트를 생성한다. 목록에는 프레임의 시간과 선택 이유를 기록한다.
- 기존 결과가 있으면 덮어쓰기 전에 중단한다. 입력 오류, FFmpeg 부재, 디코딩 실패의 원인을 표시한다.
- Windows PowerShell과 Linux 셸 실행 예시 및 Python·FFmpeg 의존성 확인을 제공한다.

## 배포 구성 — Skill 및 APM

이번 기능은 실행 스크립트를 포함한 Skill로 만들고, APM으로 배포하는 구성이 적합하다.

| 형태 | 역할 | 이번 기능에서 |
|---|---|---|
| CLI | 실제 프레임 분석·추출 실행 | 핵심 기능 |
| Skill | 에이전트에 사용 조건·명령·결과 읽는 방법 안내 | CLI와 함께 제공 |
| MCP | 연결된 앱이 도구 호출로 실행 | 앱에서 직접 호출해야 할 때 추가 |
| Plugin | 여러 Skill과 MCP 등을 묶어 배포 | 기능이 많아지면 고려 |

Skill에 실행 스크립트를 포함하여 사용자의 직접 CLI 실행과 에이전트의 호출이 동일한 실행 코어를 사용하게 한다. MCP와 Plugin 구현은 현재 범위에 포함하지 않는다.

### 확정된 개발 저장소

- 저장소: https://github.com/kvidai/kvidai-skills
- clone 경로: `C:\workspace\kvidai-skills` (기준 commit `a08d2f4`).
- 원본 개발 경로: `C:\workspace\kvidai-skills\skills\video-frame-analysis\`.
- 실행 코어: `scripts/extract_frames.py`, 진입 지침: `SKILL.md`, 사용 예시: `references/usage.md`.
- 해당 저장소의 `AGENTS.md`에 따라 Skill 추가 시 README 등록과 skill index 생성 방식을 확인한다.
- 현재 marketing-studio의 APM 설치 경로는 배포 결과이며 원본 개발에 사용하지 않는다.
- 개발 저장소의 이 계획이 정본이며, 완료 후 `20261116_done_video-frame-analysis.md`로 이름을 변경한다. marketing-studio 쪽 계획은 인계 시점의 기록이다.

## Implementation & Test Status

| File | Feature | Impl | Unit Test | Integration Test |
|---|---|---|---|---|
| 계획 문서 | CLI 및 Skill/APM 구성 | ✅ | ⏭️ | ⏭️ |
| `skills/video-frame-analysis/` | 프레임 추출 CLI 및 Skill | ✅ | ✅ | ✅ |
| `scripts/build-skills-index.ts` | Windows/Linux 동일한 `/` 파일 경로 생성 | ✅ | ⏭️ | ✅ |

## Test Execution Results

- Windows: 7 unittest cases passed, including all three modes on generated black/white scenes, real pixel/source-frame alignment, Unicode paths, single frame, caps, invalid input and dependency checks.
- Reference video: motion 74 PNG / 4 contact sheets; scene 4 PNG / 1 sheet; dense 39 PNG / 2 sheets. Stored under the campaign `out/frame-analysis-{mode}` directories. Motion page 1 and dense page 2 visually reviewed; JUST typography, moving silhouettes, HERE and end cards are visible. This is sampled visual review, not full playback/audio QA.
- Skill quick validation passed. Existing skill index was already stale before implementation; regenerated using the repository generator via Node 22 type stripping (Bun absent).
- Linux Ubuntu is present with Python 3.8.10/Pillow 9.0.1, but FFmpeg/ffprobe absent. Preparing an isolated temporary FFmpeg runtime without modifying system packages.

### Final verification

- Windows: 8 tests passed (Python 3.10.1, Pillow 12.1.0, FFmpeg 8.0.1), 5.27 seconds. Tests in `tests/video-frame-analysis/test_extract_frames.py` cover cut neighbors, scene representatives, motion neighborhoods, timestamp/cap selection, all three CLI modes, single frames, bad inputs, dependency failures, output preservation, pixel-to-source-frame alignment, and a genuinely variable-rate encoded video.
- Linux: the same 8 tests passed natively under WSL Ubuntu (Python 3.8.10, Pillow 9.0.1, FFmpeg 7.0.2), 2.21 seconds. Supported documented minimum remains Python 3.10; Linux testing used the available older interpreter. Temporary native static FFmpeg downloaded from `https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz` into `/tmp/kvidai-frame-analysis-tools`; no system package changes.
- APM: local-path dependency installed in an isolated temporary project targeting `claude,codex`, then reinstallation succeeded. Installed script dependency check passed; both target copies match source SHA-256 `705bdfe6b3ade1e9dcc3d084204dd56e124e2bb3516b9309b3054a26128b3dea`.
- Skill validator passed. Index generator and `--check` passed with Node 22 `--experimental-strip-types`; `git diff --check` clean. Index regenerated for 13 skills. Existing kvidai-media index entries had stale hashes before this task and were refreshed by the generator; no media source files changed.
- Exported PNGs retain original resolution; frames.json/CSV/index.md and timestamped sheets agree in automated fixture checks. Source input bytes remain unchanged.
- This is a local implementation and local APM distribution test. No commit, push, public release, remote installation of the unpublished skill, or live consumer configuration change was performed.

## 검증 계획

- `campaigns/20261116_marleehightower하프톤JUST그래픽포스터모션/references/`의 영상으로 세 모드를 실행한다. 확인된 영상 정보: 약 9.22초, 1440×1080, 221프레임.
- 시간순 정렬, 첫·끝 프레임 포함, 목록과 연락처 시트의 일치를 확인한다.
- 한글·공백 경로, 짧은 영상, 장면 전환 없는 영상, 잘못된 입력, 출력 폴더 충돌을 검증한다.
- 이미지를 검토해 타이포그래피 변화와 동작의 주요 단계가 분석에 충분히 포착되는지 평가한다.
- Windows에서 실행하고, Linux 실제 실행 환경이 확보되면 동일 시나리오를 검증한다. 실행하지 못한 환경은 미검증으로 기록한다.

## 가정과 한계

- 의미 있는 프레임은 장면 변화와 픽셀 변화량을 이용한 후보 선별이다. 동작의 의미적 시작·절정·끝을 항상 정확하게 판별한다고 보장하지 않는다.
- 연락처 시트를 통해 누락된 동작을 확인할 수 있게 한다.
- 원본 영상은 수정하지 않으며 외부 AI 서비스나 유료 호출 없이 로컬에서 실행한다.
- Skill 설치 자체가 Python·FFmpeg 설치를 보장하지 않으므로 의존성을 확인한다.

## Remaining Tasks

- [x] 기존 대화 계획 저장 및 Skill/APM 구성 추가.
- [x] 배포 저장소와 원본 개발 경로 확정.
- [x] 프레임 추출 CLI와 Skill 구현.
- [x] 레퍼런스 영상 및 예외 시나리오 검증.
- [x] Windows·Linux 실행 결과와 APM 설치 검증 기록.

## Research Log

### Search Keywords

- `scene.?detect|scdet|scene.?change|key.?frame|프레임 추출|장면 전환`

### Reference URLs

- https://github.com/microsoft/apm/blob/main/docs/src/content/docs/getting-started/first-package.md
- https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

### Key Findings

- 제공된 레퍼런스 영상은 ffprobe로 길이와 해상도 및 프레임 수를 확인했다.
- 현재 프로젝트는 APM을 통해 Claude와 Codex 대상으로 스킬을 설치한다.
- CLI는 처리 기능, Skill은 에이전트 사용 지침, APM은 배포 역할을 맡긴다.

## Decision Log

CLI와 Skill을 함께 제공하고 APM으로 배포한다. MCP와 Plugin은 현재의 로컬 CLI 재사용 요구에 필수적이지 않아 후속 확장으로 남긴다.

구현 결정: Python 표준 라이브러리와 Pillow, FFmpeg를 사용한다. 모든 소스 프레임의 표시 타임스탬프를 ffprobe로 읽고, 96×54 grayscale 변화량을 계산한 다음 선택된 원본 해상도 PNG를 추출한다. 광학 흐름이나 외부 AI 분석은 포함하지 않는다. 출력은 기존 폴더를 거부하고 임시 형제 폴더에서 준비해 완성 후 이동한다. Windows 명령 길이 제한을 피하도록 FFmpeg 선택식을 파일로 전달한다. 생성기 경로 구분자를 정규화해 두 플랫폼의 배포 인덱스 형식을 통일한다.

## Decision Conversation Summary

- 이번 영상 전용 추출 대신 재사용 CLI를 선택했다.
- 모션·장면 전환·촘촘한 전체 분석을 모두 사용자 선택 모드로 제공하기로 했다.
- 다른 kvidai 프로젝트 재사용 요구에 따라 실행 스크립트를 포함한 Skill과 APM 배포 구성을 추가했다.
