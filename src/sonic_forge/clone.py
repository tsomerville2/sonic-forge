"""Voice cloning — any text, spoken in the voice of a short sample.

Engine: Chatterbox Turbo (Resemble AI, MIT licence), run locally on CPU or Apple MPS. Every clip
it makes carries Resemble's imperceptible Perth watermark, so cloned speech stays identifiable.

Measured (2026-10-02, Turbo, CPU):
    Apple M-series, 8 threads, one process     ~3.4 s of compute per second of speech
    fly performance-16x, 16 threads, one process  ~1.5 s per second
    fly performance-16x, 4 processes x 4 threads  ~0.67 s per second (17 s of speech in 11.5 s)
Generation is autoregressive, so threads stop helping early; several processes, each with its
own copy of the model, are what scale. `synthesize` therefore runs one process per job.

Usage:
    from sonic_forge.clone import prep_reference, synthesize
    prep_reference("raw-sample.m4a", "me.wav")              # clean 24 kHz mono reference
    synthesize(["Hello there.", "Second line."], "me.wav", ["a.wav", "b.wav"], seed=7)

Needs the `clone` extra: pip install "sonic-forge[clone]". On Linux, install the CPU build of
torch first so pip doesn't pull CUDA wheels:
    pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

REFERENCE_RATE = 24000
MIN_REFERENCE_SECONDS = 5.0
MAX_REFERENCE_SECONDS = 20.0
# Turbo stays steady up to a few sentences; longer paragraphs are spoken a sentence group at a time.
MAX_CHARS_PER_CALL = 300

_model = None  # one per worker process


def _probe(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip() or 0)


def prep_reference(src, dst, max_seconds: float = MAX_REFERENCE_SECONDS) -> float:
    """Turn a raw recording (any format ffmpeg reads) into a clean cloning reference.

    Mono 24 kHz, leading and trailing silence removed, loudness normalised to -18 LUFS, and cut
    to at most `max_seconds` (more reference stops improving the clone and slows every call).
    Returns the reference length in seconds; raises ValueError when under 5 s of sound remain.
    """
    src, dst = Path(src), Path(dst)
    trim = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1"
    filters = f"{trim},areverse,{trim},areverse,loudnorm=I=-18:TP=-2:LRA=11"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", filters,
                    "-t", f"{max_seconds}", "-ar", str(REFERENCE_RATE), "-ac", "1",
                    "-acodec", "pcm_s16le", str(dst)], check=True)
    seconds = _probe(dst)
    if seconds < MIN_REFERENCE_SECONDS:
        dst.unlink(missing_ok=True)
        raise ValueError(f"only {seconds:.1f}s of sound in the sample; a clone needs at least "
                         f"{MIN_REFERENCE_SECONDS:.0f}s of clear speech (10-20s is best)")
    return seconds


def _chunks(text: str) -> list[str]:
    """Split a long paragraph at sentence ends into calls of at most MAX_CHARS_PER_CALL."""
    text = " ".join(text.split())
    if len(text) <= MAX_CHARS_PER_CALL:
        return [text]
    out, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if cur and len(cur) + 1 + len(sentence) > MAX_CHARS_PER_CALL:
            out.append(cur)
            cur = sentence
        else:
            cur = f"{cur} {sentence}".strip()
    if cur:
        out.append(cur)
    return out


def _device() -> str:
    return os.environ.get("SONIC_FORGE_DEVICE", "cpu")


def _init_worker(reference: str, threads: int) -> None:
    global _model
    import torch
    from chatterbox.tts_turbo import ChatterboxTurboTTS

    torch.set_num_threads(threads)
    _model = ChatterboxTurboTTS.from_pretrained(device=_device())
    _model.prepare_conditionals(reference, exaggeration=0.0)


def _speak(job: tuple[int, str, str, Optional[int]]) -> tuple[int, float]:
    import torch
    import torchaudio

    index, text, out, seed = job
    if seed is not None:
        torch.manual_seed(seed + index)
    parts = [_model.generate(chunk) for chunk in _chunks(text)]
    wav = torch.cat(parts, dim=-1)
    torchaudio.save(out, wav, _model.sr)
    return index, wav.shape[-1] / _model.sr


def default_jobs(count: int) -> int:
    """One process per four cores, at most four (each holds ~2.5 GB) and never more than the work."""
    return max(1, min(count, (os.cpu_count() or 4) // 4, 4))


def synthesize(texts: list[str], reference, out_paths: list, jobs: Optional[int] = None,
               seed: Optional[int] = None, verbose: bool = True) -> list[float]:
    """Speak each text in the reference voice, writing one WAV per text. Returns durations.

    `jobs` processes run side by side, each loading the model once and splitting the cores
    between them. With a seed the same inputs give the same audio.
    """
    if len(texts) != len(out_paths):
        raise ValueError("texts and out_paths differ in length")
    reference = str(Path(reference).resolve())
    if not Path(reference).is_file():
        raise ValueError(f"reference voice not found: {reference}")
    try:
        import chatterbox  # noqa: F401
    except ImportError as e:
        raise RuntimeError('voice cloning needs the clone extra: pip install "sonic-forge[clone]"') from e

    work = [(i, t, str(Path(p).resolve()), seed) for i, (t, p) in enumerate(zip(texts, out_paths))]
    jobs = jobs or default_jobs(len(work))
    threads = max(1, (os.cpu_count() or 4) // jobs)
    durations = [0.0] * len(work)
    if jobs == 1:
        _init_worker(reference, threads)
        results = map(_speak, work)
        for index, seconds in results:
            durations[index] = seconds
            if verbose:
                print(f"  clone: line {index + 1}/{len(work)} {seconds:.2f}s", flush=True)
        return durations

    import multiprocessing as mp

    # spawn, not fork: torch's thread pools don't survive a fork.
    with mp.get_context("spawn").Pool(jobs, initializer=_init_worker, initargs=(reference, threads)) as pool:
        for index, seconds in pool.imap_unordered(_speak, work):
            durations[index] = seconds
            if verbose:
                print(f"  clone: line {index + 1}/{len(work)} {seconds:.2f}s", flush=True)
    return durations
