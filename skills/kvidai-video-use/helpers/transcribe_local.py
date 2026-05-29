"""Transcribe a video locally with faster-whisper (CPU / CUDA GPU).

Outputs Scribe-compatible JSON: {"words": [...]} — works with pack_transcripts.py.

Requirements:
    pip install faster-whisper
    ffmpeg on PATH (https://ffmpeg.org/download.html)

GPU (NVIDIA CUDA):
    pip install faster-whisper
    # also needs CUDA toolkit matching your driver
    python transcribe_local.py video.mp4 --device cuda

CPU (any platform, including Windows, macOS, Linux):
    python transcribe_local.py video.mp4 --device cpu

NPU note:
    faster-whisper does not support NPU directly.
    Intel OpenVINO NPU → use openvino-whisper (separate package).
    Apple Neural Engine → use mlx-whisper on macOS (separate package).

Usage:
    python helpers/transcribe_local.py <video>
    python helpers/transcribe_local.py <video> --edit-dir /path/to/edit
    python helpers/transcribe_local.py <video> --language ko
    python helpers/transcribe_local.py <video> --device cuda --compute-type float16
    python helpers/transcribe_local.py <video> --model large-v3
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


# ── Device auto-detection ────────────────────────────────────────────────────

def detect_device() -> tuple[str, str]:
    """Return (device, compute_type) based on available hardware."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass
    try:
        from faster_whisper import WhisperModel
        # Quick probe: load tiny model on cuda
        WhisperModel("tiny", device="cuda", compute_type="float16")
        return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


# ── Audio extraction ─────────────────────────────────────────────────────────

def extract_audio(video: Path, dest: Path) -> None:
    """Extract mono 16 kHz WAV via ffmpeg (cross-platform)."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{result.stderr.decode(errors='replace')}")


# ── Transcription ────────────────────────────────────────────────────────────

def transcribe(
    video: Path,
    edit_dir: Path,
    language: str | None,
    model_size: str,
    device: str,
    compute_type: str,
    verbose: bool = True,
) -> Path:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper not installed. Run: pip install faster-whisper")

    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path}")
        return out_path

    if verbose:
        print(f"device: {device} / compute: {compute_type} / model: {model_size}")
        print("extracting audio...", flush=True)

    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio)
        size_mb = audio.stat().st_size / 1024 / 1024
        if verbose:
            print(f"audio: {size_mb:.1f} MB — loading model...", flush=True)

        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        if verbose:
            print("transcribing...", flush=True)

        segments, info = model.transcribe(
            str(audio),
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )

        if verbose:
            print(f"detected language: {info.language} ({info.language_probability:.1%})", flush=True)

        # Convert to Scribe-compatible word list
        words: list[dict] = []
        prev_end = 0.0

        for seg in segments:
            if not seg.words:
                continue
            for w in seg.words:
                # Insert spacing entry for gaps ≥ 0.1s (used by pack_transcripts.py)
                gap = w.start - prev_end
                if gap >= 0.1 and prev_end > 0:
                    words.append({
                        "type": "spacing",
                        "start": prev_end,
                        "end": w.start,
                        "text": "",
                    })
                words.append({
                    "type": "word",
                    "text": w.word.strip(),
                    "start": w.start,
                    "end": w.end,
                    "speaker_id": None,
                })
                prev_end = w.end

    payload = {
        "words": words,
        "_source": "faster-whisper",
        "_model": model_size,
        "_device": device,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if verbose:
        kb = out_path.stat().st_size / 1024
        word_count = sum(1 for w in words if w["type"] == "word")
        print(f"saved: {out_path} ({kb:.1f} KB, {word_count} words)")

    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Transcribe a video with faster-whisper (CPU/GPU). Outputs Scribe-compatible JSON."
    )
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--edit-dir", type=Path, default=None,
        help="Edit output directory (default: <video_parent>/edit)",
    )
    ap.add_argument(
        "--language", type=str, default=None,
        help="ISO language code, e.g. 'ko', 'en'. Omit to auto-detect.",
    )
    ap.add_argument(
        "--model", type=str, default="base",
        choices=["tiny", "tiny.en", "base", "base.en", "small", "small.en",
                 "medium", "medium.en", "large-v1", "large-v2", "large-v3"],
        help="Whisper model size (default: base). Larger = more accurate, slower.",
    )
    ap.add_argument(
        "--device", type=str, default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Compute device (default: auto — cuda if available, else cpu).",
    )
    ap.add_argument(
        "--compute-type", type=str, default=None,
        choices=["int8", "int8_float16", "float16", "float32"],
        help="Precision (default: int8 for CPU, float16 for CUDA).",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or video.parent / "edit").resolve()

    # Resolve device
    if args.device == "auto":
        device, compute_type = detect_device()
    else:
        device = args.device
        compute_type = args.compute_type or ("float16" if device == "cuda" else "int8")

    if args.compute_type:
        compute_type = args.compute_type

    transcribe(
        video=video,
        edit_dir=edit_dir,
        language=args.language,
        model_size=args.model,
        device=device,
        compute_type=compute_type,
    )


if __name__ == "__main__":
    main()
