"""Transcribe a video locally — faster-whisper or whisperx backend.

Outputs Scribe-compatible JSON: {"words": [...]} — works with pack_transcripts.py.

Backends
--------
faster-whisper (default)
    Lightweight, works on CPU/CUDA. Word timestamps ±50–100ms (Whisper internal).
    pip install faster-whisper

whisperx
    Built on faster-whisper + forced alignment (wav2vec2/MMS) → ±10ms timestamps.
    Optional speaker diarization (pyannote.audio, needs HuggingFace token).
    pip install whisperx
    # diarization also needs: pip install pyannote.audio

Requirements (both backends)
    ffmpeg on PATH — https://ffmpeg.org/download.html

NPU note
    faster-whisper/whisperx do not support NPU directly.
    Intel OpenVINO NPU → openvino-whisper (separate package).
    Apple Neural Engine → mlx-whisper on macOS (separate package).

Usage
-----
    # faster-whisper, auto device
    python helpers/transcribe_local.py video.mp4 --language ko

    # whisperx, better timestamps
    python helpers/transcribe_local.py video.mp4 --backend whisperx --language ko

    # whisperx + speaker diarization
    python helpers/transcribe_local.py video.mp4 --backend whisperx --diarize --hf-token hf_xxx

    # force CUDA, large model
    python helpers/transcribe_local.py video.mp4 --device cuda --model large-v3
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


# ── Device auto-detection ─────────────────────────────────────────────────────

def detect_device() -> tuple[str, str]:
    """Return (device, compute_type) — cuda+float16 if available, else cpu+int8."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass
    return "cpu", "int8"


# ── Audio extraction ──────────────────────────────────────────────────────────

def extract_audio(video: Path, dest: Path) -> None:
    """Extract mono 16 kHz WAV via ffmpeg (cross-platform)."""
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video),
         "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dest)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{result.stderr.decode(errors='replace')}")


# ── Shared output helpers ─────────────────────────────────────────────────────

def _build_word_list(raw_words: list[dict]) -> list[dict]:
    """Convert a flat list of {text, start, end, speaker_id?} dicts to Scribe format.

    Inserts spacing entries for gaps ≥ 0.1 s (used by pack_transcripts.py).
    """
    words: list[dict] = []
    prev_end = 0.0
    for w in raw_words:
        start, end = w["start"], w["end"]
        if start - prev_end >= 0.1 and prev_end > 0:
            words.append({"type": "spacing", "start": prev_end, "end": start, "text": ""})
        words.append({
            "type": "word",
            "text": w["text"].strip(),
            "start": start,
            "end": end,
            "speaker_id": w.get("speaker_id"),
        })
        prev_end = end
    return words


def _save(out_path: Path, words: list[dict], meta: dict, verbose: bool) -> Path:
    payload = {"words": words, **meta}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if verbose:
        kb = out_path.stat().st_size / 1024
        n = sum(1 for w in words if w["type"] == "word")
        print(f"saved: {out_path} ({kb:.1f} KB, {n} words)")
    return out_path


# ── faster-whisper backend ────────────────────────────────────────────────────

def transcribe_fw(
    audio: Path, language: str | None, model_size: str, device: str, compute_type: str,
    verbose: bool,
) -> list[dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper not installed. Run: pip install faster-whisper")

    if verbose:
        print(f"[faster-whisper] device={device} compute={compute_type} model={model_size}", flush=True)

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        str(audio), language=language, word_timestamps=True, vad_filter=True,
    )
    if verbose:
        print(f"language: {info.language} ({info.language_probability:.1%})", flush=True)

    raw: list[dict] = []
    for seg in segments:
        for w in (seg.words or []):
            raw.append({"text": w.word, "start": w.start, "end": w.end})
    return raw


# ── whisperx backend ──────────────────────────────────────────────────────────

def transcribe_wx(
    audio: Path, language: str | None, model_size: str, device: str, compute_type: str,
    diarize: bool, hf_token: str | None, verbose: bool,
) -> list[dict]:
    try:
        import whisperx
    except ImportError:
        sys.exit("whisperx not installed. Run: pip install whisperx")

    if verbose:
        print(f"[whisperx] device={device} compute={compute_type} model={model_size}", flush=True)

    # 1. Transcribe (faster-whisper under the hood)
    model = whisperx.load_model(model_size, device, compute_type=compute_type, language=language)
    result = model.transcribe(str(audio), batch_size=16 if device == "cuda" else 4)
    detected_lang = result.get("language", language or "?")
    if verbose:
        print(f"language: {detected_lang}", flush=True)

    # 2. Forced alignment → ±10ms timestamps
    if verbose:
        print("aligning...", flush=True)
    align_model, metadata = whisperx.load_align_model(
        language_code=detected_lang, device=device,
    )
    result = whisperx.align(
        result["segments"], align_model, metadata, str(audio), device,
        return_char_alignments=False,
    )

    # 3. Optional speaker diarization
    if diarize:
        if not hf_token:
            print("warning: --diarize requires --hf-token. Skipping diarization.", file=sys.stderr)
        else:
            if verbose:
                print("diarizing...", flush=True)
            diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
            diarize_segments = diarize_model(str(audio))
            result = whisperx.assign_word_speakers(diarize_segments, result)

    # 4. Flatten to raw word list
    raw: list[dict] = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            if "start" not in w or "end" not in w:
                continue
            # whisperx speaker format: "SPEAKER_00" → Scribe format: "speaker_0"
            speaker = w.get("speaker")
            if speaker and speaker.startswith("SPEAKER_"):
                speaker = "speaker_" + speaker[len("SPEAKER_"):]
            raw.append({"text": w["word"], "start": w["start"], "end": w["end"], "speaker_id": speaker})
    return raw


# ── Main transcription entry point ────────────────────────────────────────────

def transcribe(
    video: Path,
    edit_dir: Path,
    backend: str,
    language: str | None,
    model_size: str,
    device: str,
    compute_type: str,
    diarize: bool = False,
    hf_token: str | None = None,
    verbose: bool = True,
) -> Path:
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path}")
        return out_path

    if verbose:
        print("extracting audio...", flush=True)

    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio)
        if verbose:
            print(f"audio: {audio.stat().st_size / 1024 / 1024:.1f} MB", flush=True)

        if backend == "whisperx":
            raw = transcribe_wx(audio, language, model_size, device, compute_type, diarize, hf_token, verbose)
        else:
            raw = transcribe_fw(audio, language, model_size, device, compute_type, verbose)

    words = _build_word_list(raw)
    return _save(out_path, words, {"_source": backend, "_model": model_size, "_device": device}, verbose)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Transcribe a video locally (faster-whisper or whisperx). Outputs Scribe-compatible JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument("--edit-dir", type=Path, default=None,
                    help="Edit output directory (default: <video_parent>/edit)")
    ap.add_argument("--backend", choices=["faster-whisper", "whisperx"], default="faster-whisper",
                    help="Transcription backend (default: faster-whisper). "
                         "whisperx = better timestamps + optional diarization.")
    ap.add_argument("--language", type=str, default=None,
                    help="ISO language code e.g. 'ko', 'en'. Omit to auto-detect.")
    ap.add_argument("--model", type=str, default="base",
                    choices=["tiny", "tiny.en", "base", "base.en", "small", "small.en",
                             "medium", "medium.en", "large-v1", "large-v2", "large-v3"],
                    help="Whisper model size (default: base).")
    ap.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto",
                    help="Compute device (default: auto).")
    ap.add_argument("--compute-type", choices=["int8", "int8_float16", "float16", "float32"],
                    default=None, help="Precision (default: int8 for CPU, float16 for CUDA).")
    ap.add_argument("--diarize", action="store_true",
                    help="[whisperx only] Enable speaker diarization. Requires --hf-token.")
    ap.add_argument("--hf-token", type=str, default=None,
                    help="[whisperx diarization] HuggingFace token. "
                         "Accept pyannote terms at hf.co/pyannote/speaker-diarization-3.1 first.")
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or video.parent / "edit").resolve()

    device, compute_type = (detect_device() if args.device == "auto"
                            else (args.device, "float16" if args.device == "cuda" else "int8"))
    if args.compute_type:
        compute_type = args.compute_type

    transcribe(
        video=video,
        edit_dir=edit_dir,
        backend=args.backend,
        language=args.language,
        model_size=args.model,
        device=device,
        compute_type=compute_type,
        diarize=args.diarize,
        hf_token=args.hf_token,
    )


if __name__ == "__main__":
    main()
