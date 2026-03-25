"""Talking heads — animated terminal characters that lip-sync to audio.

Supports ASCII line-art and pixel-art (truecolor half-block) characters
with 3 mouth states synced to audio amplitude.

Usage from code:
    from sonic_forge.talking_heads import animate_character
    animate_character("audio.wav", char_name="droid", style="pixel")

Characters: droid, human, alien
Styles: ascii, pixel
Palettes (pixel only): nes, gameboy, cga
"""

import sys
import os
import wave
import array
import subprocess
import time
import random


# ---------------------------------------------------------------------------
# ASCII characters — 3 mouth states each
# ---------------------------------------------------------------------------

# Eye directions: center, left, right — each character has eye variants
# Format: {char: {eye_dir: [eye_line_variants]}} — only the eye row(s) change

def _ascii_frames(char, mouth, eyes):
    """Build ASCII frame with given mouth and eye state."""
    return _ASCII_PARTS[char]["top"][eyes] + _ASCII_PARTS[char]["mouth"][mouth] + _ASCII_PARTS[char]["bottom"]

_ASCII_PARTS = {
    "droid": {
        "top": {
            "center": [
                "     ╭───────╮     ",
                "     │ ◉   ◉ │     ",
                "     │       │     ",
            ],
            "left": [
                "     ╭───────╮     ",
                "     │◉   ◉  │     ",
                "     │       │     ",
            ],
            "right": [
                "     ╭───────╮     ",
                "     │  ◉   ◉│     ",
                "     │       │     ",
            ],
        },
        "mouth": {
            "closed": ["     │  ───  │     ", "     ╰───────╯     "],
            "open":   ["     │  ╭─╮  │     ", "     ╰──╰─╯──╯     "],
            "wide":   ["     │ ╭───╮ │     ", "     ╰─╰───╯─╯     "],
        },
        "bottom": [
            "      ╱│   │╲      ",
            "     ╱ │   │ ╲     ",
            "    ◇  ╰───╯  ◇   ",
        ],
    },
    "human": {
        "top": {
            "center": [
                "       ╭───╮       ",
                "      ╱     ╲      ",
                "     │ ●   ● │     ",
                "     │   ▲   │     ",
            ],
            "left": [
                "       ╭───╮       ",
                "      ╱     ╲      ",
                "     │●   ●  │     ",
                "     │   ▲   │     ",
            ],
            "right": [
                "       ╭───╮       ",
                "      ╱     ╲      ",
                "     │  ●   ●│     ",
                "     │   ▲   │     ",
            ],
        },
        "mouth": {
            "closed": ["     │  ───  │     "],
            "open":   ["     │  ╭─╮  │     "],
            "wide":   ["     │ ╭───╮ │     "],
        },
        "bottom": [
            "      ╲     ╱      ",
            "       ╰───╯       ",
            "       ╱   ╲       ",
        ],
    },
    "alien": {
        "top": {
            "center": [
                "    ╱╲  ◎◎◎  ╱╲    ",
                "   ╱  ╲     ╱  ╲   ",
                "  │  ◯       ◯  │  ",
                "  │    ╲   ╱    │  ",
            ],
            "left": [
                "    ╱╲  ◎◎◎  ╱╲    ",
                "   ╱  ╲     ╱  ╲   ",
                "  │ ◯       ◯   │  ",
                "  │    ╲   ╱    │  ",
            ],
            "right": [
                "    ╱╲  ◎◎◎  ╱╲    ",
                "   ╱  ╲     ╱  ╲   ",
                "  │   ◯       ◯ │  ",
                "  │    ╲   ╱    │  ",
            ],
        },
        "mouth": {
            "closed": ["  │     ═══     │  ", "   ╲           ╱   "],
            "open":   ["  │    ╭───╮    │  ", "   ╲   ╰───╯   ╱   "],
            "wide":   ["  │  ╭───────╮  │  ", "   ╲ ╰───────╯ ╱   "],
        },
        "bottom": [
            "    ╰─────────╯    ",
            "      ║     ║      ",
        ],
    },
}

# Legacy compat — build full frames for center eyes
ASCII_CHARACTERS = {
    char: {mouth: _ascii_frames(char, mouth, "center") for mouth in ["closed", "open", "wide"]}
    for char in _ASCII_PARTS
}


# ---------------------------------------------------------------------------
# Pixel characters — 16x16 grids, NES palette indices
# ---------------------------------------------------------------------------

_ = -1  # transparent

PALETTES = {
    "nes": [
        (0, 0, 0), (124, 124, 124), (188, 188, 188), (252, 252, 252),
        (164, 0, 0), (228, 0, 0), (252, 160, 68), (252, 224, 168),
        (0, 0, 168), (0, 120, 248), (60, 188, 252), (164, 228, 252),
        (0, 168, 0), (76, 220, 72), (184, 248, 24), (216, 248, 120),
        (168, 0, 168), (248, 56, 152), (248, 120, 248), (248, 184, 248),
        (0, 168, 168), (88, 216, 204), (152, 120, 56), (228, 196, 144),
    ],
    "gameboy": [(15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)],
    "cga": [(0, 0, 0), (0, 170, 170), (170, 0, 170), (170, 170, 170)],
}

# fmt: off
_DROID_BASE = [
    [_,_,_,_,_,_,_,10,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,10,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,1,1,1,1,1,_,_,_,_,_,_],
    [_,_,_,_,1,2,2,2,2,2,1,_,_,_,_,_],
    [_,_,_,_,1,2,2,2,2,2,1,_,_,_,_,_],
    [_,_,_,1,2,10,3,2,10,3,2,1,_,_,_,_],
    [_,_,_,1,2,10,3,2,10,3,2,1,_,_,_,_],
    [_,_,_,1,2,2,2,2,2,2,2,1,_,_,_,_],
]
_DROID_CLOSED = [[_,_,_,1,2,2,1,1,1,2,2,1,_,_,_,_],[_,_,_,1,2,2,2,2,2,2,2,1,_,_,_,_]]
_DROID_OPEN =   [[_,_,_,1,2,2,1,0,1,2,2,1,_,_,_,_],[_,_,_,1,2,2,1,1,1,2,2,1,_,_,_,_]]
_DROID_WIDE =   [[_,_,_,1,2,1,0,0,0,1,2,1,_,_,_,_],[_,_,_,1,2,1,0,0,0,1,2,1,_,_,_,_]]
_DROID_BOT = [
    [_,_,_,_,1,1,1,1,1,1,1,_,_,_,_,_],
    [_,_,_,_,_,1,_,_,_,1,_,_,_,_,_,_],
    [_,_,_,1,1,1,_,_,_,1,1,1,_,_,_,_],
    [_,_,_,1,1,1,_,_,_,1,1,1,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
]

_HUMAN_BASE = [
    [_,_,_,_,_,23,23,23,23,23,_,_,_,_,_,_],
    [_,_,_,_,23,23,23,23,23,23,23,_,_,_,_,_],
    [_,_,_,23,23,23,23,23,23,23,23,23,_,_,_,_],
    [_,_,_,7,7,7,7,7,7,7,7,7,_,_,_,_],
    [_,_,_,7,7,7,7,7,7,7,7,7,_,_,_,_],
    [_,_,_,7,3,8,7,7,7,8,3,7,_,_,_,_],
    [_,_,_,7,7,7,7,7,7,7,7,7,_,_,_,_],
    [_,_,_,7,7,7,7,6,7,7,7,7,_,_,_,_],
]
_HUMAN_CLOSED = [[_,_,_,7,7,7,4,4,4,7,7,7,_,_,_,_],[_,_,_,7,7,7,7,7,7,7,7,7,_,_,_,_]]
_HUMAN_OPEN =   [[_,_,_,7,7,7,4,0,4,7,7,7,_,_,_,_],[_,_,_,7,7,7,4,4,4,7,7,7,_,_,_,_]]
_HUMAN_WIDE =   [[_,_,_,7,7,4,0,0,0,4,7,7,_,_,_,_],[_,_,_,7,7,4,3,3,3,4,7,7,_,_,_,_]]
_HUMAN_BOT = [
    [_,_,_,_,7,7,7,7,7,7,7,_,_,_,_,_],
    [_,_,_,_,_,7,7,7,7,7,_,_,_,_,_,_],
    [_,_,_,_,_,_,7,7,7,_,_,_,_,_,_,_],
    [_,_,_,_,9,9,9,9,9,9,9,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
]

_ALIEN_BASE = [
    [_,_,_,_,_,13,_,_,_,_,13,_,_,_,_,_],
    [_,_,_,_,_,_,13,_,_,13,_,_,_,_,_,_],
    [_,_,_,_,13,13,13,13,13,13,13,13,_,_,_,_],
    [_,_,_,13,13,13,13,13,13,13,13,13,13,_,_,_],
    [_,_,13,13,0,0,3,13,13,0,0,3,13,13,_,_],
    [_,_,13,13,0,0,3,13,13,0,0,3,13,13,_,_],
    [_,_,_,13,13,13,13,13,13,13,13,13,13,_,_,_],
    [_,_,_,13,13,13,13,13,13,13,13,13,13,_,_,_],
]
_ALIEN_CLOSED = [[_,_,_,_,13,13,12,12,12,13,13,_,_,_,_,_],[_,_,_,_,13,13,13,13,13,13,13,_,_,_,_,_]]
_ALIEN_OPEN =   [[_,_,_,_,13,13,12,0,12,13,13,_,_,_,_,_],[_,_,_,_,13,13,12,12,12,13,13,_,_,_,_,_]]
_ALIEN_WIDE =   [[_,_,_,_,13,12,0,0,0,12,13,_,_,_,_,_],[_,_,_,_,13,12,0,0,0,12,13,_,_,_,_,_]]
_ALIEN_BOT = [
    [_,_,_,_,_,13,13,13,13,13,_,_,_,_,_,_],
    [_,_,_,_,_,_,13,13,13,_,_,_,_,_,_,_],
    [_,_,_,_,_,13,13,13,13,13,_,_,_,_,_,_],
    [_,_,_,_,_,13,13,13,13,13,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
]

# ---------------------------------------------------------------------------
# HD (32x32) pixel characters
# ---------------------------------------------------------------------------
# Palette: 0=black 1=dk grey 2=lt grey 3=white 8=dk blue 9=blue
#          10=sky 11=lt blue 12=dk green 13=green 14=yellow-green 15=lt green
#          16=purple 17=pink 20=teal 21=cyan

_HD_ALIEN_BASE = [
    # row 0-1: antennae tips (glowing cyan)
    [_,_,_,_,_,_,_,_,21,_,_,_,_,_,_,_,_,_,_,_,_,_,_,21,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,20,_,_,_,_,_,_,_,_,_,_,_,_,_,_,20,_,_,_,_,_,_,_,_],
    # row 2-3: antennae stalks
    [_,_,_,_,_,_,_,_,_,13,_,_,_,_,_,_,_,_,_,_,_,_,13,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,13,_,_,_,_,_,_,_,_,_,_,13,_,_,_,_,_,_,_,_,_,_],
    # row 4-5: dome top
    [_,_,_,_,_,_,_,_,_,_,_,13,13,13,13,13,13,13,13,13,13,_,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,13,13,15,15,15,15,15,15,15,15,15,15,13,13,_,_,_,_,_,_,_,_,_],
    # row 6-7: upper head
    [_,_,_,_,_,_,_,_,13,15,15,14,14,14,14,14,14,14,14,14,14,15,15,13,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,13,15,14,14,14,14,14,14,14,14,14,14,14,14,14,15,13,_,_,_,_,_,_,_,_],
    # row 8-11: eyes (4 rows tall, 5 cols wide each)
    [_,_,_,_,_,_,13,14,14,0,0,0,0,3,14,14,14,14,0,0,0,0,3,14,14,13,_,_,_,_,_,_],
    [_,_,_,_,_,_,13,14,0,0,0,0,0,3,3,14,14,0,0,0,0,0,3,3,14,13,_,_,_,_,_,_],
    [_,_,_,_,_,_,13,14,0,0,0,0,0,3,3,14,14,0,0,0,0,0,3,3,14,13,_,_,_,_,_,_],
    [_,_,_,_,_,_,13,14,14,0,0,0,0,3,14,14,14,14,0,0,0,0,3,14,14,13,_,_,_,_,_,_],
    # row 12-13: cheeks
    [_,_,_,_,_,_,_,13,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,13,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,13,14,14,14,14,14,14,14,14,14,14,14,14,14,14,13,_,_,_,_,_,_,_,_],
]
_HD_ALIEN_CLOSED = [
    # row 14-15: mouth closed (thin line)
    [_,_,_,_,_,_,_,_,_,13,14,14,12,12,12,12,12,12,12,14,14,13,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,13,14,14,14,14,14,14,14,14,14,13,_,_,_,_,_,_,_,_,_,_,_],
]
_HD_ALIEN_OPEN = [
    # row 14-15: mouth open (oval)
    [_,_,_,_,_,_,_,_,_,13,14,12,12,0,0,0,0,0,12,12,14,13,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,13,14,12,12,12,12,12,12,14,13,_,_,_,_,_,_,_,_,_,_,_,_],
]
_HD_ALIEN_WIDE = [
    # row 14-15: mouth wide (big oval)
    [_,_,_,_,_,_,_,_,_,13,12,0,0,0,0,0,0,0,0,0,12,13,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,13,12,0,0,0,0,0,0,0,0,0,12,13,_,_,_,_,_,_,_,_,_,_],
]
_HD_ALIEN_BOT = [
    # row 16-17: chin
    [_,_,_,_,_,_,_,_,_,_,_,13,14,14,14,14,14,14,14,13,_,_,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,_,_,13,13,14,14,14,13,13,_,_,_,_,_,_,_,_,_,_,_,_,_],
    # row 18-19: neck
    [_,_,_,_,_,_,_,_,_,_,_,_,_,13,14,14,14,13,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,_,_,_,13,14,14,14,13,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
    # row 20-23: shoulders/body
    [_,_,_,_,_,_,_,_,_,_,13,13,13,13,14,14,14,13,13,13,13,_,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,13,14,14,14,14,14,14,14,14,14,14,14,13,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,13,14,14,14,14,14,14,14,14,14,14,14,14,14,13,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,13,14,14,14,14,14,14,14,14,14,14,14,14,14,13,_,_,_,_,_,_,_,_,_],
    # row 24-25: padding
    [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
    [_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_],
]

# Pixel eye variants — row indices in assembled grid + replacement rows per gaze
_PIXEL_EYES = {
    "droid": {  # eyes at rows 5-6: symmetric center, both shift together
        "rows": [5, 6],
        "center": [[_,_,_,1,3,10,2,2,2,10,3,1,_,_,_,_],[_,_,_,1,3,10,2,2,2,10,3,1,_,_,_,_]],
        "left":   [[_,_,_,1,10,3,2,2,10,3,2,1,_,_,_,_],[_,_,_,1,10,3,2,2,10,3,2,1,_,_,_,_]],
        "right":  [[_,_,_,1,2,3,10,2,2,3,10,1,_,_,_,_],[_,_,_,1,2,3,10,2,2,3,10,1,_,_,_,_]],
    },
    "human": {  # eyes at row 5: iris(8) shifts in 3-pixel sockets
        "rows": [5],
        "center": [[_,_,_,7,3,8,7,7,7,8,3,7,_,_,_,_]],
        "left":   [[_,_,_,7,8,3,7,7,8,3,7,7,_,_,_,_]],
        "right":  [[_,_,_,7,7,3,8,7,7,3,8,7,_,_,_,_]],
    },
    "alien": {  # eyes at rows 4-5: catchlight(3) shifts in big dark eyes
        "rows": [4, 5],
        "center": [[_,_,13,13,0,0,3,13,13,0,0,3,13,13,_,_],[_,_,13,13,0,0,3,13,13,0,0,3,13,13,_,_]],
        "left":   [[_,_,13,13,3,0,0,13,13,3,0,0,13,13,_,_],[_,_,13,13,3,0,0,13,13,3,0,0,13,13,_,_]],
        "right":  [[_,_,13,13,0,3,0,13,13,0,3,0,13,13,_,_],[_,_,13,13,0,3,0,13,13,0,3,0,13,13,_,_]],
    },
    "alien_hd": {  # eyes at rows 8-11: catchlight shifts in 6-col eye sockets
        "rows": [8, 9, 10, 11],
        "center": [
            [_,_,_,_,_,_,13,14,14,0,0,0,0,3,14,14,14,14,0,0,0,0,3,14,14,13,_,_,_,_,_,_],
            [_,_,_,_,_,_,13,14,0,0,0,0,0,3,3,14,14,0,0,0,0,0,3,3,14,13,_,_,_,_,_,_],
            [_,_,_,_,_,_,13,14,0,0,0,0,0,3,3,14,14,0,0,0,0,0,3,3,14,13,_,_,_,_,_,_],
            [_,_,_,_,_,_,13,14,14,0,0,0,0,3,14,14,14,14,0,0,0,0,3,14,14,13,_,_,_,_,_,_],
        ],
        "left": [
            [_,_,_,_,_,_,13,14,3,0,0,0,0,14,14,14,14,3,0,0,0,0,14,14,14,13,_,_,_,_,_,_],
            [_,_,_,_,_,_,13,14,3,3,0,0,0,0,14,14,14,3,3,0,0,0,0,14,14,13,_,_,_,_,_,_],
            [_,_,_,_,_,_,13,14,3,3,0,0,0,0,14,14,14,3,3,0,0,0,0,14,14,13,_,_,_,_,_,_],
            [_,_,_,_,_,_,13,14,3,0,0,0,0,14,14,14,14,3,0,0,0,0,14,14,14,13,_,_,_,_,_,_],
        ],
        "right": [
            [_,_,_,_,_,_,13,14,14,14,0,0,0,0,3,14,14,14,14,0,0,0,0,3,14,13,_,_,_,_,_,_],
            [_,_,_,_,_,_,13,14,14,0,0,0,0,3,3,14,14,14,0,0,0,0,3,3,14,13,_,_,_,_,_,_],
            [_,_,_,_,_,_,13,14,14,0,0,0,0,3,3,14,14,14,0,0,0,0,3,3,14,13,_,_,_,_,_,_],
            [_,_,_,_,_,_,13,14,14,14,0,0,0,0,3,14,14,14,14,0,0,0,0,3,14,13,_,_,_,_,_,_],
        ],
    },
}
# fmt: on


def _assemble(base, mouth, bottom):
    return [row[:] for row in base + mouth + bottom]


def _patch_pixel_eyes(grid, char, eye_dir):
    """Return copy of assembled pixel grid with eye rows patched."""
    patched = [row[:] for row in grid]
    info = _PIXEL_EYES.get(char)
    if info and eye_dir in info:
        for i, row_idx in enumerate(info["rows"]):
            patched[row_idx] = info[eye_dir][i][:]
    return patched


PIXEL_CHARACTERS = {
    "droid": {
        "closed": _assemble(_DROID_BASE, _DROID_CLOSED, _DROID_BOT),
        "open":   _assemble(_DROID_BASE, _DROID_OPEN, _DROID_BOT),
        "wide":   _assemble(_DROID_BASE, _DROID_WIDE, _DROID_BOT),
    },
    "human": {
        "closed": _assemble(_HUMAN_BASE, _HUMAN_CLOSED, _HUMAN_BOT),
        "open":   _assemble(_HUMAN_BASE, _HUMAN_OPEN, _HUMAN_BOT),
        "wide":   _assemble(_HUMAN_BASE, _HUMAN_WIDE, _HUMAN_BOT),
    },
    "alien": {
        "closed": _assemble(_ALIEN_BASE, _ALIEN_CLOSED, _ALIEN_BOT),
        "open":   _assemble(_ALIEN_BASE, _ALIEN_OPEN, _ALIEN_BOT),
        "wide":   _assemble(_ALIEN_BASE, _ALIEN_WIDE, _ALIEN_BOT),
    },
    "alien_hd": {
        "closed": _assemble(_HD_ALIEN_BASE, _HD_ALIEN_CLOSED, _HD_ALIEN_BOT),
        "open":   _assemble(_HD_ALIEN_BASE, _HD_ALIEN_OPEN, _HD_ALIEN_BOT),
        "wide":   _assemble(_HD_ALIEN_BASE, _HD_ALIEN_WIDE, _HD_ALIEN_BOT),
    },
}


# ---------------------------------------------------------------------------
# Pixel renderer — truecolor half-blocks
# ---------------------------------------------------------------------------

def _render_pixel_sprite(grid, palette, scale=2):
    """Render a pixel grid as terminal half-block lines."""
    lines = []
    height = len(grid)
    for y in range(0, height, 2):
        line = "  "
        row_top = grid[y]
        row_bot = grid[y + 1] if y + 1 < height else [-1] * len(row_top)
        for x in range(len(row_top)):
            ct = row_top[x] if x < len(row_top) else -1
            cb = row_bot[x] if x < len(row_bot) else -1
            if ct < 0 and cb < 0:
                line += " " * scale
            elif ct < 0:
                r, g, b = palette[cb % len(palette)]
                line += f"\033[38;2;{r};{g};{b}m" + "▄" * scale + "\033[0m"
            elif cb < 0:
                r, g, b = palette[ct % len(palette)]
                line += f"\033[38;2;{r};{g};{b}m" + "▀" * scale + "\033[0m"
            else:
                rt, gt, bt = palette[ct % len(palette)]
                rb, gb, bb = palette[cb % len(palette)]
                line += (f"\033[48;2;{rt};{gt};{bt}m"
                         f"\033[38;2;{rb};{gb};{bb}m" + "▄" * scale + "\033[0m")
        lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# Audio analysis
# ---------------------------------------------------------------------------

def _analyze_amplitude(wav_path, chunk_ms=33):
    """Return list of (time_sec, rms) from WAV. ~30fps resolution."""
    with wave.open(wav_path, "r") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())

    samples = array.array("h", raw) if sw == 2 else array.array("h", [((b - 128) << 8) for b in raw])
    if nch == 2:
        mono = array.array("h")
        for i in range(0, len(samples), 2):
            mono.append((samples[i] + samples[i + 1]) // 2)
        samples = mono

    chunk_n = int(sr * chunk_ms / 1000)
    return [(i / sr, (sum(s * s for s in samples[i:i + chunk_n]) / max(1, len(samples[i:i + chunk_n]))) ** 0.5)
            for i in range(0, len(samples), chunk_n)]


def _mouth_state(rms, silence, wide):
    if rms < silence:
        return "closed"
    return "wide" if rms > wide else "open"


# ---------------------------------------------------------------------------
# Frame building
# ---------------------------------------------------------------------------

_EYE_DIRS = ("center", "left", "right", "center", "center")  # weighted toward center


def _get_frame_lines(char_name, mouth, eyes, style, palette_name):
    """Get rendered terminal lines for a specific mouth+eye combo."""
    if style == "pixel":
        base_grid = PIXEL_CHARACTERS.get(char_name, PIXEL_CHARACTERS["droid"])[mouth]
        grid = _patch_pixel_eyes(base_grid, char_name, eyes)
        pal = PALETTES.get(palette_name, PALETTES["nes"])
        return _render_pixel_sprite(grid, pal)
    return _ascii_frames(char_name, mouth, eyes)


def _prerender_all(char_name, style, palette_name, text=""):
    """Pre-render all 9 mouth x eye combinations as display-ready frames."""
    rendered = {}
    for mouth in ("closed", "open", "wide"):
        for eyes in ("center", "left", "right"):
            lines = _get_frame_lines(char_name, mouth, eyes, style, palette_name)
            rendered[(mouth, eyes)] = _build_frame(lines, text)
    return rendered


def _build_frame(char_lines, text="", width=44):
    """Character art + subtitle, padded to fixed height."""
    lines = list(char_lines) + [""]
    if text:
        words = text.split()
        wrapped, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 <= width:
                cur = f"{cur} {w}" if cur else w
            else:
                wrapped.append(cur)
                cur = w
        if cur:
            wrapped.append(cur)
        for ln in wrapped[-2:]:
            lines.append(" " * ((width - len(ln)) // 2) + ln)
    min_height = max(14, len(char_lines) + 4)
    while len(lines) < min_height:
        lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Animation engine
# ---------------------------------------------------------------------------

def animate_character(wav_path, char_name="droid", text="",
                      style="ascii", palette_name="nes",
                      voice_stem=None):
    """Play wav_path while animating mouth synced to voice_stem (or wav_path)."""
    all_frames = _prerender_all(char_name, style, palette_name, text)
    amps = _analyze_amplitude(voice_stem or wav_path)
    if not amps:
        return

    # Adaptive thresholds — works for voice-only AND voice+music mixes.
    rms_values = sorted(r for _, r in amps if r > 0)
    if not rms_values:
        return
    bg = rms_values[len(rms_values) // 4]        # 25th pct = background floor
    peak = rms_values[int(len(rms_values) * 0.95)]  # 95th pct = loud voice
    headroom = peak - bg
    if headroom < 1:
        headroom = peak * 0.5 or 1
    silence = bg + headroom * 0.08   # just above background
    wide = bg + headroom * 0.50      # halfway into voice range
    mouth_timeline = [(t, _mouth_state(r, silence, wide)) for t, r in amps]

    n_lines = len(all_frames[("closed", "center")])

    # Show initial closed-mouth frame before audio starts
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    for _ in range(n_lines):
        print()
    sys.stdout.write(f"\033[{n_lines}A")
    for ln in all_frames[("closed", "center")]:
        sys.stdout.write(f"\033[2K{ln}\n")
    sys.stdout.flush()

    audio = subprocess.Popen(["afplay", wav_path],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Eye timing: pixel droid/human = slow, everything else = normal
    if style == "pixel" and char_name in ("droid", "human"):
        eye_interval = (2.0, 4.0)
    else:
        eye_interval = (0.5, 1.5)

    try:
        t0 = time.time()
        idx = 0
        prev_state = ("closed", "center")
        cur_eyes = "center"
        next_eye_change = t0 + random.uniform(*eye_interval)

        while audio.poll() is None and idx < len(mouth_timeline):
            now = time.time()
            elapsed = now - t0
            while idx < len(mouth_timeline) - 1 and mouth_timeline[idx + 1][0] <= elapsed:
                idx += 1
            mouth = mouth_timeline[idx][1]

            # Random eye movement
            if now >= next_eye_change:
                cur_eyes = random.choice(_EYE_DIRS)
                next_eye_change = now + random.uniform(*eye_interval)

            state = (mouth, cur_eyes)
            if state != prev_state:
                frame_lines = all_frames[state]
                sys.stdout.write(f"\033[{n_lines}A")
                for ln in frame_lines:
                    sys.stdout.write(f"\033[2K{ln}\n")
                sys.stdout.flush()
                prev_state = state
            time.sleep(0.016)

        # End with closed mouth
        if prev_state[0] != "closed":
            sys.stdout.write(f"\033[{n_lines}A")
            for ln in all_frames[("closed", "center")]:
                sys.stdout.write(f"\033[2K{ln}\n")
            sys.stdout.flush()

    finally:
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()
        if audio.poll() is None:
            audio.terminate()
