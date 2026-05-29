"""Transcribe a video.

Backend priority:
  1. KVIDAI_API_KEY set  →  kvidai STT (ElevenLabs Scribe-compatible endpoint)
  2. fallback            →  faster-whisper locally (pip install faster-whisper)

Extracts mono 16kHz audio via ffmpeg, sends to the selected backend,
writes the full response to <edit_dir>/transcripts/<video_stem>.json.

Cached: if the output file already exists the upload/inference is skipped.

Usage:
    python helpers/transcribe.py <video_path>
    python helpers/transcribe.py <video_path> --edit-dir /custom/edit
    python helpers/transcribe.py <video_path> --language en
    python helpers/transcribe.py <video_path> --num-speakers 2
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests


def _load_env_key(key_name: str) -> str:
    for candidate in [Path(__file__).resolve().parent.parent / ".env", Path(".env")]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key_name:
                    return v.strip().strip('"').strip("'")
    return os.environ.get(key_name, "")


def _kvidai_key() -> str:
    return _load_env_key("KVIDAI_API_KEY")


def _kvidai_base_url() -> str:
    return _load_env_key("KVIDAI_BASE_URL") or os.environ.get("KVIDAI_BASE_URL", "https://api.kvid.ai")


def extract_audio(video_path: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _call_kvidai_stt(
    audio_path: Path,
    api_key: str,
    language: str | None,
    num_speakers: int | None,
) -> dict:
    """kvidai STT endpoint — ElevenLabs Scribe-compatible request/response."""
    url = f"{_kvidai_base_url()}/v1/speech-to-text"
    data: dict[str, str] = {
        "model_id": "scribe_v2",
        "diarize": "true",
        "tag_audio_events": "true",
        "timestamps_granularity": "word",
    }
    if language:
        data["language_code"] = language
    if num_speakers:
        data["num_speakers"] = str(num_speakers)

    with open(audio_path, "rb") as f:
        resp = requests.post(
            url,
            headers={"api-key": api_key},
            files={"file": (audio_path.name, f, "audio/wav")},
            data=data,
            timeout=1800,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"kvidai STT {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def _call_local_whisper(
    audio_path: Path,
    language: str | None,
) -> dict:
    """Local transcription via faster-whisper. Returns ElevenLabs-compatible dict."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit(
            "KVIDAI_API_KEY not set and faster-whisper not installed.\n"
            "  Install: pip install faster-whisper\n"
            "  Or set KVIDAI_API_KEY to use kvidai STT."
        )

    model = WhisperModel("large-v2", device="auto", compute_type="auto")
    kwargs: dict = {"word_timestamps": True}
    if language:
        kwargs["language"] = language

    segments, info = model.transcribe(str(audio_path), **kwargs)

    words = []
    text_parts: list[str] = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                words.append({
                    "text": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "type": "word",
                    "speaker_id": "speaker_0",
                })
                text_parts.append(w.word.strip())
        else:
            text_parts.append(seg.text.strip())

    return {
        "language_code": info.language,
        "text": " ".join(text_parts),
        "words": words,
        "_source": "faster-whisper",
    }


def transcribe_one(
    video: Path,
    edit_dir: Path,
    language: str | None = None,
    num_speakers: int | None = None,
    verbose: bool = True,
    # legacy param — ignored, backend resolved from env
    api_key: str | None = None,
) -> Path:
    """Transcribe a single video. Returns path to transcript JSON.

    Backend: kvidai STT if KVIDAI_API_KEY is set, else faster-whisper locally.
    Cached: returns existing path immediately if transcript already exists.
    """
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    key = _kvidai_key()
    backend = "kvidai-stt" if key else "faster-whisper"

    if verbose:
        print(f"  [{backend}] extracting audio from {video.name}", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio)
        size_mb = audio.stat().st_size / (1024 * 1024)
        if verbose:
            print(f"  [{backend}] processing {video.stem}.wav ({size_mb:.1f} MB)", flush=True)
        if key:
            payload = _call_kvidai_stt(audio, key, language, num_speakers)
        else:
            payload = _call_local_whisper(audio, language)

    out_path.write_text(json.dumps(payload, indent=2))
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        if isinstance(payload, dict) and "words" in payload:
            print(f"    words: {len(payload['words'])}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Transcribe a video (kvidai STT if KVIDAI_API_KEY set, else faster-whisper)"
    )
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument("--edit-dir", type=Path, default=None,
                    help="Edit output directory (default: <video_parent>/edit)")
    ap.add_argument("--language", type=str, default=None,
                    help="Optional ISO language code (e.g. 'en'). Omit to auto-detect.")
    ap.add_argument("--num-speakers", type=int, default=None,
                    help="Optional speaker count. Improves diarization accuracy.")
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()
    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        language=args.language,
        num_speakers=args.num_speakers,
    )


if __name__ == "__main__":
    main()
