"""
E2E test — transcribe 기능 (STT + agent subtitle flow)

테스트 환경:
  Strapi   : development.env (ELEVENLABS_API_KEY 있음, 로컬 DB)
  loclx    : localstrapi.loclx.io → localhost:1337
             leescwebdev.loclx.io → localhost:3000

실행:
  cd /home/ubuntu/code_workspace/kvidai
  python skills/kvidai-skills/skills/kvidai-video-use/tests/e2e_transcribe.py

환경변수 (기본값 내장 — development.env 기반):
  STRAPI_BASE_URL  : https://localstrapi.loclx.io
  AGENT_BASE_URL   : https://leescwebdev.loclx.io
  TEST_USER_EMAIL  : user1@test.kvidai.local
  TEST_APIM_KEY    : ad5f47dfc94241a6993459ce6afb53d1
  VIDEO_PATH       : (아래 DEFAULT_VIDEO 사용)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

# ── 설정 ──────────────────────────────────────────────────────────────────────

STRAPI_BASE_URL = os.environ.get("STRAPI_BASE_URL", "https://localstrapi.loclx.io")
AGENT_BASE_URL  = os.environ.get("AGENT_BASE_URL",  "https://leescwebdev.loclx.io")
TEST_USER_EMAIL = os.environ.get("TEST_USER_EMAIL",  "user1@test.kvidai.local")
TEST_APIM_KEY   = os.environ.get("TEST_APIM_KEY",    "ad5f47dfc94241a6993459ce6afb53d1")

DEFAULT_VIDEO = Path(
    "/home/ubuntu/code_workspace/kvidai-marketing-studio"
    "/campaigns/20260529_video_mabulshow"
    "/매불쇼youtube20260528_seg_01_main.mp4"
)
VIDEO_PATH = Path(os.environ.get("VIDEO_PATH", str(DEFAULT_VIDEO)))

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = PASS if ok else FAIL
    print(f"  [{status}] {name}" + (f"\n         {detail}" if detail and not ok else ""))


def extract_audio(video: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── Test 1: Strapi health ─────────────────────────────────────────────────────

def test_strapi_health() -> None:
    print("\n[1] Strapi health check")
    try:
        r = requests.get(f"{STRAPI_BASE_URL}/_health", timeout=10)
        check("Strapi 응답", r.status_code in (200, 204), f"status={r.status_code}")
    except Exception as e:
        check("Strapi 응답", False, str(e))


# ── Test 2: 직접 STT 호출 (APIM 우회) ────────────────────────────────────────

def test_stt_direct() -> None:
    print("\n[2] Strapi /api/speech-to-text 직접 호출 (loclx 경유)")
    if not VIDEO_PATH.exists():
        check("비디오 파일 존재", False, f"not found: {VIDEO_PATH}")
        return
    check("비디오 파일 존재", True)

    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{VIDEO_PATH.stem}.wav"
        try:
            extract_audio(VIDEO_PATH, audio)
            size_mb = audio.stat().st_size / 1024 / 1024
            check("ffmpeg 오디오 추출", True, f"{size_mb:.1f} MB")
        except Exception as e:
            check("ffmpeg 오디오 추출", False, str(e))
            return

        t0 = time.time()
        try:
            with open(audio, "rb") as f:
                resp = requests.post(
                    f"{STRAPI_BASE_URL}/api/speech-to-text",
                    files={"file": (audio.name, f, "audio/wav")},
                    data={
                        "email": TEST_USER_EMAIL,
                        "model_id": "scribe_v1",
                        "timestamps_granularity": "word",
                    },
                    timeout=300,
                )
            elapsed = time.time() - t0
            check("STT 응답 200", resp.status_code == 200,
                  f"status={resp.status_code} body={resp.text[:200]}")
            if resp.status_code != 200:
                return

            data = resp.json()
            has_words = isinstance(data.get("words"), list) and len(data["words"]) > 0
            check("words 배열 존재", has_words,
                  f"words count={len(data.get('words', []))}")
            check("language_code 존재", bool(data.get("language_code")),
                  f"language_code={data.get('language_code')}")
            print(f"         elapsed={elapsed:.1f}s  words={len(data.get('words', []))}"
                  f"  lang={data.get('language_code')}")

            # transcript 저장
            out_dir = VIDEO_PATH.parent / "edit" / "transcripts"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{VIDEO_PATH.stem}.json"
            out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"         saved: {out_file}")

        except Exception as e:
            check("STT 호출", False, str(e))


# ── Test 3: media-management 업로드 ──────────────────────────────────────────

def test_media_upload() -> tuple[str | None, int | None]:
    """비디오를 media-management에 업로드하고 (cdnUrl, fileId) 반환."""
    print("\n[3] media-management 파일 업로드")
    if not VIDEO_PATH.exists():
        check("비디오 업로드", False, f"not found: {VIDEO_PATH}")
        return None, None

    try:
        with open(VIDEO_PATH, "rb") as f:
            resp = requests.post(
                f"{STRAPI_BASE_URL}/api/media-management/upload",
                files={"files": (VIDEO_PATH.name, f, "video/mp4")},
                data={"email": TEST_USER_EMAIL},
                timeout=120,
            )
        check("업로드 응답 200", resp.status_code == 200,
              f"status={resp.status_code} body={resp.text[:200]}")
        if resp.status_code != 200:
            return None, None

        data = resp.json()
        files = data.get("data", [])
        check("업로드 파일 반환", len(files) > 0, f"count={len(files)}")
        if not files:
            return None, None

        cdn_url = files[0].get("url")
        file_id = files[0].get("id")
        check("CDN URL 반환", bool(cdn_url), f"url={cdn_url}")
        print(f"         fileId={file_id}  url={cdn_url}")
        return cdn_url, file_id

    except Exception as e:
        check("비디오 업로드", False, str(e))
        return None, None


# ── Test 4: Agent — generate_transcript + add_subtitles ───────────────────────

def test_agent_transcribe(cdn_url: str | None) -> None:
    print("\n[4] Agent e2e — generate_transcript + add_subtitles_from_transcript")

    # 프로젝트 생성
    try:
        r = requests.post(
            f"{STRAPI_BASE_URL}/api/video-project",
            json={"name": "E2E Transcribe Test", "email": TEST_USER_EMAIL},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        check("프로젝트 생성", r.status_code in (200, 201),
              f"status={r.status_code} body={r.text[:200]}")
        if r.status_code not in (200, 201):
            return

        project = r.json()
        project_id = (project.get("data", {}) or project).get("id")
        check("projectId 반환", bool(project_id), f"projectId={project_id}")
        if not project_id:
            return
        print(f"         projectId={project_id}")

    except Exception as e:
        check("프로젝트 생성", False, str(e))
        return

    # 프로젝트 composition 조회 (agent에 전달 필요)
    composition = None
    try:
        pr = requests.get(
            f"{STRAPI_BASE_URL}/api/video-project/{project_id}",
            params={"email": TEST_USER_EMAIL},
            timeout=10,
        )
        if pr.ok:
            composition = (pr.json().get("data") or pr.json()).get("composition")
    except Exception:
        pass

    # Agent 호출
    message = "이 영상에 한국어 자막을 추가해줘"
    body: dict = {
        "projectId": project_id,
        "email": TEST_USER_EMAIL,
        "apiKey": TEST_APIM_KEY,
        "message": message,
        "chatHistory": [],
        "composition": composition or {"fps": 30, "items": {}, "assets": {}, "tracks": [], "durationInFrames": 300, "compositionWidth": 1080, "compositionHeight": 1920},
    }
    if cdn_url:
        body["attachedFiles"] = [{
            "name": VIDEO_PATH.name,
            "type": "video",
            "mimeType": "video/mp4",
            "size": VIDEO_PATH.stat().st_size if VIDEO_PATH.exists() else 0,
            "cdnUrl": cdn_url,
        }]

    try:
        print(f"         POST {AGENT_BASE_URL}/api/agent  message='{message}'")
        t0 = time.time()
        resp = requests.post(
            f"{AGENT_BASE_URL}/api/agent",
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=300,
            stream=True,
        )
        check("Agent 응답 200", resp.status_code == 200,
              f"status={resp.status_code}")
        if resp.status_code != 200:
            print(f"         body={resp.text[:300]}")
            return

        # SSE 스트림 파싱 (tool_start 이벤트만 — top-level 툴 호출 추적)
        tools_started: list[str] = []
        cur_event = ""
        for line in resp.iter_lines(decode_unicode=True):
            if line is None or line == "":
                continue
            if line.startswith("event: "):
                cur_event = line[7:].strip()
            elif line.startswith("data: ") and cur_event == "tool_start":
                try:
                    d = json.loads(line[6:])
                    if d.get("toolName"):
                        tools_started.append(d["toolName"])
                        print(f"         ▸ tool_start: {d['toolName']}")
                except Exception:
                    pass

        elapsed = time.time() - t0
        print(f"         elapsed={elapsed:.1f}s  tool_start={tools_started}")

        # generate_transcript 는 top-level 툴 → SSE 에 나타남
        check("generate_transcript 호출됨",
              "generate_transcript" in tools_started,
              f"tool_start={tools_started}")

        # add_subtitles_from_transcript 는 generate_transcript 내부 delegation(executeTool 재귀)
        # → 별도 SSE tool_start 미발생. 따라서 SSE 가 아닌 실제 composition 결과로 검증한다.
        comp = None
        for _ in range(5):
            time.sleep(2)  # autoSave 반영 대기
            pr = requests.get(
                f"{STRAPI_BASE_URL}/api/video-project/{project_id}",
                params={"email": TEST_USER_EMAIL},
                timeout=10,
            )
            if pr.ok:
                comp = (pr.json().get("data") or pr.json()).get("composition", {})
                assets = comp.get("assets", {})
                if any(a.get("type") == "caption" for a in assets.values()):
                    break

        assets = (comp or {}).get("assets", {})
        items = (comp or {}).get("items", {})
        cap_assets = [a for a in assets.values() if a.get("type") == "caption"]
        cap_items = [i for i in items.values() if i.get("type") in ("captions", "caption", "subtitle", "text")]

        check("CaptionAsset 생성됨 (STT transcript 저장)",
              len(cap_assets) > 0,
              f"caption assets={len(cap_assets)}")
        if cap_assets:
            c = cap_assets[0]
            check("CaptionAsset captions 비어있지 않음",
                  len(c.get("captions", [])) > 0,
                  f"captions={len(c.get('captions', []))}")
            check("idempotency remoteFileKey 설정됨",
                  str(c.get("remoteFileKey", "")).startswith("transcript:"),
                  f"remoteFileKey={c.get('remoteFileKey')}")
        check("자막 아이템(captions) composition 에 추가됨",
              len(cap_items) > 0,
              f"caption/subtitle items={len(cap_items)}")

    except Exception as e:
        check("Agent 호출", False, str(e))


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("E2E: kvidai-video-use transcribe 기능 테스트")
    print(f"  Strapi : {STRAPI_BASE_URL}")
    print(f"  Agent  : {AGENT_BASE_URL}")
    print(f"  Email  : {TEST_USER_EMAIL}")
    print(f"  Video  : {VIDEO_PATH.name}")
    print("=" * 60)

    test_strapi_health()
    test_stt_direct()
    cdn_url, _ = test_media_upload()
    test_agent_transcribe(cdn_url)

    # 결과 요약
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed
    print(f"결과: {passed}/{total} passed" + (f"  ({failed} failed)" if failed else ""))
    if failed:
        print("\n실패 목록:")
        for name, ok, detail in results:
            if not ok:
                print(f"  ❌ {name}" + (f": {detail}" if detail else ""))
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
