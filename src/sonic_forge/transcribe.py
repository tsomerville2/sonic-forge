"""Speech to text on this machine: NVIDIA Parakeet TDT via parakeet-mlx (Apple silicon GPU).

The result is shaped like OpenAI / Groq Whisper `verbose_json`, so a caller written for the
hosted Whisper can swap this in:

    {"task": "transcribe", "language": "english", "duration": 65.32, "text": "...",
     "segments": [{"id": 0, "start": 0.0, "end": 7.4, "text": "..."}, ...],
     "words":    [{"word": "Someone", "start": 0.0, "end": 0.56}, ...],   # with words=True
     "model": "mlx-community/parakeet-tdt-0.6b-v2"}

Measured (2026-10-02, M2 Max, parakeet-tdt-0.6b-v2, warm): 65 s of speech in ~2.8 s and 120 s in
~5.7 s (about 0.045 s per second of audio); loading the model takes ~2 s. The owner's STT
shoot-out put this model first (WER 0.149) ahead of Vosk, faster-whisper and AWS Transcribe.

Needs the `stt-mlx` extra (Apple silicon): pip install "sonic-forge[stt-mlx]", and ffmpeg.
"""

from __future__ import annotations

import contextlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

DEFAULT_MODEL = "mlx-community/parakeet-tdt-0.6b-v2"
# Long recordings are heard in overlapping windows so memory stays flat; parakeet-mlx stitches them.
CHUNK_SECONDS = 120.0
OVERLAP_SECONDS = 15.0


def model_name(model: Optional[str] = None) -> str:
    return model or os.environ.get("SONIC_FORGE_STT_MODEL") or DEFAULT_MODEL


def _duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def words_from_tokens(tokens) -> list[dict]:
    """Join Parakeet's sub-word tokens into words: a token that starts with a space starts a word.

    Punctuation stays on its word ("fix," "Thursday."), as Whisper's word lists do.
    """
    words: list[dict] = []
    for t in tokens:
        text = t.text
        if not text.strip():
            continue
        if words and not text.startswith(" "):
            words[-1]["word"] += text
            words[-1]["end"] = round(float(t.end), 3)
        else:
            words.append({"word": text.strip(), "start": round(float(t.start), 3), "end": round(float(t.end), 3)})
    return words


def shape(result, duration: float, model: str, words: bool) -> dict:
    """An AlignedResult from parakeet-mlx → Whisper verbose_json."""
    segments = []
    all_tokens = []
    for s in result.sentences:
        text = s.text.strip()
        all_tokens.extend(s.tokens)
        if text:
            segments.append({"id": len(segments), "start": round(float(s.start), 3),
                             "end": round(float(s.end), 3), "text": text})
    out = {
        "task": "transcribe",
        # parakeet-tdt v2 hears English only; the v3 models are multilingual and don't say which.
        "language": "english" if "v2" in model else None,
        "duration": round(duration or (segments[-1]["end"] if segments else 0.0), 3),
        "text": (result.text or "").strip(),
        "segments": segments,
        "model": model,
    }
    if words:
        out["words"] = words_from_tokens(all_tokens)
    return out


_loaded: dict[str, object] = {}


def transcribe(audio, words: bool = False, model: Optional[str] = None) -> dict:
    """Transcribe any file ffmpeg reads. Returns the verbose_json-shaped dict above."""
    path = Path(audio)
    if not path.is_file():
        raise ValueError(f"audio not found: {path}")
    if importlib.util.find_spec("parakeet_mlx") is None:
        raise RuntimeError('transcribe needs the stt-mlx extra (Apple silicon): pip install "sonic-forge[stt-mlx]"')
    name = model_name(model)
    os.environ.setdefault("TQDM_DISABLE", "1")
    # Libraries print download and progress chatter on stdout; keep stdout for the JSON.
    with contextlib.redirect_stdout(sys.stderr):
        if name not in _loaded:
            from parakeet_mlx import from_pretrained

            _loaded[name] = from_pretrained(name)
        result = _loaded[name].transcribe(str(path), chunk_duration=CHUNK_SECONDS, overlap_duration=OVERLAP_SECONDS)
    return shape(result, _duration(path), name, words)
