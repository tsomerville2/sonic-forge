#!/usr/bin/env python3
"""Test hi-res image animation — halfblock text rendering vs image protocols.

    python tests/visual/test_image2.py G        # halfblock (text art, no flicker)
    python tests/visual/test_image2.py G 80     # wider (80 columns)
    python tests/visual/test_image2.py H        # Kitty: place new THEN delete old
    python tests/visual/test_image2.py I        # iTerm2: cursor home in alt screen

Ctrl-C to stop. Uses ~/.sonic-forge/characters/aliengirl/ spritesheet.
"""

import base64
import io
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from PIL import Image
from sonic_forge.spritesheet import slice_spritesheet

SPRITE = os.path.expanduser("~/.sonic-forge/characters/aliengirl/uhd-girlalien-spritesheet.jpeg")
FRAME_DELAY = 0.4


def img_to_halfblocks(img, width_cols=60):
    """Convert PIL Image to truecolor halfblock text lines.

    Each text row = 2 pixel rows. Uses ▄ with bg=top pixel, fg=bottom pixel.
    Returns list of strings ready for terminal output.
    """
    # Resize to target width, height must be even
    ratio = width_cols / img.width
    new_h = int(img.height * ratio)
    if new_h % 2:
        new_h += 1
    img = img.resize((width_cols, new_h), Image.LANCZOS)
    px = img.load()

    lines = []
    for y in range(0, new_h, 2):
        parts = []
        for x in range(width_cols):
            r1, g1, b1 = px[x, y][:3]      # top pixel → background
            if y + 1 < new_h:
                r2, g2, b2 = px[x, y + 1][:3]  # bottom pixel → foreground
                parts.append(
                    f"\033[48;2;{r1};{g1};{b1}m"
                    f"\033[38;2;{r2};{g2};{b2}m▄"
                )
            else:
                parts.append(f"\033[38;2;{r1};{g1};{b1}m▀")
        parts.append("\033[0m")
        lines.append("".join(parts))
    return lines


def img_to_b64(img, max_w=400):
    if img.width > max_w:
        r = max_w / img.width
        img = img.resize((max_w, int(img.height * r)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def chunked_kitty(b64, **kw):
    extra = ",".join(f"{k}={v}" for k, v in kw.items())
    chunks = [b64[i:i+4096] for i in range(0, len(b64), 4096)]
    parts = []
    for i, c in enumerate(chunks):
        m = 1 if i < len(chunks) - 1 else 0
        parts.append(f"\033_G{extra},m={m};{c}\033\\" if i == 0
                     else f"\033_Gm={m};{c}\033\\")
    return "".join(parts)


# ── METHOD G: Halfblock text art (universal, no flicker) ───────────────

def method_g(frames, keys, width_cols=60):
    """Halfblock text art — truecolor ANSI, works everywhere, no flicker."""
    print(f"  Method G: halfblock text art ({width_cols} cols)")
    print(f"  Pre-rendering...")

    rendered = {}
    for key, img in frames.items():
        rendered[key] = img_to_halfblocks(img, width_cols)

    n_lines = len(rendered[keys[0]])
    print(f"  {n_lines} text rows per frame. Starting animation...\n")

    # Reserve space
    sys.stdout.write("\033[?25l")
    for _ in range(n_lines):
        sys.stdout.write("\n")

    try:
        for key in _cycle(keys):
            lines = rendered[key]
            sys.stdout.write(f"\033[{n_lines}A")  # cursor up
            for ln in lines:
                sys.stdout.write(f"\033[2K{ln}\n")  # clear line + draw
            sys.stdout.flush()
            time.sleep(FRAME_DELAY)
    finally:
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()


# ── METHOD H: Kitty place-then-delete (reduce flicker) ─────────────────

def method_h(frames_b64, keys):
    """Kitty: transmit all, place NEW first, then delete OLD (less flicker)."""
    print("  Method H: Kitty place-before-delete")
    print("  Transmitting 9 frames...")

    for i, key in enumerate(keys):
        sys.stdout.write(chunked_kitty(frames_b64[key], a="t", f=100, t="d", i=i+1, q=2))
    sys.stdout.flush()

    cur_placement = 0
    placement_counter = 100

    sys.stdout.write("\033[?25l")
    time.sleep(0.3)

    try:
        for key in _cycle(keys):
            idx = keys.index(key) + 1
            placement_counter += 1
            # Place new image FIRST (on top)
            sys.stdout.write("\0337")  # save cursor
            sys.stdout.write(f"\033_Ga=p,i={idx},p={placement_counter},q=2\033\\")
            # THEN delete old placement
            if cur_placement > 0:
                sys.stdout.write(f"\033_Ga=d,d=p,p={cur_placement},q=2\033\\")
            sys.stdout.write("\0338")  # restore cursor
            sys.stdout.flush()
            cur_placement = placement_counter
            time.sleep(FRAME_DELAY)
    finally:
        sys.stdout.write("\033_Ga=d,d=A,q=2\033\\")
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()


# ── METHOD I: iTerm2 alternate screen + precise positioning ────────────

def method_i(frames_b64, keys):
    """iTerm2: alternate screen, cursor home each frame."""
    print("  Method I: iTerm2 alt screen + cursor home")
    time.sleep(1)

    sys.stdout.write("\033[?1049h\033[?25l\033[H")
    sys.stdout.flush()

    try:
        for key in _cycle(keys):
            b64 = frames_b64[key]
            sys.stdout.write("\033[H")  # cursor home
            sys.stdout.write(
                f"\033]1337;File=inline=1;width=40;height=20"
                f";preserveAspectRatio=1:{b64}\a"
            )
            sys.stdout.flush()
            time.sleep(FRAME_DELAY)
    finally:
        sys.stdout.write("\033[?25h\033[?1049l\n")
        sys.stdout.flush()


# ── Helpers ────────────────────────────────────────────────────────────

def _cycle(keys):
    while True:
        for k in keys:
            yield k


def main():
    method = sys.argv[1].upper() if len(sys.argv) > 1 else None
    width_cols = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 60
    methods = {"G": None, "H": None, "I": None}

    if not method or method not in methods:
        print(f"\nUsage: python {sys.argv[0]} <G|H|I> [width_cols]\n")
        print("  G [cols]  — Halfblock text art (no flicker, all terminals)")
        print("  H         — Kitty place-before-delete (less flicker)")
        print("  I         — iTerm2 alt screen + cursor home")
        print()
        sys.exit(1)

    if not os.path.exists(SPRITE):
        print(f"  Spritesheet not found: {SPRITE}")
        sys.exit(1)

    print(f"\n  Loading spritesheet...")
    frames = slice_spritesheet(SPRITE)
    keys = sorted(frames.keys())

    if method == "G":
        method_g(frames, keys, width_cols)
    else:
        print(f"  Encoding frames...")
        frames_b64 = {k: img_to_b64(img) for k, img in frames.items()}
        if method == "H":
            method_h(frames_b64, keys)
        elif method == "I":
            method_i(frames_b64, keys)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write("\033_Ga=d,d=A,q=2\033\\")
        sys.stdout.write("\033[?25h\033[?1049l\n")
        sys.stdout.flush()
        print("\n  Stopped.")
