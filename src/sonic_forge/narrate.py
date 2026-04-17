"""Narrate — long-form paragraph-chunked TTS with silence management and timing manifest.

Design:
- Paragraph chunks fed to the chosen TTS engine with plain punctuation
  (no stacked dots — that's the kokoro_prep aesthetic, which produces
  vocal filler artifacts like "ehhh/mmmm" for long-form narration)
- ffmpeg-generated silence files interleaved between paragraphs
- Pause pools with randomized selection for natural variation
- Emits `<output>.timing.json` — per-segment start/end times so downstream
  tools (Remotion, DaVinci, etc.) can align visuals to actual audio boundaries

Segment markup:
    Paragraphs separated by blank lines. Default gap = [pause: medium].
    Override with [pause: short], [pause: long], [pause: xlong],
    [pause: tiny], or [pause: 1.2] for jittered numeric.

Usage:
    from sonic_forge.narrate import narrate
    narrate("input.txt", "output.wav", voice="am_fenrir", seed=608)
"""

from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator, Optional


DEFAULT_SAMPLE_RATE = 24000
DEFAULT_PAUSE_LABEL = "medium"
DEFAULT_FPS = 30

PAUSE_POOLS: dict[str, list[float]] = {
    "tiny":   [0.15, 0.18, 0.22, 0.25, 0.28, 0.31, 0.33, 0.36, 0.38, 0.40],
    "short":  [0.30, 0.35, 0.40, 0.44, 0.48, 0.52, 0.56, 0.60, 0.64, 0.68],
    "medium": [0.55, 0.62, 0.68, 0.74, 0.80, 0.85, 0.90, 0.95, 1.02, 1.10],
    "long":   [0.95, 1.05, 1.12, 1.18, 1.25, 1.32, 1.40, 1.48, 1.54, 1.60],
    "xlong":  [1.50, 1.60, 1.70, 1.80, 1.90, 2.00, 2.08, 2.15, 2.25, 2.35],
}


def pick_pause(label_or_value, rng: random.Random) -> float:
    """Resolve a pause spec into a concrete duration.

    - Labels (tiny/short/medium/long/xlong) → pick from the pool.
    - Numeric values → apply ±15% jitter, floor at 0.1s.
    - Unknown labels → fall back to the default pool.
    """
    s = str(label_or_value).strip().lower()
    if s in PAUSE_POOLS:
        return rng.choice(PAUSE_POOLS[s])
    try:
        v = float(s)
    except ValueError:
        return rng.choice(PAUSE_POOLS[DEFAULT_PAUSE_LABEL])
    return max(0.1, v * (1.0 + rng.uniform(-0.15, 0.15)))


def phonics_apply(text: str, phonics_path: Optional[Path]) -> str:
    """Apply word-boundary regex replacements from a JSON dict.

    Longer keys are applied first so "CI/CD" wins over "CI".
    Optional — returns text unchanged if phonics_path is None or missing.
    """
    if not phonics_path:
        return text
    p = Path(phonics_path)
    if not p.exists():
        return text
    with p.open() as f:
        d = json.load(f)
    for k in sorted(d.keys(), key=len, reverse=True):
        pat = r'(?<![a-zA-Z])' + re.escape(k) + r'(?![a-zA-Z])'
        text = re.sub(pat, d[k], text)
    return text


def split_script(text: str, rng: random.Random) -> Iterator[tuple[str, object]]:
    """Parse input text into ("text", paragraph) and ("pause", seconds) tuples.

    - `[pause: label]` on its own line → explicit pause.
    - Blank lines between paragraphs → default medium pause.
    - Consecutive non-blank lines are joined into one paragraph.
    """
    lines = text.split("\n")
    buffer: list[str] = []

    def flush():
        chunk = "\n".join(buffer).strip()
        buffer.clear()
        if chunk:
            yield ("text", chunk)

    for line in lines:
        m = re.match(r'^\s*\[pause:\s*([^\]]+)\s*\]\s*$', line)
        if m:
            yield from flush()
            yield ("pause", pick_pause(m.group(1), rng))
        elif line.strip() == "":
            yield from flush()
            yield ("pause", pick_pause(DEFAULT_PAUSE_LABEL, rng))
        else:
            buffer.append(line)
    yield from flush()


def probe_duration(wav: Path) -> float:
    """ffprobe → duration in seconds."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(wav)],
        capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def make_silence(duration: float, out_path: Path,
                 sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    """ffmpeg anullsrc → pcm_s16le mono silence at the given sample rate."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"anullsrc=r={sample_rate}:cl=mono",
         "-t", f"{duration}", "-acodec", "pcm_s16le", str(out_path)],
        check=True, capture_output=True)


def reencode(src: Path, dst: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    """Normalize any WAV to the target sample rate, mono, pcm_s16le."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src),
         "-ar", str(sample_rate), "-ac", "1", "-acodec", "pcm_s16le", str(dst)],
        check=True, capture_output=True)


def concat_wavs(files: list, out_path: Path,
                sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    """ffmpeg concat demuxer → single WAV, re-encoded for safety."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in files:
            f.write(f"file '{os.path.abspath(p)}'\n")
        list_path = f.name
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
             "-ar", str(sample_rate), "-ac", "1", "-acodec", "pcm_s16le",
             str(out_path)],
            check=True, capture_output=True)
    finally:
        os.unlink(list_path)


def _tts_paragraph(text: str, out_path: Path,
                   engine: Optional[str], voice: Optional[str],
                   lang: Optional[str]) -> None:
    """Generate TTS for one paragraph via the shared sonic-forge engine layer."""
    from sonic_forge.tts import generate_to_wav
    generate_to_wav(text, str(out_path),
                    engine=engine, voice=voice, lang=lang)


def _resolve_engine_voice(engine: Optional[str], voice: Optional[str],
                          lang: Optional[str]) -> tuple[str, str]:
    """Resolve into final (engine, voice) — same logic that `speak` uses.

    Also enforces the Telugu × Kokoro fail-loud rule.
    """
    from sonic_forge.tts import resolve_voice

    resolved_engine, resolved_voice = resolve_voice(
        voice=voice, engine=engine, lang=lang)

    if engine == "kokoro" and lang and lang.lower() == "telugu":
        raise RuntimeError(
            "Kokoro cannot synthesize Telugu (tokenizer IndexError). "
            "Use --engine edge or drop --engine to auto-pick."
        )

    return resolved_engine, resolved_voice


def narrate(input_path, output_path,
            voice: Optional[str] = None,
            engine: Optional[str] = None,
            lang: Optional[str] = None,
            phonics: Optional[str] = None,
            seed: Optional[int] = None,
            fps: int = DEFAULT_FPS,
            sample_rate: int = DEFAULT_SAMPLE_RATE,
            write_manifest: bool = True,
            verbose: bool = True) -> Path:
    """Produce a narration WAV + (optional) timing manifest JSON.

    Args:
        input_path: Path to text file, or "-" for stdin.
        output_path: Target WAV path. Manifest written at `<output>.timing.json`
                     unless write_manifest is False.
        voice: Voice short name or full ID (e.g. "am_fenrir", "af_heart").
        engine: "say", "kokoro", or "edge". Auto-detected if None.
        lang: Language name; auto-picks engine + voice. Overrides voice defaults.
        phonics: Path to JSON dict of word→pronunciation replacements.
        seed: Seed pause-pool randomness for reproducibility.
        fps: Frame rate assumed for manifest `total_frames`.
        sample_rate: Output sample rate (Hz).
        write_manifest: Skip the timing JSON if False.
        verbose: Print per-segment progress.

    Returns:
        Path to the produced WAV.
    """
    rng = random.Random(seed)
    output_path = Path(output_path)
    manifest_path = output_path.with_suffix(".timing.json")

    if str(input_path) == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(input_path).read_text()

    phonics_path = Path(phonics) if phonics else None
    phonicsed = phonics_apply(raw, phonics_path)

    resolved_engine, resolved_voice = _resolve_engine_voice(engine, voice, lang)

    tmpdir = Path(tempfile.mkdtemp(prefix="narrate_"))
    try:
        # Collapse adjacent pauses (keep max) and trim leading/trailing pauses
        collapsed: list[tuple[str, object]] = []
        for kind, val in split_script(phonicsed, rng):
            if kind == "pause" and collapsed and collapsed[-1][0] == "pause":
                collapsed[-1] = ("pause", max(collapsed[-1][1], val))
            else:
                collapsed.append((kind, val))
        while collapsed and collapsed[0][0] == "pause":
            collapsed.pop(0)
        while collapsed and collapsed[-1][0] == "pause":
            collapsed.pop()

        files: list[str] = []
        manifest: list[dict] = []
        cumulative = 0.0

        for i, (kind, val) in enumerate(collapsed):
            if kind == "text":
                raw_wav = tmpdir / f"raw_{i:03d}.wav"
                norm_wav = tmpdir / f"seg_{i:03d}.wav"
                _tts_paragraph(val, raw_wav,
                               engine=resolved_engine,
                               voice=resolved_voice,
                               lang=None)
                reencode(raw_wav, norm_wav, sample_rate=sample_rate)
                dur = probe_duration(norm_wav)
                manifest.append({
                    "kind": "text",
                    "index": len(manifest),
                    "start": round(cumulative, 3),
                    "end": round(cumulative + dur, 3),
                    "duration": round(dur, 3),
                    "text": val,
                })
                cumulative += dur
                files.append(str(norm_wav))
                if verbose:
                    head = val.replace("\n", " ")[:70]
                    print(f"  [{cumulative-dur:6.2f}–{cumulative:6.2f}s] {head!r}")
            else:
                sil = tmpdir / f"sil_{i:03d}_{val:.3f}.wav"
                make_silence(val, sil, sample_rate=sample_rate)
                manifest.append({
                    "kind": "pause",
                    "index": len(manifest),
                    "start": round(cumulative, 3),
                    "end": round(cumulative + val, 3),
                    "duration": round(val, 3),
                })
                cumulative += val
                files.append(str(sil))
                if verbose:
                    print(f"  [{cumulative-val:6.2f}–{cumulative:6.2f}s] pause {val:.2f}s")

        concat_wavs(files, output_path, sample_rate=sample_rate)
        total = probe_duration(output_path)

        if write_manifest:
            manifest_out = {
                "total_duration": round(total, 3),
                "fps": fps,
                "total_frames": int(total * fps),
                "segments": manifest,
            }
            manifest_path.write_text(json.dumps(manifest_out, indent=2))

        if verbose:
            print(f"\nFinal: {output_path} ({total:.2f}s, {int(total*fps)} frames)")
            if write_manifest:
                print(f"Timing: {manifest_path}")

        return output_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
