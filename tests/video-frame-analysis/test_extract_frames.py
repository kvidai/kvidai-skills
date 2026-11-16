"""Behavioral tests with generated videos; runs on Windows and Linux."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/video-frame-analysis/scripts/extract_frames.py"
spec = importlib.util.spec_from_file_location("extract_frames", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class SelectionTests(unittest.TestCase):
    def test_cut_neighbors_and_scene_representatives(self):
        times = [i / 10 for i in range(20)]
        frames, cuts, _ = tool.select_frames(times, [0] * 10 + [0.8] + [0] * 9, "scene", 0.5, 80, 0.22, 0.025, 0.25)
        selected = {f["source_frame"]: f for f in frames}
        self.assertEqual(cuts, [10])
        self.assertTrue({0, 9, 10, 19}.issubset(selected))
        self.assertIn("scene_before", selected[9]["reasons"])
        self.assertIn("scene_after", selected[10]["reasons"])
        self.assertEqual(sum("scene_representative" in f["reasons"] for f in frames), 2)

    def test_irregular_timestamps_dense_and_cap(self):
        times = [0, 0.03, 0.2, 0.8, 0.83, 1.9]
        frames, _, _ = tool.select_frames(times, [0] * 6, "dense", 0.1, 80, 0.22, 0.025, 0.25)
        indices = [f["source_frame"] for f in frames]
        self.assertEqual(indices, sorted(set(indices)))
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 5)
        for frame in frames:
            self.assertEqual(frame["timestamp_seconds"], times[frame["source_frame"]])
        capped, _, candidates = tool.select_frames(times, [0] * 6, "dense", 0.01, 2, 0.22, 0.025, 0.25)
        self.assertEqual([f["source_frame"] for f in capped], [0, 5])
        self.assertGreater(candidates, 2)

    def test_motion_peak_surroundings(self):
        times = [i / 20 for i in range(21)]
        scores = [0] * 21
        scores[8] = 0.1
        frames, _, _ = tool.select_frames(times, scores, "motion", 1, 80, 0.22, 0.025, 0.25)
        peak = next(f for f in frames if "motion_peak" in f["reasons"])
        self.assertEqual(peak["source_frame"], 8)
        self.assertTrue(any("motion_before" in f["reasons"] for f in frames))
        self.assertTrue(any("motion_after" in f["reasons"] for f in frames))


class CLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tool.dependencies()
        cls.temp = tempfile.TemporaryDirectory(prefix="frames-test-")
        cls.root = Path(cls.temp.name) / "한글 영상 공백"
        cls.root.mkdir()
        cls.video = cls.root / "reference clip.mkv"
        tool.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=black:s=160x90:r=10:d=1",
                  "-f", "lavfi", "-i", "color=white:s=160x90:r=10:d=1", "-filter_complex",
                  "[0:v][1:v]concat=n=2:v=1:a=0[out]", "-map", "[out]", "-c:v", "ffv1", str(cls.video)])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def invoke(self, *args, env=None):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    def test_modes_artifact_consistency_and_original_preserved(self):
        from PIL import Image
        before = self.video.read_bytes()
        for mode in ("motion", "scene", "dense"):
            with self.subTest(mode=mode):
                output = self.root / mode
                result = self.invoke(self.video, "--output", output, "--mode", mode)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
                report = json.loads((output / "frames.json").read_text(encoding="utf-8"))
                self.assertEqual(report["decoded_frames"], 20)
                self.assertEqual(report["frames"][0]["source_frame"], 0)
                self.assertEqual(report["frames"][-1]["source_frame"], 19)
                self.assertEqual(report["detected_scene_changes"][0]["source_frame"], 10)
                self.assertEqual(len(list((output / "frames").glob("*.png"))), len(report["frames"]))
                with (output / "frames.csv").open(encoding="utf-8", newline="") as file:
                    self.assertEqual(len(list(csv.DictReader(file))), len(report["frames"]))
                for frame in report["frames"]:
                    self.assertIn(frame["image"], (output / "index.md").read_text(encoding="utf-8"))
                    with Image.open(output / frame["image"]) as image:
                        self.assertEqual(image.size, (160, 90))
                        brightness = image.convert("L").getpixel((0, 0))
                        self.assertEqual(brightness, 0 if frame["source_frame"] < 10 else 255)
                for sheet in report["contact_sheets"]:
                    with Image.open(output / sheet) as image:
                        image.verify()
        self.assertEqual(self.video.read_bytes(), before)

    def test_single_frame_static_and_cap_warning(self):
        single = self.root / "single.mkv"
        tool.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=64x64:r=1",
                  "-frames:v", "1", "-c:v", "ffv1", str(single)])
        output = self.root / "one-frame"
        result = self.invoke(single, "--output", output, "--mode", "scene")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((output / "frames.json").read_text(encoding="utf-8"))
        self.assertEqual(len(report["frames"]), 1)
        self.assertEqual(report["detected_scene_changes"], [])
        self.assertTrue({"first", "last"}.issubset(report["frames"][0]["reasons"]))
        capped = self.root / "capped"
        result = self.invoke(self.video, "--output", capped, "--mode", "dense", "--interval", 0.01, "--max-frames", 2)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((capped / "frames.json").read_text(encoding="utf-8"))
        self.assertEqual(len(report["frames"]), 2)
        self.assertTrue(report["warnings"])

    def test_existing_output_and_bad_inputs(self):
        output = self.root / "existing"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        self.assertNotEqual(self.invoke(self.video, "--output", output).returncode, 0)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")
        invalid = self.root / "invalid.mp4"
        invalid.write_bytes(b"not a video")
        for source in (self.root / "missing.mp4", invalid):
            destination = self.root / "must-not-exist"
            result = self.invoke(source, "--output", destination)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(destination.exists())
        for option, value in (("--interval", "0"), ("--interval", "nan"), ("--scene-threshold", "2"), ("--max-frames", "1")):
            self.assertNotEqual(self.invoke(self.video, "--output", self.root / "unused", option, value).returncode, 0)

    def test_dependency_diagnostic(self):
        environment = dict(os.environ, PATH="")
        result = self.invoke("--check", env=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"Missing executable", result.stderr)

    def test_variable_frame_rate_uses_actual_timestamps(self):
        video = self.root / "variable-rate.mkv"
        tool.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=96x64:r=10:d=1",
                  "-vf", "setpts='if(lt(N,5),N,5+(N-5)*3)'", "-fps_mode", "passthrough",
                  "-c:v", "ffv1", str(video)])
        output = self.root / "vfr"
        result = self.invoke(video, "--output", output, "--mode", "dense", "--interval", 0.1)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((output / "frames.json").read_text(encoding="utf-8"))
        self.assertEqual(report["decoded_frames"], 10)
        self.assertAlmostEqual(report["last_timestamp_seconds"], 1.7)
        for frame in report["frames"]:
            index = frame["source_frame"]
            expected = index / 10 if index < 5 else (5 + (index - 5) * 3) / 10
            self.assertAlmostEqual(frame["timestamp_seconds"], expected)


if __name__ == "__main__":
    unittest.main()
