"""sonic-forge transcribe: Parakeet's tokens and sentences shaped like Whisper verbose_json.

The model runs only with SONIC_FORGE_SLOW=1 on Apple silicon with the stt-mlx extra; the shaping
and the CLI run anywhere (the model is replaced by a stand-in).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sonic_forge import transcribe as stt  # noqa: E402


@dataclass
class Tok:
    text: str
    start: float
    end: float


@dataclass
class Sent:
    text: str
    start: float
    end: float
    tokens: list = field(default_factory=list)


@dataclass
class Result:
    text: str
    sentences: list


def heard() -> Result:
    s1 = Sent(" Say it back.", 0.0, 1.2, [Tok(" S", 0.0, 0.16), Tok("ay", 0.16, 0.3), Tok(" it", 0.3, 0.5),
                                          Tok(" back", 0.5, 1.0), Tok(".", 1.0, 1.2)])
    s2 = Sent(" Out loud, now.", 1.6, 2.9, [Tok(" Out", 1.6, 1.9), Tok(" lo", 1.9, 2.1), Tok("ud", 2.1, 2.3),
                                            Tok(",", 2.3, 2.35), Tok(" now", 2.4, 2.8), Tok(".", 2.8, 2.9)])
    return Result(" Say it back. Out loud, now.", [s1, s2])


class Shape(unittest.TestCase):
    def test_tokens_join_into_words_with_their_punctuation(self):
        words = stt.words_from_tokens(heard().sentences[0].tokens + heard().sentences[1].tokens)
        self.assertEqual(words, [
            {"word": "Say", "start": 0.0, "end": 0.3}, {"word": "it", "start": 0.3, "end": 0.5},
            {"word": "back.", "start": 0.5, "end": 1.2}, {"word": "Out", "start": 1.6, "end": 1.9},
            {"word": "loud,", "start": 1.9, "end": 2.35}, {"word": "now.", "start": 2.4, "end": 2.9},
        ])

    def test_verbose_json_shape(self):
        out = stt.shape(heard(), 3.25, stt.DEFAULT_MODEL, words=True)
        self.assertEqual(out["text"], "Say it back. Out loud, now.")
        self.assertEqual(out["language"], "english")
        self.assertEqual(out["duration"], 3.25)
        self.assertEqual(out["segments"], [{"id": 0, "start": 0.0, "end": 1.2, "text": "Say it back."},
                                           {"id": 1, "start": 1.6, "end": 2.9, "text": "Out loud, now."}])
        self.assertEqual(len(out["words"]), 6)

    def test_words_only_when_asked_and_language_unknown_for_v3(self):
        out = stt.shape(heard(), 3.25, "mlx-community/parakeet-tdt-0.6b-v3", words=False)
        self.assertNotIn("words", out)
        self.assertIsNone(out["language"])

    def test_silence_gives_no_segments(self):
        out = stt.shape(Result("", []), 0.0, stt.DEFAULT_MODEL, words=True)
        self.assertEqual((out["segments"], out["words"], out["duration"]), ([], [], 0.0))

    def test_missing_extra_and_missing_file_are_clear(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            stt.transcribe("/no/such/file.wav")
        f = Path(tempfile.mkdtemp()) / "a.wav"
        f.write_bytes(b"RIFF")
        with mock.patch("importlib.util.find_spec", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "stt-mlx"):
                stt.transcribe(f)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        from typer.testing import CliRunner

        from sonic_forge.cli import app

        fake = stt.shape(heard(), 3.25, stt.DEFAULT_MODEL, words="--words" in args)
        with mock.patch("sonic_forge.transcribe.transcribe", return_value=fake) as t:
            res = CliRunner().invoke(app, ["transcribe", *args])
        return res, t

    def test_json_with_words_is_the_only_thing_on_stdout(self):
        res, t = self.run_cli("memo.m4a", "--json", "--words")
        self.assertEqual(res.exit_code, 0, res.output)
        data = json.loads(res.stdout)
        self.assertEqual(data["words"][0], {"word": "Say", "start": 0.0, "end": 0.3})
        t.assert_called_once_with("memo.m4a", words=True, model=None)

    def test_plain_text_is_one_sentence_per_line(self):
        res, _ = self.run_cli("memo.m4a")
        self.assertEqual(res.stdout.strip().splitlines(), ["Say it back.", "Out loud, now."])

    def test_output_file(self):
        out = Path(tempfile.mkdtemp()) / "t.json"
        res, _ = self.run_cli("memo.m4a", "--json", "-o", str(out))
        self.assertEqual(res.exit_code, 0, res.output)
        self.assertEqual(json.loads(out.read_text())["segments"][1]["text"], "Out loud, now.")


class Doctor(unittest.TestCase):
    def test_json_says_what_this_install_can_do(self):
        from typer.testing import CliRunner

        from sonic_forge.cli import app

        res = CliRunner().invoke(app, ["doctor", "--json"])
        self.assertEqual(res.exit_code, 0, res.output)
        info = json.loads(res.stdout)
        self.assertEqual(set(info), {"version", "platform", "ffmpeg", "kokoro", "clone", "transcribe"})
        self.assertIn(info["clone"]["backend"], ("mlx", "torch", None))
        self.assertEqual(info["transcribe"]["model"], stt.DEFAULT_MODEL)


@unittest.skipUnless(os.environ.get("SONIC_FORGE_SLOW") == "1", "set SONIC_FORGE_SLOW=1 to run the real model")
class RealModel(unittest.TestCase):
    def test_hears_a_spoken_sentence(self):
        d = Path(tempfile.mkdtemp())
        subprocess.run(["say", "-o", str(d / "s.aiff"), "Say it back, out loud, before the conversation ends."], check=True)
        out = stt.transcribe(d / "s.aiff", words=True)
        self.assertIn("conversation", out["text"].lower())
        self.assertGreaterEqual(len(out["words"]), 8)
        self.assertTrue(all(w["end"] >= w["start"] for w in out["words"]))


if __name__ == "__main__":
    unittest.main()
