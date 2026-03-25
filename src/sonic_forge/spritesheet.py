"""Spritesheet slicer for talking head characters.

Slices a 3x3 spritesheet into 9 individual frames for animation.

Layout convention:
    Row 0 (top):    mouth CLOSED  — eyes open, eyes closed, eyes variant
    Row 1 (middle): mouth OPEN    — eyes open, eyes closed, eyes variant
    Row 2 (bottom): mouth WIDE    — eyes open, eyes closed, eyes variant

Usage:
    from sonic_forge.spritesheet import slice_spritesheet
    frames = slice_spritesheet("path/to/spritesheet.jpg")
    # frames = {("closed","open"): PIL.Image, ("closed","closed"): PIL.Image, ...}
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PIL import Image

# Grid layout
ROWS = ["closed", "open", "wide"]       # mouth states, top to bottom
COLS = ["open", "closed", "variant"]     # eye states, left to right


def _col_names(n: int) -> list[str]:
    """Generate column (eye state) names for n columns."""
    base = ["open", "closed", "variant"]
    if n <= 3:
        return base[:n]
    return base + [f"variant{i}" for i in range(2, n - 1)]


def _row_names(n: int) -> list[str]:
    """Generate row (mouth state) names for n rows."""
    base = ["closed", "open", "wide"]
    if n <= 3:
        return base[:n]
    return base + [f"wide{i}" for i in range(2, n - 1)]


TRIM_PCT = 0.02  # trim 2% off each edge of each cell to cut AI grid bleed


def slice_spritesheet(
    path: str,
    output_dir: Optional[str] = None,
    cols: int = 3,
    rows: int = 3,
    trim: Optional[float] = None,
) -> dict[tuple[str, str], Image.Image]:
    """Slice a 3x3 spritesheet into labeled frames.

    Args:
        path: Path to the spritesheet image (JPG or PNG).
        output_dir: If set, save individual frames as PNGs here.
        cols: Number of columns (default 3).
        rows: Number of rows (default 3).
        trim: Fraction of each cell to trim from edges (default TRIM_PCT).
              Set to 0 to disable trimming.

    Returns:
        Dict mapping (mouth_state, eye_state) -> PIL Image.
        mouth_state: "closed", "open", "wide"
        eye_state: "open", "closed", "variant"
    """
    if trim is None:
        trim = TRIM_PCT

    img = Image.open(path)
    w, h = img.size

    row_labels = _row_names(rows)
    col_labels = _col_names(cols)

    frames = {}
    for row_idx, mouth in enumerate(row_labels):
        for col_idx, eyes in enumerate(col_labels):
            x1 = round(col_idx * w / cols)
            y1 = round(row_idx * h / rows)
            x2 = round((col_idx + 1) * w / cols)
            y2 = round((row_idx + 1) * h / rows)

            # Trim edges to cut AI gridline bleed
            if trim > 0:
                cell_w = x2 - x1
                cell_h = y2 - y1
                tx = round(cell_w * trim)
                ty = round(cell_h * trim)
                x1, y1 = x1 + tx, y1 + ty
                x2, y2 = x2 - tx, y2 - ty

            cell = img.crop((x1, y1, x2, y2))
            frames[(mouth, eyes)] = cell

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                cell.save(os.path.join(output_dir, f"{mouth}_{eyes}.png"))

    return frames


def save_grid_info(char_dir: str, rows: int, cols: int) -> None:
    """Save grid dimensions so load_character_frames knows how to slice."""
    with open(os.path.join(char_dir, "grid.txt"), "w") as f:
        f.write(f"{rows}x{cols}\n")


def _read_grid_info(char_dir: str) -> tuple[int, int]:
    """Read saved grid dimensions. Returns (rows, cols), default (3, 3)."""
    grid_file = os.path.join(char_dir, "grid.txt")
    if os.path.exists(grid_file):
        with open(grid_file) as f:
            text = f.read().strip()
        parts = text.lower().split("x")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])
    return 3, 3


def load_character_frames(char_dir: str) -> Optional[dict[tuple[str, str], Image.Image]]:
    """Load frames for a character directory.

    Tries spritesheet first, then falls back to individual frame files.
    Returns None if no valid character found.
    """
    char_path = Path(char_dir)
    rows, cols = _read_grid_info(char_dir)

    # Look for spritesheet
    for ext in (".jpeg", ".jpg", ".png"):
        candidates = list(char_path.glob(f"*spritesheet*{ext}")) + list(char_path.glob(f"*sprite*{ext}"))
        if candidates:
            return slice_spritesheet(str(candidates[0]), rows=rows, cols=cols)

    # Look for pre-sliced individual frames
    row_labels = _row_names(rows)
    col_labels = _col_names(cols)
    frames = {}
    for mouth in row_labels:
        for eyes in col_labels:
            for ext in (".png", ".jpg", ".jpeg"):
                fp = char_path / f"{mouth}_{eyes}{ext}"
                if fp.exists():
                    frames[(mouth, eyes)] = Image.open(str(fp))
                    break
    return frames if frames else None
