"""Worker fleets: script_segments, speak_clip, narrate_from_clips, `narrate --segments/--from-clips`, `clip`.

A narration spoken paragraph by paragraph on other machines and assembled here must be the same
WAV and the same timing manifest, byte for byte, as `narrate` speaking it all in one place. The
"voice" is a distinct sine tone per paragraph, so these run anywhere with ffmpeg and no TTS.
Set SONIC_FORGE_SLOW=1 to also check it with real Kokoro and a real cloned voice.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sonic_forge import clone  # noqa: E402
from sonic_forge import narrate as N  # noqa: E402

HAVE_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

SCRIPT = """Welcome to the CI/CD tour.
It starts on two lines.

Second paragraph, plain.

[pause: long]

Third, after a long pause.
[pause: short]

[pause: 0.3]
Fourth: NASA has the floor.


Fifth and last.
"""
PHONICS = {"CI/CD": "see eye see dee", "NASA": "nassa"}


def tone(path: Path, freq: int, seconds: float, rate: int = 22050) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f={freq}:d={seconds}",
                    "-ar", str(rate), "-ac", "1", str(path)], check=True)


def wav_format(path: Path) -> tuple[int, int, int]:
    with wave.open(str(path)) as w:
        return w.getnchannels(), w.getsampwidth(), w.getframerate()


@unittest.skipUnless(HAVE_FFMPEG, "needs ffmpeg and ffprobe")
class FromClipsMatchesNarrate(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.script = self.d / "script.txt"
        self.script.write_text(SCRIPT)
        self.phonics = self.d / "phonics.json"
        self.phonics.write_text(json.dumps(PHONICS))
        self.tones: dict[str, Path] = {}  # paragraph text (as spoken) -> its tone

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def plan(self, mode, seed):
        return N.script_segments(SCRIPT, phonics=str(self.phonics), pause_mode=mode, seed=seed)

    def make_tones(self, plan, rate=22050):
        for seg in plan:
            if seg["kind"] == "text":
                p = self.d / f"tone_{seg['index']}.wav"
                tone(p, 300 + 110 * seg["index"], 0.4 + 0.15 * seg["index"], rate)
                self.tones[seg["text"]] = p

    def fake_tts(self, spoken):
        def _tts(text, out_path, engine, voice, lang):
            spoken.append(text)
            shutil.copyfile(self.tones[text], out_path)
        return _tts

    def fake_synthesize(self, calls):
        def _synth(texts, reference, out_paths, jobs=None, seed=None, verbose=True):
            calls.append({"texts": list(texts), "reference": reference, "jobs": jobs, "seed": seed})
            for t, p in zip(texts, out_paths):
                shutil.copyfile(self.tones[t], p)
            return [0.0] * len(texts)
        return _synth

    def narrate_whole(self, out, mode, seed, engine="say", voice=None):
        spoken: list[str] = []
        calls: list[dict] = []
        with mock.patch.object(N, "_tts_paragraph", side_effect=self.fake_tts(spoken)), \
                mock.patch("sonic_forge.clone.synthesize", side_effect=self.fake_synthesize(calls)):
            N.narrate(self.script, out, engine=engine, voice=voice, seed=seed, pause_mode=mode,
                      phonics=str(self.phonics), verbose=False)
        return spoken, calls

    def assert_same(self, a: Path, b: Path):
        self.assertEqual(a.read_bytes(), b.read_bytes(), "WAVs differ")
        self.assertEqual(json.loads(a.with_suffix(".timing.json").read_text()),
                         json.loads(b.with_suffix(".timing.json").read_text()))
        self.assertEqual(a.with_suffix(".timing.json").read_bytes(), b.with_suffix(".timing.json").read_bytes())

    def test_raw_clips_give_byte_identical_wav_and_manifest(self):
        for mode in ("legacy", "explicit"):
            with self.subTest(mode=mode):
                plan = self.plan(mode, 608)
                self.make_tones(plan)
                whole = self.d / f"whole-{mode}.wav"
                spoken, _ = self.narrate_whole(whole, mode, 608)
                # script_segments' text segments are exactly what narrate speaks, in order.
                self.assertEqual(spoken, [s["text"] for s in plan if s["kind"] == "text"])
                clips = self.d / f"clips-{mode}"
                clips.mkdir()
                for seg in plan:
                    if seg["kind"] == "text":
                        shutil.copyfile(self.tones[seg["text"]], clips / N.clip_name(seg["index"]))
                parts = self.d / f"parts-{mode}.wav"
                N.narrate_from_clips(self.script, clips, parts, seed=608, pause_mode=mode,
                                     phonics=str(self.phonics), verbose=False)
                self.assert_same(whole, parts)

    def test_clips_from_speak_clip_give_byte_identical_wav_and_manifest(self):
        # 44.1 kHz "voices" (like macOS say): speak_clip resamples once, as narrate does.
        for mode in ("legacy", "explicit"):
            with self.subTest(mode=mode):
                plan = self.plan(mode, 11)
                self.make_tones(plan, rate=44100)
                whole = self.d / f"whole-{mode}.wav"
                self.narrate_whole(whole, mode, 11)
                clips = self.d / f"clips-{mode}"
                spoken: list[str] = []
                with mock.patch.object(N, "_tts_paragraph", side_effect=self.fake_tts(spoken)):
                    # Workers get the raw script paragraphs and the phonics file, in any order.
                    raw_paragraphs = N.script_segments(SCRIPT, pause_mode=mode, seed=11)
                    for seg in reversed([s for s in raw_paragraphs if s["kind"] == "text"]):
                        out = N.speak_clip(seg["text"], clips / N.clip_name(seg["index"]), engine="say",
                                           seed=11, index=seg["index"], phonics=str(self.phonics))
                        self.assertEqual(wav_format(out), (1, 2, 24000))
                self.assertEqual(sorted(spoken), sorted(s["text"] for s in plan if s["kind"] == "text"))
                parts = self.d / f"parts-{mode}.wav"
                N.narrate_from_clips(self.script, clips, parts, engine="say", seed=11, pause_mode=mode,
                                     phonics=str(self.phonics), verbose=False)
                self.assert_same(whole, parts)

    def test_cloned_voice_assembly_is_levelled_like_narrate(self):
        for mode in ("legacy", "explicit"):
            with self.subTest(mode=mode):
                plan = self.plan(mode, 7)
                self.make_tones(plan)
                whole = self.d / f"whole-{mode}.wav"
                _, calls = self.narrate_whole(whole, mode, 7, engine="chatterbox", voice="me.wav")
                self.assertEqual(calls[0]["texts"], [s["text"] for s in plan if s["kind"] == "text"])
                clips = self.d / f"clips-{mode}"
                clips.mkdir()
                for seg in plan:
                    if seg["kind"] == "text":
                        shutil.copyfile(self.tones[seg["text"]], clips / N.clip_name(seg["index"]))
                parts = self.d / f"parts-{mode}.wav"
                N.narrate_from_clips(self.script, clips, parts, engine="chatterbox", seed=7, pause_mode=mode,
                                     phonics=str(self.phonics), verbose=False)
                self.assert_same(whole, parts)
                r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(parts), "-af", "volumedetect", "-f", "null", "-"],
                                   capture_output=True, text=True)
                self.assertIn("max_volume: -4.5 dB", r.stderr)


class ScriptSegments(unittest.TestCase):
    def test_shape_indices_and_trimmed_pauses(self):
        plan = N.script_segments("\n[pause: long]\nOne.\n\nTwo.\n[pause: xlong]\n\nThree.\n\n", seed=3)
        self.assertEqual([s["kind"] for s in plan], ["text", "pause", "text", "pause", "text"])
        self.assertEqual([s["index"] for s in plan if s["kind"] == "text"], [0, 1, 2])
        self.assertEqual([s["text"] for s in plan if s["kind"] == "text"], ["One.", "Two.", "Three."])
        self.assertTrue(all(set(s) == {"kind", "seconds"} for s in plan if s["kind"] == "pause"))
        self.assertGreaterEqual(plan[3]["seconds"], 1.5)  # xlong wins over the blank line's medium

    def test_same_seed_same_plan_and_phonics_applied(self):
        d = Path(tempfile.mkdtemp())
        ph = d / "ph.json"
        ph.write_text(json.dumps(PHONICS))
        a = N.script_segments(SCRIPT, phonics=str(ph), pause_mode="explicit", seed=5)
        self.assertEqual(a, N.script_segments(SCRIPT, phonics=ph, pause_mode="explicit", seed=5))
        self.assertIn("see eye see dee", a[0]["text"])
        self.assertNotEqual([s.get("seconds") for s in a],
                            [s.get("seconds") for s in N.script_segments(SCRIPT, phonics=str(ph), pause_mode="explicit", seed=6)])

    def test_bad_pause_mode(self):
        with self.assertRaisesRegex(ValueError, "pause_mode must be"):
            N.script_segments("Hi.", pause_mode="fast")


@unittest.skipUnless(HAVE_FFMPEG, "needs ffmpeg and ffprobe")
class ClipCountMismatch(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.script = self.d / "s.txt"
        self.script.write_text("One.\n\nTwo.\n\nThree.\n")
        self.clips = self.d / "clips"
        self.clips.mkdir()

    def test_missing_clip_names_counts_and_first_missing_file(self):
        for k in (0, 2):
            tone(self.clips / N.clip_name(k), 440, 0.3)
        with self.assertRaises(ValueError) as e:
            N.narrate_from_clips(self.script, self.clips, self.d / "o.wav", seed=1, verbose=False)
        msg = str(e.exception)
        self.assertIn("3 clip(s)", msg)
        self.assertIn("found 2", msg)
        self.assertIn("0001.wav", msg)
        self.assertFalse((self.d / "o.wav").exists())

    def test_extra_clip_is_an_error(self):
        for k in range(4):
            tone(self.clips / N.clip_name(k), 440, 0.3)
        with self.assertRaisesRegex(ValueError, r"3 clip\(s\).*found 4.*unexpected: 0003\.wav"):
            N.narrate_from_clips(self.script, self.clips, self.d / "o.wav", seed=1, verbose=False)

    def test_missing_folder(self):
        with self.assertRaisesRegex(ValueError, "clips folder not found"):
            N.narrate_from_clips(self.script, self.d / "nope", self.d / "o.wav", verbose=False)


@unittest.skipUnless(HAVE_FFMPEG, "needs ffmpeg and ffprobe")
class SpeakClip(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_cloned_voice_uses_seed_plus_index_and_is_not_levelled(self):
        calls = []

        def fake_synthesize(texts, reference, out_paths, jobs=None, seed=None, verbose=True):
            calls.append((list(texts), reference, jobs, seed))
            tone(Path(out_paths[0]), 330, 0.5)
            return [0.5]

        with mock.patch("sonic_forge.clone.synthesize", side_effect=fake_synthesize), \
                mock.patch("sonic_forge.clone.peak_normalize") as level:
            out = N.speak_clip("  Hello there.\n", self.d / "sub" / "0003.wav", engine="chatterbox",
                               voice="me.wav", seed=7, index=3)
            N.speak_clip("Unseeded.", self.d / "0000.wav", engine="chatterbox", voice="me.wav")
        self.assertEqual(calls, [(["Hello there."], "me.wav", 1, 10), (["Unseeded."], "me.wav", 1, None)])
        level.assert_not_called()
        self.assertEqual(wav_format(out), (1, 2, 24000))
        # A sine tone peaks near 0 dB; not levelled down to -4.5.
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(out), "-af", "volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True)
        self.assertNotIn("max_volume: -4.5 dB", r.stderr)

    def test_other_engines_go_through_the_paragraph_path_with_resolved_voice(self):
        seen = []

        def fake_tts(text, out_path, engine, voice, lang):
            seen.append((text, engine, voice, lang))
            tone(Path(out_path), 500, 0.3, rate=44100)

        ph = self.d / "ph.json"
        ph.write_text(json.dumps(PHONICS))
        with mock.patch.object(N, "_tts_paragraph", side_effect=fake_tts):
            out = N.speak_clip("NASA calling.", self.d / "c.wav", voice="onyx", phonics=str(ph), sample_rate=16000)
        self.assertEqual(seen, [("nassa calling.", "kokoro", "am_onyx", None)])
        self.assertEqual(wav_format(out), (1, 2, 16000))

    def test_empty_text_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            N.speak_clip(" \n", self.d / "c.wav", engine="say")


class CloneModelStaysWarm(unittest.TestCase):
    def test_one_process_loads_the_model_once_per_reference(self):
        d = Path(tempfile.mkdtemp())
        ref = d / "me.wav"
        ref.write_bytes(b"RIFF")
        loads = []

        def fake_init(reference, threads, which="torch"):
            loads.append(reference)
            clone._model = object()
            clone._loaded = (reference, which, threads)

        saved = (clone._model, clone._loaded, clone._backend)
        try:
            with mock.patch.object(clone, "backend", return_value="torch"), \
                    mock.patch.object(clone, "_require"), \
                    mock.patch.object(clone, "_init_worker", side_effect=fake_init), \
                    mock.patch.object(clone, "_speak", side_effect=lambda job: (job[0], 1.0, 0.1)):
                clone._model = clone._loaded = None
                for i in range(3):
                    clone.synthesize([f"line {i}"], ref, [d / f"{i}.wav"], jobs=1, seed=i, verbose=False)
                other = d / "you.wav"
                other.write_bytes(b"RIFF")
                clone.synthesize(["x"], other, [d / "x.wav"], jobs=1, verbose=False)
        finally:
            clone._model, clone._loaded, clone._backend = saved
        self.assertEqual(loads, [str(ref.resolve()), str(other.resolve())])


@unittest.skipUnless(HAVE_FFMPEG, "needs ffmpeg and ffprobe")
class AssemblyLoadsNoModel(unittest.TestCase):
    def test_from_clips_imports_no_tts_engine(self):
        d = Path(tempfile.mkdtemp())
        (d / "s.txt").write_text("One.\n\nTwo.\n")
        (d / "clips").mkdir()
        for k in range(2):
            tone(d / "clips" / N.clip_name(k), 440 + k, 0.3)
        code = (
            "import sys; sys.path.insert(0, %r)\n"
            "from sonic_forge.narrate import narrate_from_clips\n"
            "narrate_from_clips(%r, %r, %r, engine='chatterbox', seed=1, verbose=False)\n"
            "heavy = [m for m in ('torch', 'torchaudio', 'kokoro_onnx', 'onnxruntime', 'mlx', 'mlx_audio',"
            " 'chatterbox', 'numpy', 'soundfile') if m in sys.modules]\n"
            "print(heavy)\n" % (str(SRC), str(d / "s.txt"), str(d / "clips"), str(d / "o.wav")))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "[]")
        self.assertTrue((d / "o.timing.json").exists())


@unittest.skipUnless(HAVE_FFMPEG, "needs ffmpeg and ffprobe")
class Cli(unittest.TestCase):
    def setUp(self):
        from typer.testing import CliRunner

        from sonic_forge.cli import app
        self.app = app
        self.runner = CliRunner()
        self.d = Path(tempfile.mkdtemp())
        self.script = self.d / "s.txt"
        self.script.write_text(SCRIPT)
        self.phonics = self.d / "ph.json"
        self.phonics.write_text(json.dumps(PHONICS))

    def invoke(self, *args, input=None):
        with mock.patch.dict(os.environ, {"SONIC_FORGE_NO_SKILLS": "1"}):
            return self.runner.invoke(self.app, [str(a) for a in args], input=input)

    def test_segments_prints_the_plan_without_an_output(self):
        r = self.invoke("narrate", self.script, "--segments", "--seed", "7", "--pause-mode", "explicit",
                        "--phonics", self.phonics)
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(json.loads(r.stdout),
                         N.script_segments(SCRIPT, phonics=str(self.phonics), pause_mode="explicit", seed=7))

    def test_segments_from_stdin(self):
        r = self.invoke("narrate", "-", "--segments", "--seed", "1", input="A.\n\nB.\n")
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual([s.get("text") for s in json.loads(r.stdout)], ["A.", None, "B."])

    def test_output_is_required_without_segments(self):
        r = self.invoke("narrate", self.script)
        self.assertEqual(r.exit_code, 2)
        self.assertIn("OUTPUT", r.output)

    def test_clip_then_from_clips_end_to_end(self):
        def fake_tts(text, out_path, engine, voice, lang):
            tone(Path(out_path), 200 + len(text) * 7, 0.2 + len(text) / 100, rate=44100)

        plan = json.loads(self.invoke("narrate", self.script, "--segments", "--seed", "9",
                                      "--phonics", self.phonics).stdout)
        clips = self.d / "clips"
        with mock.patch.object(N, "_tts_paragraph", side_effect=fake_tts):
            for seg in plan:
                if seg["kind"] == "text":
                    # Text from --segments already has phonics applied, so no --phonics here.
                    r = self.invoke("clip", "-", clips / N.clip_name(seg["index"]), "--engine", "say",
                                    "--seed", "9", "--index", seg["index"], input=seg["text"])
                    self.assertEqual(r.exit_code, 0, r.output)
            whole = self.d / "whole.wav"
            r = self.invoke("narrate", self.script, whole, "--engine", "say", "--seed", "9", "--phonics", self.phonics)
            self.assertEqual(r.exit_code, 0, r.output)
        parts = self.d / "parts.wav"
        r = self.invoke("narrate", self.script, parts, "--from-clips", clips, "--engine", "say", "--seed", "9",
                        "--pause-mode", "legacy", "--phonics", self.phonics, "--fps", "30")
        self.assertEqual(r.exit_code, 0, r.output)
        self.assertEqual(whole.read_bytes(), parts.read_bytes())
        self.assertEqual(whole.with_suffix(".timing.json").read_bytes(), parts.with_suffix(".timing.json").read_bytes())

    def test_from_clips_mismatch_is_a_clean_error(self):
        (self.d / "clips").mkdir()
        r = self.invoke("narrate", self.script, self.d / "o.wav", "--from-clips", self.d / "clips")
        self.assertEqual(r.exit_code, 1)
        self.assertIn("found 0", r.output)
        self.assertIsNone(r.exception if not isinstance(r.exception, SystemExit) else None)


@unittest.skipUnless(os.environ.get("SONIC_FORGE_SLOW") == "1" and HAVE_FFMPEG, "set SONIC_FORGE_SLOW=1 to run real voices")
class RealVoices(unittest.TestCase):
    """Kokoro, and a cloned voice on this machine's backend: per-paragraph clips == one narrate."""

    def check(self, engine, voice, seed):
        d = Path(tempfile.mkdtemp())
        script = d / "s.txt"
        script.write_text("Hello there, this is the first paragraph.\n\n[pause: long]\n\nAnd this is the second one.\n")
        N.narrate(script, d / "whole.wav", engine=engine, voice=voice, seed=seed, pause_mode="explicit",
                  jobs=1, verbose=False)
        for seg in N.script_segments(script.read_text(), pause_mode="explicit", seed=seed):
            if seg["kind"] == "text":
                N.speak_clip(seg["text"], d / "clips" / N.clip_name(seg["index"]), engine=engine, voice=voice,
                             seed=seed, index=seg["index"])
        N.narrate_from_clips(script, d / "clips", d / "parts.wav", engine=engine, seed=seed,
                             pause_mode="explicit", verbose=False)
        self.assertEqual((d / "whole.wav").read_bytes(), (d / "parts.wav").read_bytes())
        self.assertEqual((d / "whole.timing.json").read_text(), (d / "parts.timing.json").read_text())

    def test_kokoro(self):
        self.check("kokoro", "am_fenrir", 608)

    def test_cloned_voice(self):
        d = Path(tempfile.mkdtemp())
        sample = os.environ.get("SONIC_FORGE_SAMPLE")
        if not sample:
            sample = str(d / "sample.aiff")
            subprocess.run(["say", "-o", sample, "This is a short sample of my speaking voice, recorded so the "
                            "narrator can learn how I sound when I tell a story."], check=True)
        clone.prep_reference(sample, d / "me.wav")
        self.check("chatterbox", str(d / "me.wav"), 7)


if __name__ == "__main__":
    unittest.main()
