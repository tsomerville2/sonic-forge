"""Cloned voices: reference prep, chunking, engine resolution, and narrate's parallel path.

The model itself is exercised only with SONIC_FORGE_SLOW=1 (it downloads ~1.5 GB and needs the
clone extra); everything else runs anywhere with ffmpeg.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sonic_forge import clone  # noqa: E402
from sonic_forge.narrate import narrate, probe_duration  # noqa: E402
from sonic_forge.tts import resolve_voice  # noqa: E402


def tone(path: Path, seconds: float, silence_before: float = 0.0, silence_after: float = 0.0) -> None:
    """A test 'voice': a sine tone with optional silence around it."""
    parts = []
    if silence_before:
        parts.append(f"aevalsrc=0:d={silence_before}[a]")
    parts.append(f"sine=f=220:d={seconds}[b]")
    if silence_after:
        parts.append(f"aevalsrc=0:d={silence_after}[c]")
    labels = "".join(x for x, used in (("[a]", silence_before), ("[b]", True), ("[c]", silence_after)) if used)
    graph = ";".join(parts) + f";{labels}concat=n={labels.count('[')}:v=0:a=1"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_complex", graph, "-ar", "24000", "-ac", "1", str(path)], check=True)


class ReferencePrep(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_trims_silence_and_caps_length(self):
        raw = self.dir / "raw.wav"
        tone(raw, 25, silence_before=2, silence_after=2)
        seconds = clone.prep_reference(raw, self.dir / "ref.wav")
        self.assertAlmostEqual(seconds, 20.0, delta=0.1)
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate,channels",
                              "-of", "json", str(self.dir / "ref.wav")], capture_output=True, text=True).stdout
        stream = json.loads(out)["streams"][0]
        self.assertEqual((stream["sample_rate"], stream["channels"]), ("24000", 1))

    def test_refuses_too_little_speech(self):
        raw = self.dir / "short.wav"
        tone(raw, 3, silence_before=4)
        with self.assertRaisesRegex(ValueError, "at least 5s"):
            clone.prep_reference(raw, self.dir / "ref.wav")
        self.assertFalse((self.dir / "ref.wav").exists())


class Chunking(unittest.TestCase):
    def test_short_text_is_one_call(self):
        self.assertEqual(clone._chunks("Hello  there.\nFriend."), ["Hello there. Friend."])

    def test_long_paragraph_splits_at_sentences_under_the_limit(self):
        sentence = "This sentence is about sixty characters long, more or less ok."
        chunks = clone._chunks(" ".join([sentence] * 12))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= clone.MAX_CHARS_PER_CALL for c in chunks))
        self.assertEqual(" ".join(chunks), " ".join([sentence] * 12))


class Engine(unittest.TestCase):
    def test_chatterbox_takes_a_reference_path(self):
        self.assertEqual(resolve_voice(engine="chatterbox", voice="me.wav"), ("chatterbox", "me.wav"))

    def test_chatterbox_without_a_reference_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "reference"):
            resolve_voice(engine="chatterbox")

    def test_default_jobs_stay_within_cores_and_work(self):
        with mock.patch("os.cpu_count", return_value=16):
            self.assertEqual(clone.default_jobs(9), 4)
            self.assertEqual(clone.default_jobs(2), 2)
        with mock.patch("os.cpu_count", return_value=2):
            self.assertEqual(clone.default_jobs(9), 1)


class NarrateWithClone(unittest.TestCase):
    def test_every_paragraph_is_spoken_in_one_parallel_batch_and_timed(self):
        d = Path(tempfile.mkdtemp())
        script = d / "script.txt"
        script.write_text("First line.\n\n[pause: short]\n\nSecond line.\n\nThird line.\n")
        calls = []

        def fake_synthesize(texts, reference, out_paths, jobs=None, seed=None, verbose=True):
            calls.append((texts, reference, jobs, seed))
            for i, p in enumerate(out_paths):
                tone(Path(p), 1.0 + i)
            return [1.0 + i for i in range(len(texts))]

        with mock.patch("sonic_forge.clone.synthesize", side_effect=fake_synthesize):
            narrate(script, d / "out.wav", engine="chatterbox", voice="me.wav", seed=7,
                    pause_mode="explicit", jobs=3, verbose=False)

        self.assertEqual(calls, [(["First line.", "Second line.", "Third line."], "me.wav", 3, 7)])
        timing = json.loads((d / "out.timing.json").read_text())
        texts = [s for s in timing["segments"] if s["kind"] == "text"]
        self.assertEqual([round(s["duration"], 1) for s in texts], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(probe_duration(d / "out.wav"), timing["total_duration"], delta=0.05)


@unittest.skipUnless(os.environ.get("SONIC_FORGE_SLOW") == "1", "set SONIC_FORGE_SLOW=1 to run the real model")
class RealModel(unittest.TestCase):
    def test_clones_a_voice_end_to_end(self):
        d = Path(tempfile.mkdtemp())
        sample = os.environ.get("SONIC_FORGE_SAMPLE")
        if not sample:
            sample = str(d / "sample.aiff")
            subprocess.run(["say", "-o", sample, "This is a short sample of my speaking voice, recorded so the "
                            "narrator can learn how I sound when I tell a story."], check=True)
        clone.prep_reference(sample, d / "me.wav")
        script = d / "script.txt"
        script.write_text("Hello there.\n\nThis is my cloned voice.\n")
        narrate(script, d / "out.wav", engine="chatterbox", voice=str(d / "me.wav"), seed=1, pause_mode="explicit", jobs=2)
        timing = json.loads((d / "out.timing.json").read_text())
        self.assertEqual(len([s for s in timing["segments"] if s["kind"] == "text"]), 2)
        self.assertGreater(timing["total_duration"], 1.5)


if __name__ == "__main__":
    unittest.main()
