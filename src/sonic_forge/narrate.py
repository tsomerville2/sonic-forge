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

Worker fleets (paragraphs spoken on many machines, assembled on one, byte-identical to narrate):
    from sonic_forge.narrate import script_segments, speak_clip, narrate_from_clips
    plan = script_segments(text, seed=7, pause_mode="explicit")        # text {text,index} / pause {seconds}
    speak_clip(plan[0]["text"], "clips/0000.wav", engine="chatterbox", voice="me.wav", seed=7, index=0)
    narrate_from_clips("input.txt", "clips", "output.wav", engine="chatterbox", seed=7, pause_mode="explicit")
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


def split_script(text: str, rng: random.Random,
                 pause_mode: str = "legacy") -> Iterator[tuple[str, object]]:
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

    if pause_mode == "explicit":
        yield from _split_explicit(lines, rng)
        return

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


def _split_explicit(lines: list[str], rng: random.Random) -> Iterator[tuple[str, object]]:
    """Explicit pause mode: a [pause: …] marker REPLACES the blank-line default.

    Each gap between two paragraphs (any run of blank lines and markers) emits
    exactly one pause. If the gap holds markers, the longest marker wins and no
    default is drawn; a gap of bare blank lines gets the default medium pause.
    So `[pause: short]` really is short, and `[pause: 0.3]` really is ~0.3s.
    """
    buffer: list[str] = []
    markers: list[str] = []
    in_gap = False

    def flush():
        chunk = "\n".join(buffer).strip()
        buffer.clear()
        if chunk:
            yield ("text", chunk)

    def close_gap():
        if markers:
            yield ("pause", max(pick_pause(m, rng) for m in markers))
        else:
            yield ("pause", pick_pause(DEFAULT_PAUSE_LABEL, rng))
        markers.clear()

    for line in lines:
        m = re.match(r'^\s*\[pause:\s*([^\]]+)\s*\]\s*$', line)
        if m or line.strip() == "":
            yield from flush()
            in_gap = True
            if m:
                markers.append(m.group(1))
        else:
            if in_gap:
                yield from close_gap()
                in_gap = False
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


def _check_pause_mode(pause_mode: str) -> None:
    if pause_mode not in ("legacy", "explicit"):
        raise ValueError(f"pause_mode must be 'legacy' or 'explicit', got {pause_mode!r}")


def _read_script(input_path) -> str:
    """The script text: a file, or stdin when input_path is "-"."""
    if str(input_path) == "-":
        return sys.stdin.read()
    return Path(input_path).read_text()


def script_segments(text: str, phonics=None, pause_mode: str = "legacy",
                    seed: Optional[int] = None) -> list[dict]:
    """The exact plan `narrate` speaks: what is said, and the pauses between, in order.

    Phonics are applied to the whole text first, the text is split with
    `random.Random(seed)` (so the pause draws are the very ones narrate makes), adjacent
    pauses collapse to the longest, and leading/trailing pauses are dropped.

    Returns a list of
        {"kind": "text", "text": paragraph, "index": k}   k = 0, 1, 2 … over text segments only
        {"kind": "pause", "seconds": duration}

    A worker fleet speaks text segment k to `k:04d.wav` (see `speak_clip`) and one machine
    puts them together with `narrate_from_clips`.
    """
    _check_pause_mode(pause_mode)
    rng = random.Random(seed)
    phonicsed = phonics_apply(text, Path(phonics) if phonics else None)

    # Collapse adjacent pauses (keep max) and trim leading/trailing pauses
    collapsed: list[tuple[str, object]] = []
    for kind, val in split_script(phonicsed, rng, pause_mode):
        if kind == "pause" and collapsed and collapsed[-1][0] == "pause":
            collapsed[-1] = ("pause", max(collapsed[-1][1], val))
        else:
            collapsed.append((kind, val))
    while collapsed and collapsed[0][0] == "pause":
        collapsed.pop(0)
    while collapsed and collapsed[-1][0] == "pause":
        collapsed.pop()

    segments: list[dict] = []
    spoken = 0
    for kind, val in collapsed:
        if kind == "text":
            segments.append({"kind": "text", "text": val, "index": spoken})
            spoken += 1
        else:
            segments.append({"kind": "pause", "seconds": val})
    return segments


def clip_name(index: int) -> str:
    """File name of text segment `index` in a clips folder: 0000.wav, 0001.wav, …"""
    return f"{index:04d}.wav"


def _assemble(segments: list[dict], speech_for, output_path: Path, tmpdir: Path, *,
              level: bool, pause_mode: str, fps: int, sample_rate: int,
              write_manifest: bool, verbose: bool) -> Path:
    """Re-encode each spoken paragraph, make each silence, concatenate, level, write the manifest.

    `speech_for(i, segment)` returns the raw WAV of text segment `segment` (position `i` in the
    plan). narrate and narrate_from_clips both end here, so their output can't drift apart.
    """
    manifest_path = output_path.with_suffix(".timing.json")
    files: list[str] = []
    manifest: list[dict] = []
    cumulative = 0.0

    for i, seg in enumerate(segments):
        if seg["kind"] == "text":
            val = seg["text"]
            norm_wav = tmpdir / f"seg_{i:03d}.wav"
            reencode(speech_for(i, seg), norm_wav, sample_rate=sample_rate)
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
            val = seg["seconds"]
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
    if level:
        # Cloned speech comes out quiet (peaks near -15 dB); one linear gain to a -4.5 dB peak
        # puts it level with Kokoro without touching timing or dynamics.
        from sonic_forge.clone import peak_normalize
        peak_normalize(output_path, target_db=-4.5, sample_rate=sample_rate)
    total = probe_duration(output_path)

    if write_manifest:
        manifest_out = {
            "total_duration": round(total, 3),
            "fps": fps,
            "total_frames": int(total * fps),
            "pause_mode": pause_mode,
            "segments": manifest,
        }
        manifest_path.write_text(json.dumps(manifest_out, indent=2))

    if verbose:
        print(f"\nFinal: {output_path} ({total:.2f}s, {int(total*fps)} frames)")
        if write_manifest:
            print(f"Timing: {manifest_path}")

    return output_path


def narrate(input_path, output_path,
            voice: Optional[str] = None,
            engine: Optional[str] = None,
            lang: Optional[str] = None,
            phonics: Optional[str] = None,
            seed: Optional[int] = None,
            fps: int = DEFAULT_FPS,
            sample_rate: int = DEFAULT_SAMPLE_RATE,
            write_manifest: bool = True,
            verbose: bool = True,
            pause_mode: str = "legacy",
            jobs: Optional[int] = None) -> Path:
    """Produce a narration WAV + (optional) timing manifest JSON.

    Args:
        input_path: Path to text file, or "-" for stdin.
        output_path: Target WAV path. Manifest written at `<output>.timing.json`
                     unless write_manifest is False.
        voice: Voice short name or full ID (e.g. "am_fenrir", "af_heart").
        engine: "say", "kokoro", "edge" or "chatterbox" (a cloned voice: `voice` is the
            path of a reference recording). Auto-detected if None.
        lang: Language name; auto-picks engine + voice. Overrides voice defaults.
        phonics: Path to JSON dict of word→pronunciation replacements.
        seed: Seed pause-pool randomness for reproducibility.
        fps: Frame rate assumed for manifest `total_frames`.
        sample_rate: Output sample rate (Hz).
        write_manifest: Skip the timing JSON if False.
        verbose: Print per-segment progress.
        pause_mode: "legacy" (every blank line draws a medium pause and adjacent
            pauses collapse by max, so markers shorter than ~1.3s are swallowed;
            byte-identical to earlier releases) or "explicit" (a marker replaces
            the blank-line default for its gap).
        jobs: Cloned voices only — paragraphs spoken side by side in this many processes
            (default: one per four cores, at most four).

    Returns:
        Path to the produced WAV.
    """
    _check_pause_mode(pause_mode)
    output_path = Path(output_path)
    raw = _read_script(input_path)
    resolved_engine, resolved_voice = _resolve_engine_voice(engine, voice, lang)
    segments = script_segments(raw, phonics=phonics, pause_mode=pause_mode, seed=seed)

    tmpdir = Path(tempfile.mkdtemp(prefix="narrate_"))
    try:
        # A cloned voice is slow per call and scales with processes, so every paragraph is
        # spoken up front in parallel; assembly then only measures and joins. Text segment k
        # is spoken with seed + k, exactly as speak_clip(..., seed=seed, index=k) speaks it.
        cloned: dict[int, Path] = {}
        if resolved_engine == "chatterbox":
            from sonic_forge.clone import synthesize
            texts = [(i, seg["text"]) for i, seg in enumerate(segments) if seg["kind"] == "text"]
            cloned = {i: tmpdir / f"raw_{i:03d}.wav" for i, _ in texts}
            synthesize([t for _, t in texts], resolved_voice, [cloned[i] for i, _ in texts],
                       jobs=jobs, seed=seed, verbose=verbose)

        def speech_for(i: int, seg: dict) -> Path:
            if i in cloned:
                return cloned[i]
            raw_wav = tmpdir / f"raw_{i:03d}.wav"
            _tts_paragraph(seg["text"], raw_wav, engine=resolved_engine,
                           voice=resolved_voice, lang=None)
            return raw_wav

        return _assemble(segments, speech_for, output_path, tmpdir,
                         level=resolved_engine == "chatterbox", pause_mode=pause_mode,
                         fps=fps, sample_rate=sample_rate,
                         write_manifest=write_manifest, verbose=verbose)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def speak_clip(text, out_path, engine=None, voice=None, seed=None, index=0,
               phonics=None, sample_rate=DEFAULT_SAMPLE_RATE) -> Path:
    """Speak ONE paragraph exactly as `narrate` speaks text segment `index` of a script.

    For worker fleets: each machine speaks some paragraphs to `clip_name(index)`, and one
    machine assembles them with `narrate_from_clips`. Same engine/voice resolution as narrate;
    a cloned voice (engine="chatterbox", voice = reference WAV) is sampled with seed + index,
    the seed narrate gives that paragraph, and is NOT levelled here (narrate_from_clips levels
    the whole narration once, as narrate does). The clip is mono pcm_s16le at sample_rate.

    `phonics` is applied to `text`. Text taken from `script_segments(..., phonics=…)` already
    has it applied; pass phonics=None then. Models stay loaded between calls in one process
    (Kokoro and Chatterbox are each loaded once), so a worker can call this in a loop.
    """
    text = phonics_apply(str(text), Path(phonics) if phonics else None).strip()
    if not text:
        raise ValueError("nothing to speak: the clip text is empty")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_engine, resolved_voice = _resolve_engine_voice(engine, voice, None)

    tmpdir = Path(tempfile.mkdtemp(prefix="clip_"))
    try:
        raw_wav = tmpdir / "raw.wav"
        if resolved_engine == "chatterbox":
            from sonic_forge.clone import synthesize
            synthesize([text], resolved_voice, [raw_wav], jobs=1,
                       seed=None if seed is None else seed + index, verbose=False)
        else:
            _tts_paragraph(text, raw_wav, engine=resolved_engine,
                           voice=resolved_voice, lang=None)
        reencode(raw_wav, out_path, sample_rate=sample_rate)
        return out_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def narrate_from_clips(input_path, clips_dir, output_path,
                       engine: Optional[str] = None,
                       seed: Optional[int] = None,
                       pause_mode: str = "legacy",
                       phonics: Optional[str] = None,
                       fps: int = DEFAULT_FPS,
                       sample_rate: int = DEFAULT_SAMPLE_RATE,
                       write_manifest: bool = True,
                       verbose: bool = True) -> Path:
    """Assemble a narration from paragraphs spoken elsewhere — no TTS here, only ffmpeg.

    `clips_dir` holds 0000.wav, 0001.wav, … one per text segment of
    script_segments(script, phonics, pause_mode, seed), in order (see speak_clip). The pauses
    are the same seeded draws narrate makes, clips and silences are encoded and joined the
    same way, and engine="chatterbox" levels the result to a -4.5 dB peak as narrate does, so
    with the same clips the WAV and `<output>.timing.json` match narrate's byte for byte.

    Raises ValueError naming expected and found counts when clips are missing or extra.
    """
    _check_pause_mode(pause_mode)
    output_path = Path(output_path)
    clips_dir = Path(clips_dir)
    segments = script_segments(_read_script(input_path), phonics=phonics,
                               pause_mode=pause_mode, seed=seed)
    expected = [clip_name(s["index"]) for s in segments if s["kind"] == "text"]
    if not clips_dir.is_dir():
        raise ValueError(f"clips folder not found: {clips_dir}")
    found = sorted(p.name for p in clips_dir.iterdir()
                   if p.is_file() and re.fullmatch(r"\d+\.wav", p.name))
    missing = [n for n in expected if n not in set(found)]
    extra = [n for n in found if n not in set(expected)]
    if missing or extra:
        detail = []
        if missing:
            detail.append(f"first missing: {clips_dir / missing[0]}")
        if extra:
            detail.append(f"unexpected: {extra[0]}" + (f" (+{len(extra) - 1} more)" if len(extra) > 1 else ""))
        raise ValueError(f"the script has {len(expected)} paragraph(s), so {clips_dir} should hold "
                         f"{len(expected)} clip(s) ({expected[0] if expected else 'none'}"
                         f"{' … ' + expected[-1] if len(expected) > 1 else ''}), found {len(found)}; "
                         + "; ".join(detail))

    tmpdir = Path(tempfile.mkdtemp(prefix="narrate_clips_"))
    try:
        return _assemble(segments, lambda i, seg: clips_dir / clip_name(seg["index"]),
                         output_path, tmpdir,
                         level=engine == "chatterbox", pause_mode=pause_mode,
                         fps=fps, sample_rate=sample_rate,
                         write_manifest=write_manifest, verbose=verbose)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
