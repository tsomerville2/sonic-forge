"""End-to-end test for `sonic-forge narrate`.

Uses macOS `say` engine so no Kokoro/Edge install is required.
Skips on non-darwin platforms or if ffmpeg/ffprobe missing.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure we can import sonic_forge from source (not an installed package)
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sonic_forge.narrate import (  # noqa: E402
    PAUSE_POOLS,
    pick_pause,
    split_script,
    narrate,
)


def _tools_available() -> bool:
    return (
        shutil.which("ffmpeg") is not None
        and shutil.which("ffprobe") is not None
        and shutil.which("say") is not None  # macOS only
    )


SAMPLE_SCRIPT = """First paragraph. This is a short intro sentence.

Second paragraph. This follows after a blank line default pause.

[pause: medium]

Third paragraph after an explicit medium pause.

[pause: 1.2]

Fourth paragraph after a numeric pause.
"""


class PausePoolTests(unittest.TestCase):
    def test_known_labels_pick_from_pool(self):
        rng = random.Random(0)
        for label, pool in PAUSE_POOLS.items():
            v = pick_pause(label, rng)
            self.assertIn(v, pool, f"{label} → {v} not in pool")

    def test_numeric_gets_jitter(self):
        rng = random.Random(0)
        v = pick_pause("1.0", rng)
        self.assertGreaterEqual(v, 0.85)
        self.assertLessEqual(v, 1.15)

    def test_unknown_label_falls_back_to_default(self):
        rng = random.Random(0)
        v = pick_pause("nonsense", rng)
        self.assertIn(v, PAUSE_POOLS["medium"])


class SplitScriptTests(unittest.TestCase):
    def test_parses_text_and_pause_tuples(self):
        rng = random.Random(42)
        segments = list(split_script(SAMPLE_SCRIPT, rng))
        kinds = [s[0] for s in segments]
        self.assertIn("text", kinds)
        self.assertIn("pause", kinds)
        # Has 4 text paragraphs
        text_count = sum(1 for k in kinds if k == "text")
        self.assertEqual(text_count, 4)

    def test_explicit_pause_markup_parsed(self):
        rng = random.Random(42)
        segments = list(split_script("hello\n\n[pause: xlong]\n\nworld", rng))
        # hello / blank-pause / xlong-pause / world
        text_segs = [s for s in segments if s[0] == "text"]
        pause_segs = [s for s in segments if s[0] == "pause"]
        self.assertEqual(len(text_segs), 2)
        self.assertGreaterEqual(len(pause_segs), 1)


@unittest.skipUnless(_tools_available(), "requires macOS say + ffmpeg + ffprobe")
class NarrateEndToEndTests(unittest.TestCase):
    def test_generates_wav_and_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            script_path = td / "script.txt"
            script_path.write_text(SAMPLE_SCRIPT)
            out_wav = td / "out.wav"

            narrate(
                input_path=str(script_path),
                output_path=str(out_wav),
                engine="say",
                voice="Samantha",
                seed=123,
                verbose=False,
            )

            manifest_path = out_wav.with_suffix(".timing.json")
            self.assertTrue(out_wav.exists(), "WAV not created")
            self.assertGreater(out_wav.stat().st_size, 0, "WAV is empty")
            self.assertTrue(manifest_path.exists(), "Manifest not created")

            manifest = json.loads(manifest_path.read_text())
            self.assertIn("total_duration", manifest)
            self.assertIn("fps", manifest)
            self.assertIn("total_frames", manifest)
            self.assertIn("segments", manifest)
            self.assertGreater(manifest["total_duration"], 0)

            # total_duration should match ffprobe within 50ms
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(out_wav)],
                capture_output=True, text=True, check=True)
            ffprobe_dur = float(probe.stdout.strip())
            self.assertAlmostEqual(manifest["total_duration"], ffprobe_dur,
                                   delta=0.05)

            # At least one text segment and one pause segment
            kinds = [s["kind"] for s in manifest["segments"]]
            self.assertIn("text", kinds)
            self.assertIn("pause", kinds)

            # Each text segment carries its source text
            text_segs = [s for s in manifest["segments"] if s["kind"] == "text"]
            for ts in text_segs:
                self.assertIn("text", ts)
                self.assertTrue(ts["text"].strip())

    def test_no_manifest_flag_skips_json(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            script_path = td / "s.txt"
            script_path.write_text("Just one paragraph.\n")
            out_wav = td / "o.wav"

            narrate(
                input_path=str(script_path),
                output_path=str(out_wav),
                engine="say",
                voice="Samantha",
                seed=1,
                write_manifest=False,
                verbose=False,
            )
            self.assertTrue(out_wav.exists())
            self.assertFalse(out_wav.with_suffix(".timing.json").exists())


if __name__ == "__main__":
    unittest.main()
