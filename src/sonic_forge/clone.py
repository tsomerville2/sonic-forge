"""Voice cloning — any text, spoken in the voice of a short sample.

Engine: Chatterbox Turbo (Resemble AI, MIT licence), run locally in one of two backends:
    mlx    Apple silicon GPU via mlx-audio (mlx-community/chatterbox-turbo-fp16). Picked
           automatically on macOS arm64 when the clone-mlx extra is installed.
    torch  the reference PyTorch build on CPU (or MPS). Everywhere else, e.g. Linux workers.
SONIC_FORGE_CLONE_BACKEND=mlx|torch forces one. Both take the same reference, chunk the same
way, honour the same seed (within a backend) and put Resemble's imperceptible Perth watermark
on every clip, so cloned speech stays identifiable.

Measured (2026-10-02, Turbo):
    torch, Apple M2 Max, 8 threads, one process   ~3.4 s of compute per second of speech
    torch, fly performance-16x, 16 threads         ~1.5 s per second
    torch, fly performance-16x, 4 processes x 4    ~0.67 s per second (17 s of speech in 11.5 s)
    mlx,   Apple M2 Max GPU, one process           see README (about 0.4-0.7 s per second)
Generation is autoregressive, so threads stop helping early; on CPU several processes, each with
its own copy of the model, are what scale. On the GPU one process is the default: processes
share the one GPU.

Usage:
    from sonic_forge.clone import prep_reference, synthesize
    prep_reference("raw-sample.m4a", "me.wav")              # clean 24 kHz mono reference
    synthesize(["Hello there.", "Second line."], "me.wav", ["a.wav", "b.wav"], seed=7)

Needs the `clone` extra: pip install "sonic-forge[clone]" (torch), or on Apple silicon
"sonic-forge[clone-mlx]" (GPU). On Linux, install the CPU build of torch first so pip doesn't
pull CUDA wheels:
    pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import platform
import re
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Optional

REFERENCE_RATE = 24000
MIN_REFERENCE_SECONDS = 5.0
MAX_REFERENCE_SECONDS = 20.0
# Turbo stays steady up to a few sentences; longer paragraphs are spoken a sentence group at a time.
MAX_CHARS_PER_CALL = 300

MLX_MODEL = "mlx-community/chatterbox-turbo-fp16"

_model = None  # one per worker process
_backend = None  # the backend that process loaded
_watermarker = None  # mlx backend: Resemble's Perth, applied to each clip as torch's Chatterbox does


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


def peak_normalize(path, target_db: float = -4.5, sample_rate: int = REFERENCE_RATE) -> float:
    """Apply one linear gain so the loudest sample sits at `target_db` dBFS. Returns the gain in dB."""
    path = Path(path)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr)
    if not m:
        return 0.0
    gain = target_db - float(m.group(1))
    tmp = path.with_suffix(".norm.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-af", f"volume={gain:.2f}dB",
                    "-ar", str(sample_rate), "-ac", "1", "-acodec", "pcm_s16le", str(tmp)], check=True)
    tmp.replace(path)
    return gain


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


def _apple_silicon() -> bool:
    return sys.platform == "darwin" and platform.machine() == "arm64"


def backend() -> str:
    """Which Chatterbox runs here: "mlx" (Apple GPU) or "torch" (CPU).

    SONIC_FORGE_CLONE_BACKEND=mlx|torch decides; otherwise mlx on Apple silicon when mlx-audio
    is installed (the clone-mlx extra), torch everywhere else.
    """
    forced = os.environ.get("SONIC_FORGE_CLONE_BACKEND", "").strip().lower()
    if forced in ("mlx", "torch"):
        return forced
    if forced:
        raise ValueError(f"SONIC_FORGE_CLONE_BACKEND must be mlx or torch, not {forced!r}")
    if _apple_silicon() and importlib.util.find_spec("mlx_audio") is not None:
        return "mlx"
    return "torch"


def _require(which: str) -> None:
    if which == "mlx":
        if importlib.util.find_spec("mlx_audio") is None:
            raise RuntimeError('the mlx clone backend needs the clone-mlx extra (Apple silicon): '
                               'pip install "sonic-forge[clone-mlx]"')
        return
    if importlib.util.find_spec("chatterbox") is None:
        raise RuntimeError('voice cloning needs the clone extra: pip install "sonic-forge[clone]"'
                           + (' (or "sonic-forge[clone-mlx]" for the GPU)' if _apple_silicon() else ""))


_init_error: Optional[str] = None  # a pool worker that couldn't load the model says why on its first job


def _init_pool_worker(reference: str, threads: int, which: str) -> None:
    """Pool initializer. An exception here would make multiprocessing respawn the worker forever
    (the run hangs with no output), so the error is kept and raised by the first job instead."""
    global _init_error
    try:
        _init_worker(reference, threads, which)
    except BaseException as e:  # noqa: BLE001 - reported by _speak in the parent
        _init_error = f"{type(e).__name__}: {e}"


def _init_worker(reference: str, threads: int, which: str = "torch") -> None:
    global _model, _backend, _watermarker
    _backend = which
    if which == "mlx":
        os.environ.setdefault("TQDM_DISABLE", "1")  # mlx-audio draws a progress bar per sentence
        import logging

        from mlx_audio.tts.utils import load_model

        logging.getLogger("mlx_audio").setLevel(logging.ERROR)
        _model = load_model(os.environ.get("SONIC_FORGE_MLX_CLONE_MODEL", MLX_MODEL))
        _model.prepare_conditionals(reference)
        _watermarker = _perth()
        return
    import torch
    from chatterbox.tts_turbo import ChatterboxTurboTTS

    _float32_reference()
    torch.set_num_threads(threads)
    _model = ChatterboxTurboTTS.from_pretrained(device=_device())
    _model.prepare_conditionals(reference, exaggeration=0.0)


def _float32_reference() -> None:
    """chatterbox-tts 0.1.7 levels the reference with `wav * gain`, where gain is a numpy float64;
    under numpy 2's promotion rules that turns the float32 audio into float64, and torch later
    refuses it ("expected m1 and m2 to have the same dtype"). Keep the reference float32."""
    import numpy as np
    from chatterbox.tts_turbo import ChatterboxTurboTTS

    original = ChatterboxTurboTTS.norm_loudness
    if getattr(original, "_sonic_forge_f32", False):
        return

    def norm_loudness(self, wav, sr, *args, **kwargs):
        return np.asarray(original(self, wav, sr, *args, **kwargs), dtype=np.float32)

    norm_loudness._sonic_forge_f32 = True
    ChatterboxTurboTTS.norm_loudness = norm_loudness


def _perth():
    """Resemble's Perth watermarker (CPU, ~3% of the time), or None with a warning when missing."""
    try:
        import perth

        if perth.PerthImplicitWatermarker is None:
            raise ImportError("PerthImplicitWatermarker unavailable (needs torch, torchaudio, setuptools<81)")
        return perth.PerthImplicitWatermarker()
    except ImportError as e:
        print(f"  clone: warning, no Perth watermark on this clip ({e})", file=sys.stderr, flush=True)
        return None


def write_wav(path, samples, sample_rate: int) -> None:
    """Mono float samples (-1..1) to a 16-bit PCM WAV, with no audio library needed."""
    import numpy as np

    pcm = (np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())


def _speak_mlx(index: int, text: str, out: str, seed: Optional[int]) -> tuple[int, float]:
    import mlx.core as mx
    import numpy as np

    if seed is not None:
        mx.random.seed(seed + index)
    parts = []
    # mlx-audio prints a line per chunk ("S3 Token -> Mel Inference..."); keep stdout for ours.
    with contextlib.redirect_stdout(io.StringIO()):
        for chunk in _chunks(text):
            # Our chunks are already sentence groups under the limit; don't let mlx-audio re-split.
            parts.extend(np.array(r.audio, dtype=np.float32) for r in _model.generate(text=chunk, split_pattern=None))
    wav = np.concatenate(parts) if parts else np.zeros(1, dtype=np.float32)
    sr = _model.sample_rate
    if _watermarker is not None:
        wav = np.asarray(_watermarker.apply_watermark(wav, sample_rate=sr), dtype=np.float32)
    write_wav(out, wav, sr)
    return index, len(wav) / sr


def _speak(job: tuple[int, str, str, Optional[int]]) -> tuple[int, float, float]:
    """Speak one line. Returns (index, seconds of speech, seconds it took)."""
    if _init_error:
        raise RuntimeError(f"the cloning model failed to load: {_init_error}")
    started = time.monotonic()
    index, seconds = _speak_line(job)
    return index, seconds, time.monotonic() - started


def _speak_line(job: tuple[int, str, str, Optional[int]]) -> tuple[int, float]:
    index, text, out, seed = job
    if _backend == "mlx":
        return _speak_mlx(index, text, out, seed)
    import torch
    import torchaudio

    if seed is not None:
        torch.manual_seed(seed + index)
    parts = [_model.generate(chunk) for chunk in _chunks(text)]
    wav = torch.cat(parts, dim=-1)
    torchaudio.save(out, wav, _model.sr)
    return index, wav.shape[-1] / _model.sr


def default_jobs(count: int, which: Optional[str] = None) -> int:
    """CPU: one process per four cores, at most four (each holds ~2.5 GB), never more than the work.
    GPU (mlx): one; processes would only queue for the same GPU."""
    if (which or backend()) == "mlx":
        return 1
    return max(1, min(count, (os.cpu_count() or 4) // 4, 4))


def synthesize(texts: list[str], reference, out_paths: list, jobs: Optional[int] = None,
               seed: Optional[int] = None, verbose: bool = True) -> list[float]:
    """Speak each text in the reference voice, writing one WAV per text. Returns durations.

    `jobs` processes run side by side, each loading the model once and splitting the cores
    between them. With a seed the same inputs give the same audio (on the same backend).
    """
    if len(texts) != len(out_paths):
        raise ValueError("texts and out_paths differ in length")
    reference = str(Path(reference).resolve())
    if not Path(reference).is_file():
        raise ValueError(f"reference voice not found: {reference}")
    which = backend()
    _require(which)

    work = [(i, t, str(Path(p).resolve()), seed) for i, (t, p) in enumerate(zip(texts, out_paths))]
    jobs = max(1, min(jobs or default_jobs(len(work), which), len(work) or 1))
    threads = max(1, (os.cpu_count() or 4) // jobs)
    durations = [0.0] * len(work)
    if verbose:
        print(f"  clone: Chatterbox Turbo on {'the GPU (mlx)' if which == 'mlx' else 'CPU (torch)'}, "
              f"{len(work)} line(s), {jobs} process(es)", flush=True)
    if jobs == 1:
        started = time.monotonic()
        _init_worker(reference, threads, which)
        if verbose:
            print(f"  clone: model ready in {time.monotonic() - started:.1f}s", flush=True)
        for index, seconds, took in map(_speak, work):
            durations[index] = seconds
            if verbose:
                print(f"  clone: line {index + 1}/{len(work)} {seconds:.2f}s of speech in {took:.1f}s", flush=True)
        return durations

    import multiprocessing as mp

    # spawn, not fork: torch's thread pools don't survive a fork.
    with mp.get_context("spawn").Pool(jobs, initializer=_init_pool_worker, initargs=(reference, threads, which)) as pool:
        for index, seconds, took in pool.imap_unordered(_speak, work):
            durations[index] = seconds
            if verbose:
                print(f"  clone: line {index + 1}/{len(work)} {seconds:.2f}s of speech in {took:.1f}s", flush=True)
    return durations
