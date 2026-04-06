#!/usr/bin/env python3
"""Test hi-res image animation methods in terminal.

Run with a method letter:
    python tests/visual/test_image.py A       # iTerm2 inline + cursor up
    python tests/visual/test_image.py B       # Kitty transmit+place by ID
    python tests/visual/test_image.py C       # Kitty clear+show + cursor save/restore
    python tests/visual/test_image.py D       # Alternate screen buffer + cursor home
    python tests/visual/test_image.py E       # Clear screen each frame
    python tests/visual/test_image.py F       # Kitty with virtual placement (Unicode)

Each method cycles through 9 frames (3 mouth x 3 eye states) with 0.4s per frame.
No audio needed — just visual test. Ctrl-C to stop.

Uses: ~/.sonic-forge/characters/aliengirl/uhd-girlalien-spritesheet.jpeg
"""

import base64
import io
import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from PIL import Image
from sonic_forge.spritesheet import slice_spritesheet

SPRITE = os.path.expanduser("~/.sonic-forge/characters/aliengirl/uhd-girlalien-spritesheet.jpeg")
FRAME_DELAY = 0.4  # seconds between frames
MAX_WIDTH = 400     # pixels — smaller = faster

def img_to_b64(img):
    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")

def chunked_kitty(b64, **kw):
    """Build Kitty graphics escape with chunked data."""
    extra = ",".join(f"{k}={v}" for k, v in kw.items())
    chunks = [b64[i:i+4096] for i in range(0, len(b64), 4096)]
    parts = []
    for i, chunk in enumerate(chunks):
        m = 1 if i < len(chunks) - 1 else 0
        if i == 0:
            parts.append(f"\033_G{extra},m={m};{chunk}\033\\")
        else:
            parts.append(f"\033_Gm={m};{chunk}\033\\")
    return "".join(parts)


# ── METHOD A: iTerm2 inline image + cursor up ──────────────────────────

def method_a(frames_b64, keys):
    """iTerm2: inline image escape, cursor-up to reposition."""
    H = 20  # height in cells
    print(f"  Method A: iTerm2 inline + cursor up ({H} cell height)")
    # Reserve space
    for _ in range(H):
        print()

    for key in _cycle(keys):
        b64 = frames_b64[key]
        esc = (f"\033]1337;File=inline=1;width=40;height={H}"
               f";preserveAspectRatio=1:{b64}\a")
        sys.stdout.write(f"\033[{H}A")  # cursor up
        sys.stdout.write(esc)
        sys.stdout.flush()
        time.sleep(FRAME_DELAY)


# ── METHOD B: Kitty transmit + place by ID ─────────────────────────────

def method_b(frames_b64, keys):
    """Kitty: pre-transmit all frames, then place by ID."""
    print("  Method B: Kitty transmit + place by ID")

    # Transmit all frames
    for i, key in enumerate(keys):
        b64 = frames_b64[key]
        sys.stdout.write(chunked_kitty(b64, a="t", f=100, t="d", i=i+1, q=2))
    sys.stdout.flush()
    print("  (transmitted 9 frames)")
    time.sleep(0.5)

    for key in _cycle(keys):
        idx = keys.index(key) + 1
        # Delete all placements, display this one
        sys.stdout.write("\033_Ga=d,d=A,q=2\033\\")
        sys.stdout.write(f"\033_Ga=p,i={idx},q=2\033\\")
        sys.stdout.flush()
        time.sleep(FRAME_DELAY)


# ── METHOD C: Kitty clear + show + cursor save/restore ─────────────────

def method_c(frames_b64, keys):
    """Kitty: delete all, transmit+display, with cursor save/restore."""
    print("  Method C: Kitty clear + show + cursor save/restore")
    time.sleep(0.5)

    for key in _cycle(keys):
        b64 = frames_b64[key]
        sys.stdout.write("\033_Ga=d,d=A,q=2\033\\")  # delete all
        sys.stdout.write("\0337")  # save cursor
        sys.stdout.write(chunked_kitty(b64, a="T", f=100, t="d", q=2))
        sys.stdout.write("\0338")  # restore cursor
        sys.stdout.flush()
        time.sleep(FRAME_DELAY)


# ── METHOD D: Alternate screen buffer + cursor home ────────────────────

def method_d(frames_b64, keys):
    """Alternate screen buffer, cursor home before each frame."""
    print("  Method D: Alternate screen + cursor home")
    time.sleep(1)
    sys.stdout.write("\033[?1049h")  # enter alternate screen
    sys.stdout.write("\033[?25l")    # hide cursor

    try:
        for key in _cycle(keys):
            b64 = frames_b64[key]
            sys.stdout.write("\033[H")   # cursor home (top-left)
            sys.stdout.write("\033[2J")  # clear screen
            # For Kitty
            sys.stdout.write("\033_Ga=d,d=A,q=2\033\\")
            # Try both protocols — one will work
            sys.stdout.write(chunked_kitty(b64, a="T", f=100, t="d", q=2))
            sys.stdout.write(f"\033]1337;File=inline=1;width=40;height=20;preserveAspectRatio=1:{b64}\a")
            sys.stdout.flush()
            time.sleep(FRAME_DELAY)
    finally:
        sys.stdout.write("\033[?25h")    # show cursor
        sys.stdout.write("\033[?1049l")  # leave alternate screen
        sys.stdout.flush()


# ── METHOD E: Clear screen each frame (simplest) ──────────────────────

def method_e(frames_b64, keys):
    """Brute force: clear entire screen, redraw."""
    print("  Method E: Full clear screen each frame")
    time.sleep(1)

    try:
        sys.stdout.write("\033[?25l")
        for key in _cycle(keys):
            b64 = frames_b64[key]
            sys.stdout.write("\033[2J\033[H")  # clear + home
            sys.stdout.write("\033_Ga=d,d=A,q=2\033\\")  # kitty clear
            # Both protocols
            sys.stdout.write(chunked_kitty(b64, a="T", f=100, t="d", q=2))
            sys.stdout.write(f"\033]1337;File=inline=1;width=40;height=20;preserveAspectRatio=1:{b64}\a")
            sys.stdout.flush()
            time.sleep(FRAME_DELAY)
    finally:
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()


# ── METHOD F: Kitty virtual/Unicode placement ──────────────────────────

def method_f(frames_b64, keys):
    """Kitty: transmit with virtual placement, replace by same ID."""
    print("  Method F: Kitty single ID replacement (a=T same i= each time)")
    time.sleep(0.5)

    for key in _cycle(keys):
        b64 = frames_b64[key]
        # Delete image with id=1, then transmit new one with same id
        sys.stdout.write("\033_Ga=d,d=I,i=1,q=2\033\\")
        sys.stdout.write("\0337")  # save cursor
        sys.stdout.write(chunked_kitty(b64, a="T", f=100, t="d", i=1, q=2))
        sys.stdout.write("\0338")  # restore cursor
        sys.stdout.flush()
        time.sleep(FRAME_DELAY)


# ── Helpers ────────────────────────────────────────────────────────────

def _cycle(keys):
    """Cycle through frames forever. Ctrl-C to stop."""
    while True:
        for key in keys:
            yield key

def main():
    method = sys.argv[1].upper() if len(sys.argv) > 1 else None
    methods = {"A": method_a, "B": method_b, "C": method_c,
               "D": method_d, "E": method_e, "F": method_f}

    if not method or method not in methods:
        print(f"\nUsage: python {sys.argv[0]} <A|B|C|D|E|F>\n")
        for k, fn in methods.items():
            print(f"  {k} — {fn.__doc__.strip().splitlines()[0]}")
        print()
        sys.exit(1)

    if not os.path.exists(SPRITE):
        print(f"  Spritesheet not found: {SPRITE}")
        sys.exit(1)

    print(f"\n  Loading spritesheet...")
    frames = slice_spritesheet(SPRITE)
    keys = sorted(frames.keys())

    print(f"  Encoding {len(frames)} frames as base64 PNG ({MAX_WIDTH}px wide)...")
    frames_b64 = {}
    for key, img in frames.items():
        frames_b64[key] = img_to_b64(img)
        sz = len(frames_b64[key]) // 1024
        print(f"    {key}: {sz}KB")

    print(f"\n  Running method {method} — Ctrl-C to stop\n")
    try:
        methods[method](frames_b64, keys)
    except KeyboardInterrupt:
        # Cleanup
        sys.stdout.write("\033_Ga=d,d=A,q=2\033\\")  # kitty cleanup
        sys.stdout.write("\033[?25h\n")  # show cursor
        sys.stdout.flush()
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
