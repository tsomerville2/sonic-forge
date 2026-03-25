"""Image-based talking heads — hi-res character animation in terminal.

Two rendering modes:
  - iTerm2: real inline images (HD quality, no flicker)
  - Universal: halfblock text art (works everywhere, no flicker, 16-bit look)

Characters live in ~/.sonic-forge/characters/<name>/ with a 3x3 spritesheet.
"""

from __future__ import annotations

import array
import base64
import io
import os
import random
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Optional

from PIL import Image

from sonic_forge.spritesheet import load_character_frames

CHARACTERS_DIR = Path.home() / ".sonic-forge" / "characters"


# ---------------------------------------------------------------------------
# Terminal detection
# ---------------------------------------------------------------------------

def _is_iterm2() -> bool:
    term = os.environ.get("TERM_PROGRAM", "")
    lc = os.environ.get("LC_TERMINAL", "")
    return "iTerm" in term or "iTerm" in lc


# ---------------------------------------------------------------------------
# Halfblock renderer (universal — works in all terminals)
# ---------------------------------------------------------------------------

def _img_to_halfblocks(img: Image.Image, width_cols: int = 60) -> list[str]:
    """Convert PIL Image to truecolor halfblock text lines.

    Each text row = 2 pixel rows. Uses ▄ with bg=top, fg=bottom.
    """
    ratio = width_cols / img.width
    new_h = int(img.height * ratio)
    if new_h % 2:
        new_h += 1
    img = img.convert("RGB").resize((width_cols, new_h), Image.LANCZOS)
    px = img.load()

    lines = []
    for y in range(0, new_h, 2):
        parts = []
        for x in range(width_cols):
            r1, g1, b1 = px[x, y]
            if y + 1 < new_h:
                r2, g2, b2 = px[x, y + 1]
                parts.append(
                    f"\033[48;2;{r1};{g1};{b1}m"
                    f"\033[38;2;{r2};{g2};{b2}m▄"
                )
            else:
                parts.append(f"\033[38;2;{r1};{g1};{b1}m▀")
        parts.append("\033[0m")
        lines.append("".join(parts))
    return lines


# ---------------------------------------------------------------------------
# iTerm2 inline image
# ---------------------------------------------------------------------------

def _img_to_b64(img: Image.Image, max_width: int = 480) -> str:
    if img.width > max_width:
        r = max_width / img.width
        img = img.resize((max_width, int(img.height * r)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _iterm2_escape(b64: str, height: int = 20) -> str:
    return (
        f"\033]1337;File=inline=1;width=40;height={height}"
        f";preserveAspectRatio=1:{b64}\a"
    )


# ---------------------------------------------------------------------------
# Audio analysis (same as talking_heads.py)
# ---------------------------------------------------------------------------

def _analyze_amplitude(wav_path: str, chunk_ms: int = 33) -> list[tuple[float, float]]:
    with wave.open(wav_path, "r") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())

    if sw == 2:
        samples = array.array("h", raw)
    else:
        samples = array.array("h", [((b - 128) << 8) for b in raw])
    if nch == 2:
        mono = array.array("h")
        for i in range(0, len(samples), 2):
            mono.append((samples[i] + samples[i + 1]) // 2)
        samples = mono

    chunk_n = int(sr * chunk_ms / 1000)
    return [
        (i / sr, (sum(s * s for s in samples[i:i + chunk_n]) / max(1, len(samples[i:i + chunk_n]))) ** 0.5)
        for i in range(0, len(samples), chunk_n)
    ]


def _mouth_state(rms: float, silence: float, wide: float) -> str:
    if rms < silence:
        return "closed"
    return "wide" if rms > wide else "open"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_characters() -> list[str]:
    if not CHARACTERS_DIR.exists():
        return []
    return [
        d.name for d in CHARACTERS_DIR.iterdir()
        if d.is_dir() and (
            list(d.glob("*sprite*")) or list(d.glob("*_open.*"))
        )
    ]


def animate_image_character(
    wav_path: str,
    char_name: str,
    text: str = "",
    voice_stem: Optional[str] = None,
    width_cols: int = 60,
) -> None:
    """Play audio while animating a hi-res image character.

    Auto-detects terminal:
      iTerm2 → real inline images (HD)
      Everything else → halfblock text art (16-bit look)
    """
    # Handle MP3 → WAV conversion
    cleanup_wav = False
    analysis_wav = wav_path
    if wav_path.lower().endswith(".mp3"):
        wav_out = wav_path.rsplit(".", 1)[0] + "_tmp.wav"
        try:
            subprocess.run(
                ["afconvert", wav_path, wav_out, "-d", "LEI16", "-f", "WAVE"],
                check=True, capture_output=True,
            )
            analysis_wav = wav_out
            cleanup_wav = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  Cannot convert MP3 to WAV for animation.")
            return

    try:
        if _is_iterm2():
            _animate_iterm2(wav_path, analysis_wav, char_name, voice_stem)
        else:
            _animate_halfblock(wav_path, analysis_wav, char_name, voice_stem, width_cols)
    finally:
        if cleanup_wav and os.path.exists(analysis_wav):
            os.remove(analysis_wav)


# ---------------------------------------------------------------------------
# Halfblock animation (universal)
# ---------------------------------------------------------------------------

def _animate_halfblock(audio_path, wav_path, char_name, voice_stem, width_cols):
    char_dir = CHARACTERS_DIR / char_name
    frames = load_character_frames(str(char_dir))
    if not frames:
        print(f"  No frames for '{char_name}'")
        return

    # Pre-render all frames as text lines
    rendered = {}
    for key, img in frames.items():
        rendered[key] = _img_to_halfblocks(img, width_cols)

    n_lines = len(rendered[sorted(rendered.keys())[0]])

    # Analyze audio
    amps = _analyze_amplitude(voice_stem or wav_path)
    if not amps:
        return
    mouth_timeline, silence, wide_thresh = _build_timeline(amps)

    # Animation
    sys.stdout.write("\033[?25l")  # hide cursor
    for _ in range(n_lines):
        sys.stdout.write("\n")

    initial = ("closed", "open")
    _draw_halfblock(rendered[initial], n_lines)

    audio = subprocess.Popen(
        ["afplay", audio_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    try:
        _run_loop(audio, mouth_timeline, rendered, n_lines, _draw_halfblock)
    finally:
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()
        if audio.poll() is None:
            audio.terminate()


def _draw_halfblock(lines, n_lines):
    sys.stdout.write(f"\033[{n_lines}A")
    for ln in lines:
        sys.stdout.write(f"\033[2K{ln}\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# iTerm2 animation (HD)
# ---------------------------------------------------------------------------

def _animate_iterm2(audio_path, wav_path, char_name, voice_stem):
    char_dir = CHARACTERS_DIR / char_name
    frames = load_character_frames(str(char_dir))
    if not frames:
        print(f"  No frames for '{char_name}'")
        return

    # Pre-encode as iTerm2 escape sequences
    encoded = {}
    for key, img in frames.items():
        b64 = _img_to_b64(img, max_width=480)
        encoded[key] = _iterm2_escape(b64)

    # Analyze audio
    amps = _analyze_amplitude(voice_stem or wav_path)
    if not amps:
        return
    mouth_timeline, silence, wide_thresh = _build_timeline(amps)

    # Enter alternate screen
    sys.stdout.write("\033[?1049h\033[?25l\033[H")
    sys.stdout.flush()

    initial = ("closed", "open")
    _draw_iterm2(encoded[initial])

    audio = subprocess.Popen(
        ["afplay", audio_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    try:
        _run_loop(audio, mouth_timeline, encoded, 0, _draw_iterm2)
    finally:
        sys.stdout.write("\033[?25h\033[?1049l\n")
        sys.stdout.flush()
        if audio.poll() is None:
            audio.terminate()


def _draw_iterm2(data, _n_lines=0):
    sys.stdout.write("\033[H")  # cursor home
    sys.stdout.write(data)
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Shared animation loop
# ---------------------------------------------------------------------------

def _build_timeline(amps):
    rms_values = sorted(r for _, r in amps if r > 0)
    if not rms_values:
        return [], 0, 0
    bg = rms_values[len(rms_values) // 4]
    peak = rms_values[int(len(rms_values) * 0.95)]
    headroom = peak - bg
    if headroom < 1:
        headroom = peak * 0.5 or 1
    silence = bg + headroom * 0.08
    wide_thresh = bg + headroom * 0.50
    timeline = [(t, _mouth_state(r, silence, wide_thresh)) for t, r in amps]
    return timeline, silence, wide_thresh


def _run_loop(audio, mouth_timeline, frames, n_lines, draw_fn):
    """Shared animation loop for both renderers."""
    if not mouth_timeline:
        return

    # Discover available eye variants from frame keys
    all_eyes = sorted({eyes for _, eyes in frames if eyes not in ("open", "closed")})
    eye_states = ["open"] + all_eyes if all_eyes else ["open"]
    blink_interval = (2.5, 5.0)
    blink_duration = 0.12

    t0 = time.time()
    idx = 0
    prev_state = ("closed", "open")
    cur_eyes = "open"
    next_blink = t0 + random.uniform(*blink_interval)
    blink_end = 0
    next_eye_variant = t0 + random.uniform(1.0, 3.0)

    while audio.poll() is None and idx < len(mouth_timeline):
        now = time.time()
        elapsed = now - t0

        while idx < len(mouth_timeline) - 1 and mouth_timeline[idx + 1][0] <= elapsed:
            idx += 1
        mouth = mouth_timeline[idx][1]

        # Blink
        if now >= next_blink and now > blink_end:
            cur_eyes = "closed"
            blink_end = now + blink_duration
            next_blink = now + random.uniform(*blink_interval)
        elif now > blink_end and cur_eyes == "closed":
            cur_eyes = "open"

        # Eye variant
        if cur_eyes != "closed" and now >= next_eye_variant:
            cur_eyes = random.choice(eye_states)
            next_eye_variant = now + random.uniform(1.5, 4.0)

        state = (mouth, cur_eyes)
        if state not in frames:
            state = (mouth, "open")

        if state != prev_state and state in frames:
            draw_fn(frames[state], n_lines)
            prev_state = state

        time.sleep(0.016)

    # End with closed mouth
    end = ("closed", "open")
    if end in frames and prev_state != end:
        draw_fn(frames[end], n_lines)
