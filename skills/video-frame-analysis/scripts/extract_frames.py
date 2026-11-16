#!/usr/bin/env python3
"""Select inspectable video frames using local FFmpeg, ffprobe and Pillow."""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class AnalysisError(Exception):
    pass


def run(command: list[str]) -> str:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise AnalysisError(result.stderr.decode("utf-8", errors="replace")[-4000:])
    return result.stdout.decode("utf-8", errors="replace")


def dependencies() -> dict:
    found = {name: shutil.which(name) for name in ("ffmpeg", "ffprobe")}
    missing = [name for name, path in found.items() if not path]
    if missing:
        raise AnalysisError("Missing executable(s) on PATH: " + ", ".join(missing))
    try:
        import PIL
    except ImportError as exc:
        raise AnalysisError("Missing Pillow. Install: python -m pip install Pillow") from exc
    return {
        "python": sys.version.split()[0], "pillow": PIL.__version__,
        **{name: run([path, "-version"]).splitlines()[0] for name, path in found.items()},
    }


def probe(source: Path) -> tuple[dict, list[float]]:
    data = json.loads(run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
        "-show_streams", "-show_entries",
        "stream=width,height,avg_frame_rate:frame=best_effort_timestamp_time",
        "-of", "json", str(source),
    ]))
    if not data.get("streams") or not data.get("frames"):
        raise AnalysisError("Input has no decodable video frames.")
    try:
        times = [float(frame["best_effort_timestamp_time"]) for frame in data["frames"]]
    except (ValueError, KeyError) as exc:
        raise AnalysisError("Video frames lack usable presentation timestamps.") from exc
    if any(not math.isfinite(t) for t in times) or any(b < a for a, b in zip(times, times[1:])):
        raise AnalysisError("Frame timestamps must be finite and nondecreasing.")
    stream = data["streams"][0]
    stream["first_pts_seconds"] = times[0]
    return stream, [t - times[0] for t in times]


def measure(source: Path, expected: int) -> list[float]:
    """Decode every frame to a small grayscale image; keep only adjacent MAD scores."""
    size = 96 * 54
    scores: list[float] = []
    previous = None
    # A temporary stderr file avoids pipe deadlocks on a long corrupt input.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen([
            "ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(source), "-map", "0:v:0",
            "-vf", "scale=96:54", "-fps_mode", "passthrough", "-pix_fmt", "gray",
            "-f", "rawvideo", "pipe:1",
        ], stdout=subprocess.PIPE, stderr=errors)
        try:
            while True:
                frame = process.stdout.read(size)
                if not frame:
                    break
                if len(frame) != size:
                    raise AnalysisError("Incomplete decoded analysis frame.")
                score = (sum(abs(a - b) for a, b in zip(previous, frame)) / (255 * size)
                         if previous is not None else 0.0)
                scores.append(score)
                previous = frame
            status = process.wait()
            if status:
                errors.seek(0)
                raise AnalysisError(errors.read().decode("utf-8", errors="replace")[-4000:])
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()
    if len(scores) != expected:
        raise AnalysisError(f"Probe/decode frame count mismatch: {expected} vs {len(scores)}.")
    return scores


def nearest(times: list[float], target: float) -> int:
    i = bisect.bisect_left(times, target)
    if i == len(times):
        return i - 1
    if i and target - times[i - 1] <= times[i] - target:
        return i - 1
    return i


def spread(items: list[int], limit: int) -> list[int]:
    if limit <= 0:
        return []
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[len(items) // 2]]
    return [items[round(i * (len(items) - 1) / (limit - 1))] for i in range(limit)]


def select_frames(times: list[float], scores: list[float], mode: str,
                  interval: float, maximum: int, scene_threshold: float,
                  motion_threshold: float, min_gap: float) -> tuple[list[dict], list[int], int]:
    """Protect endpoints, then prioritize cuts, coverage, and motion details."""
    reasons: dict[int, set[str]] = {}
    priorities: dict[int, int] = {}

    def add(index: int, reason: str, priority: int) -> None:
        reasons.setdefault(index, set()).add(reason)
        priorities[index] = min(priority, priorities.get(index, priority))

    add(0, "first", 0)
    add(len(times) - 1, "last", 0)
    cuts: list[int] = []
    for i in range(1, len(times)):
        # Peaks avoid flagging every frame during a rapid continuous transition.
        peak = scores[i] >= scores[i - 1] and (i + 1 == len(times) or scores[i] > scores[i + 1])
        if scores[i] >= scene_threshold and peak and (not cuts or times[i] - times[cuts[-1]] >= min_gap):
            cuts.append(i)
            add(i - 1, "scene_before", 1)
            add(i, "scene_after", 1)

    if mode == "scene":
        bounds = [0, *cuts, len(times)]
        for start, end in zip(bounds, bounds[1:]):
            midpoint = (times[start] + times[end - 1]) / 2
            add(max(start, min(end - 1, nearest(times, midpoint))), "scene_representative", 2)
    else:
        # Iterate actual timestamps, avoiding millions of grid points for tiny intervals.
        target = interval
        for i, timestamp in enumerate(times):
            if timestamp >= target:
                add(nearest(times, target), "interval", 2)
                target = (math.floor(timestamp / interval) + 1) * interval
        if mode == "motion":
            last_peak = -math.inf
            for i in range(1, len(times)):
                if (scores[i] >= motion_threshold and scores[i] >= scores[i - 1]
                        and (i + 1 == len(times) or scores[i] > scores[i + 1])
                        and times[i] - last_peak >= min_gap and i not in cuts):
                    add(i, "motion_peak", 3)
                    add(nearest(times, max(0, times[i] - min_gap / 2)), "motion_before", 4)
                    add(nearest(times, times[i] + min_gap / 2), "motion_after", 4)
                    last_peak = times[i]

    candidates = len(reasons)
    chosen: list[int] = []
    for priority in sorted(set(priorities.values())):
        group = sorted(i for i, p in priorities.items() if p == priority)
        chosen.extend(spread(group, maximum - len(chosen)))
    frames = [{"source_frame": i, "timestamp_seconds": times[i],
               "change_score": round(scores[i], 6), "reasons": sorted(reasons[i])}
              for i in sorted(chosen)]
    return frames, cuts, candidates


def timecode(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def extract(source: Path, folder: Path, frames: list[dict]) -> None:
    frames_dir = folder / "frames"
    frames_dir.mkdir()
    expression = "+".join(f"eq(n,{frame['source_frame']})" for frame in frames)
    filter_file = folder / "selection-filter.txt"
    filter_file.write_text("select='" + expression + "'", encoding="utf-8")
    run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(source), "-map", "0:v:0",
         "-filter_script:v", str(filter_file), "-fps_mode", "vfr",
         str(frames_dir / "%06d.png")])
    filter_file.unlink()
    generated = sorted(frames_dir.glob("*.png"))
    if len(generated) != len(frames):
        raise AnalysisError("Extracted image count differs from selected frame count.")
    for order, (frame, path) in enumerate(zip(frames, generated), 1):
        stamp = timecode(frame["timestamp_seconds"])
        name = f"frame_{order:04d}_f{frame['source_frame']:08d}_{stamp.replace(':', '-')}.png"
        path.rename(frames_dir / name)
        frame.update(order=order, timecode=stamp, image="frames/" + name)


def sheets(folder: Path, frames: list[dict]) -> list[str]:
    from PIL import Image, ImageDraw, ImageOps
    pages = []
    columns, per_page, width, height = 4, 20, 320, 220
    for offset in range(0, len(frames), per_page):
        batch = frames[offset:offset + per_page]
        rows = math.ceil(len(batch) / columns)
        sheet = Image.new("RGB", (columns * width, rows * height), "#171717")
        draw = ImageDraw.Draw(sheet)
        for cell, frame in enumerate(batch):
            x, y = cell % columns * width, cell // columns * height
            with Image.open(folder / frame["image"]) as img:
                thumb = ImageOps.contain(img.convert("RGB"), (width - 12, 172))
            sheet.paste(thumb, (x + (width - thumb.width) // 2, y + (172 - thumb.height) // 2))
            draw.text((x + 6, y + 177), f"#{frame['order']:04d}  {frame['timecode']}  f{frame['source_frame']}", fill="white")
            draw.text((x + 6, y + 195), ", ".join(frame["reasons"])[:47], fill="#bbbbbb")
        name = f"contact-sheet-{len(pages) + 1:03d}.jpg"
        sheet.save(folder / name, quality=90)
        pages.append(name)
    return pages


def write_outputs(folder: Path, report: dict) -> None:
    (folder / "frames.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (folder / "frames.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["order", "source_frame", "timestamp_seconds", "timecode", "image", "change_score", "reasons"])
        for frame in report["frames"]:
            writer.writerow([frame[key] for key in ("order", "source_frame", "timestamp_seconds", "timecode", "image", "change_score")] + [";".join(frame["reasons"])])
    lines = ["# Video frame analysis", "", f"Mode: {report['config']['mode']}; selected {len(report['frames'])} of {report['candidate_count']} candidates.",
             "", "Times are relative to the first decoded video frame. Source frame numbers are zero-based.",
             "Pixel-change candidates need visual review; they do not establish semantic action boundaries.", ""]
    for warning in report["warnings"]:
        lines += [f"Warning: {warning}", ""]
    for page in report["contact_sheets"]:
        lines += [f"![{page}]({page})", ""]
    lines += ["| # | Time | Source frame | Reasons | Image |", "|---|---|---|---|---|"]
    for frame in report["frames"]:
        lines.append(f"| {frame['order']} | {frame['timecode']} | {frame['source_frame']} | {', '.join(frame['reasons'])} | [Open]({frame['image']}) |")
    (folder / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def finite_positive(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return number


def threshold(value: str) -> float:
    number = finite_positive(value)
    if number > 1:
        raise argparse.ArgumentTypeError("must be in (0, 1]")
    return number


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("input", nargs="?", type=Path, help="Local input video")
    cli.add_argument("--output", type=Path, help="New output directory (must not exist)")
    cli.add_argument("--check", action="store_true", help="Check dependencies and exit")
    cli.add_argument("--mode", choices=("motion", "scene", "dense"), default="motion")
    cli.add_argument("--interval", type=finite_positive, default=None, help="Coverage spacing in seconds (motion: 0.5; dense: 0.25)")
    cli.add_argument("--max-frames", type=int, default=80, help="Output image cap, at least 2 (default: 80)")
    cli.add_argument("--scene-threshold", type=threshold, default=0.22, help="Adjacent grayscale change threshold (default: 0.22)")
    cli.add_argument("--motion-threshold", type=threshold, default=0.025, help="Motion peak threshold (default: 0.025)")
    cli.add_argument("--min-gap", type=finite_positive, default=0.25, help="Minimum spacing between detected peaks, seconds")
    return cli


def main(argv: list[str] | None = None) -> int:
    cli = parser()
    args = cli.parse_args(argv)
    if not args.check and (args.input is None or args.output is None):
        cli.error("input and --output are required unless --check is used")
    if args.max_frames < 2:
        cli.error("--max-frames must be at least 2")
    try:
        versions = dependencies()
        if args.check:
            print(json.dumps(versions, ensure_ascii=True, indent=2))
            return 0
        source = args.input.resolve()
        destination = args.output.absolute()
        if not source.is_file():
            raise AnalysisError(f"Input is not a file: {source}")
        if destination.exists() or destination.is_symlink():
            raise AnalysisError(f"Output already exists; choose a new directory: {destination}")
        interval = args.interval if args.interval is not None else (0.25 if args.mode == "dense" else 0.5)
        print("Probing video timestamps...", file=sys.stderr)
        stream, times = probe(source)
        print(f"Measuring change across {len(times)} frames...", file=sys.stderr)
        scores = measure(source, len(times))
        frames, cuts, candidates = select_frames(times, scores, args.mode, interval, args.max_frames,
                                                 args.scene_threshold, args.motion_threshold, args.min_gap)
        warnings = []
        if candidates > len(frames):
            warnings.append(f"Frame cap removed {candidates - len(frames)} candidates. Increase --max-frames for full coverage.")
        report = {
            "schema_version": 1, "source": str(source), "video": stream,
            "decoded_frames": len(times), "last_timestamp_seconds": times[-1],
            "config": {"mode": args.mode, "interval_seconds": interval, "max_frames": args.max_frames,
                       "scene_threshold": args.scene_threshold, "motion_threshold": args.motion_threshold,
                       "min_gap_seconds": args.min_gap},
            "dependencies": versions, "candidate_count": candidates,
            "detected_scene_changes": [{"source_frame": i, "timestamp_seconds": times[i]} for i in cuts],
            "warnings": warnings, "frames": frames,
        }
        digest = hashlib.sha256()
        with source.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        report["source_sha256"] = digest.hexdigest()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".frame-analysis-", dir=destination.parent) as temp:
            staging = Path(temp) / "result"
            staging.mkdir()
            print(f"Extracting {len(frames)} images...", file=sys.stderr)
            extract(source, staging, frames)
            report["contact_sheets"] = sheets(staging, frames)
            write_outputs(staging, report)
            staging.rename(destination)
        print(f"Created {len(frames)} frames and {len(report['contact_sheets'])} contact sheets: {destination}")
        for warning in warnings:
            print("Warning: " + warning, file=sys.stderr)
        return 0
    except (AnalysisError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
