---
name: kvidai-ai
description: kvid.ai APIM 생성 엔드포인트 래퍼 (기존 kvidai CLI 미포함분). voice(TTS)·stt·talk-v2v·ai-edit. api-key 헤더 + credit 식별(email). Triggers on TTS, 나레이션, 음성 생성, speech-to-text, 자막 추출, 립싱크, talk, 영상 편집 AI.
metadata:
  tags: kvidai, tts, voice, stt, talk-v2v, ai-edit, apim
---

kvid.ai APIM 의 생성 엔드포인트 중 **`kvidai` CLI 가 제공하지 않는 것**을 감싼다. (image / video t2v 는 `kvidai` CLI 사용.)
클라이언트: `.claude/skills/kvidai-ai/scripts/kvidai-ai-client.mjs` (plain `node`).

## 환경변수
```bash
KVIDAI_API_KEY="<APIM key>"           # api-key 헤더
KVIDAI_BASE_URL="https://api.kvid.ai" # 기본값. Local(api.hometip.net/...clone) 미사용
KVIDAI_USER_EMAIL="<계정 이메일>"      # 생성 크레딧 pool 식별 (또는 KVIDAI_PRODUCT_CODE/ID)
```

## voice (TTS) — ✅ 구현·검증됨
```bash
SKILL=.claude/skills/kvidai-ai/scripts/kvidai-ai-client.mjs
node $SKILL voice --text "나레이션 문장" \
  --voice-id m3gJBS8OofDJfycyA2Ip --lang ko --speed 1.1 \
  --out campaigns/<slug>/assets/voice1.mp3
# → stdout JSON: { result_url, duration_seconds, alignment, out }
node $SKILL voices   # (참고: 현재 404 — 미배포. voice_id 는 프리셋 config.voice.voiceId 에서 획득)
node $SKILL models
```
- 비동기: submit → `/ai/generation/voice/status` 폴링 → `/ai/generation/voice/result`.
- **`duration_seconds`** 로 씬 길이를 맞추고, **`alignment`**(문자단위 타이밍)로 자막 싱크 가능.
- 한국어 voice_id 예: `m3gJBS8OofDJfycyA2Ip` (multilingual_v2). `kvidai-preset get <id>` 의 `config.voice` 에서 획득.

## 나레이션 → 조립 연동 (voice-driven timing)
1. 씬별 나레이션 문장 작성 → 순차로 `voice --out assets/voiceN.mp3` (429 회피).
2. 각 `duration_seconds` + 여유(~0.5s) 를 씬 `durationSec` 로.
3. video.json 씬에 `"voice": { "file": "assets/voiceN.mp3" }` 추가 → video-template 조립.

## stt (speech-to-text) — ✅ 구현·검증됨
```bash
node $SKILL stt --url <cdnUrl> --lang ko        # CDN URL (JSON)
node $SKILL stt --file audio.mp3 --lang ko      # 파일 업로드 (multipart)
# → 원본 Scribe JSON: { text, words:[{text,start,end,speaker_id}], language_code }
```
동기(단일 POST). `/ai/speech-to-text`. api.kvid.ai 는 api-key 로 owner 주입 → email 불필요.

## edit (ai-edit) — ✅ 구현 (SSE)
```bash
node $SKILL edit summary --url <mediaUrl> --instruction "핵심만 요약" [--mode overview|trailer]
node $SKILL edit silence-cut --url <mediaUrl> [--out out.mp4]   # 무음 제거 → MP4
node $SKILL edit shorts --url <mediaUrl>                        # 숏폼 하이라이트 후보
# → done.data (summary: segments+captions / silence-cut: outputUrl / shorts: 후보)
```
`/ai-edit/{summary,silence-cut,shorts}`. SSE 스트림, api-key 만.

## 제외
- **talk-v2v (립싱크)**: 서비스 미제공 상태 → 미구현.
- **image / video t2v**: `kvidai` CLI 가 이미 제공 (`kvidai image`, `kvidai video t2v`).
