"""
songs.py -- Generate long-form evolving pattern music using tidal.py

Each song is a sequence of sections. Each section has its own pattern
that plays for N cycles. Patterns evolve between sections: euclidean
params shift, layers add/drop, notes change.

Usage:
    python LABS/pattern-engine/songs.py

Generates WAV files in LABS/pattern-engine/ (playable with afplay).
"""

import math
import os
import struct
import sys
import wave
import random

# Import the pattern engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tidal import (
    mini, stack, sequence, fast, slow, euclid, atom, silence,
    render_events, SYNTHS, _PITCHED_SYNTHS, _clamp, _synth_default,
    _parse_value, _simple_reverb,
    Fraction,
)


def render_song(sections, filename, bpm=130.0, sample_rate=44100):
    """Render a list of (pattern, n_cycles) sections into one WAV file.

    sections: list of (Pattern, cycles) tuples
    Each section flows into the next — no gaps.
    """
    cycle_duration = 4.0 * 60.0 / bpm

    # Calculate total duration
    total_cycles = sum(c for _, c in sections)
    total_duration = total_cycles * cycle_duration
    n_samples = int(total_duration * sample_rate)
    buffer = [0.0] * n_samples

    # Render each section with its cycle offset
    cycle_offset = 0
    for pattern, n_cycles in sections:
        events = render_events(pattern, cycles=n_cycles, bpm=bpm)
        time_offset = cycle_offset * cycle_duration

        for (t_start, dur, value) in events:
            synth_name, freq = _parse_value(value)
            synth_fn = SYNTHS.get(synth_name, _synth_default)
            note_dur = min(dur, 0.5) if synth_name not in _PITCHED_SYNTHS else min(dur, 2.0)
            if freq is not None and synth_name in _PITCHED_SYNTHS:
                note_samples = synth_fn(t_start + time_offset, note_dur, sample_rate, freq)
            else:
                note_samples = synth_fn(t_start + time_offset, note_dur, sample_rate)

            start_idx = int((t_start + time_offset) * sample_rate)
            for j, s in enumerate(note_samples):
                idx = start_idx + j
                if 0 <= idx < n_samples:
                    buffer[idx] += s

        cycle_offset += n_cycles

    # Reverb
    buffer = _simple_reverb(buffer, sample_rate, wet=0.25)

    # Normalize
    peak = max(abs(s) for s in buffer) if buffer else 1.0
    gain = 0.85 / peak if peak > 0 else 1.0

    # Write WAV
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw = bytearray(n_samples * 2)
        for i, s in enumerate(buffer):
            val = int(_clamp(s * gain) * 32767)
            struct.pack_into("<h", raw, i * 2, val)
        wf.writeframes(bytes(raw))

    print(f"  Wrote {filename}")
    print(f"    {total_duration:.0f}s ({total_duration/60:.1f} min), {total_cycles} cycles @ {bpm} BPM")


# ─────────────────────────────────────────────────────────
# Song 1: Four on the Floor — builds up over 3 minutes
# ─────────────────────────────────────────────────────────
def song_four_on_floor():
    """Classic dance beat that builds from minimal to full."""
    sections = []

    # Intro: just kick (8 cycles)
    sections.append((mini("bd*4"), 8))

    # Add hihat (8 cycles)
    sections.append((stack(mini("bd*4"), mini("hh*8")), 8))

    # Add snare on 2&4 (8 cycles)
    sections.append((stack(mini("bd*4"), mini("hh*8"), mini("~ sn ~ sn")), 8))

    # Add clap layer (8 cycles)
    sections.append((stack(
        mini("bd*4"), mini("hh*8"), mini("~ sn ~ sn"), mini("~ ~ cp ~")
    ), 8))

    # Breakdown: drop kick, keep hats and clap (8 cycles)
    sections.append((stack(mini("hh*8"), mini("~ ~ cp ~")), 8))

    # Build: add kick euclidean (8 cycles)
    sections.append((stack(
        mini("bd(3,8)"), mini("hh*8"), mini("~ sn ~ sn")
    ), 8))

    # Drop: full beat with double hats (16 cycles)
    sections.append((stack(
        mini("bd*4"), mini("[hh hh hh ~]*4"), mini("~ sn ~ sn"),
        mini("~ ~ cp ~"), mini("bass*2")
    ), 16))

    # Variation: euclidean shift (8 cycles)
    sections.append((stack(
        mini("bd(5,8)"), mini("hh*8"), mini("sn(2,5)"),
        mini("cp(3,8)"), mini("bass*2")
    ), 8))

    # Full power (16 cycles)
    sections.append((stack(
        mini("bd*4"), mini("hh*8"), mini("~ sn ~ sn"),
        mini("cp(3,8)"), mini("bass(3,8)")
    ), 16))

    # Outro: strip back (8 cycles)
    sections.append((stack(mini("bd*4"), mini("hh*4")), 8))

    # Final: kick alone (4 cycles)
    sections.append((mini("bd*4"), 4))

    return sections


# ─────────────────────────────────────────────────────────
# Song 2: Euclidean Journey — shifting polyrhythms
# ─────────────────────────────────────────────────────────
def song_euclidean_journey():
    """Evolving euclidean patterns — the rhythm shifts every section."""
    sections = []

    # Sparse opening: 3 over 8
    sections.append((stack(
        mini("bd(3,8)"), mini("hh(5,8)")
    ), 8))

    # Add clap
    sections.append((stack(
        mini("bd(3,8)"), mini("hh(5,8)"), mini("cp(2,5)")
    ), 8))

    # Shift to 5 over 12
    sections.append((stack(
        mini("bd(5,12)"), mini("hh(7,12)"), mini("cp(3,8)")
    ), 8))

    # Dense: 7 over 16
    sections.append((stack(
        mini("bd(7,16)"), mini("hh(9,16)"), mini("sn(5,12)"),
        mini("cp(3,8)")
    ), 12))

    # Breakdown: just hats and clap
    sections.append((stack(
        mini("hh(5,8)"), mini("cp(2,5)")
    ), 8))

    # New feel: 4 over 7 (odd meter)
    sections.append((stack(
        mini("bd(4,7)"), mini("hh(5,7)"), mini("sn(2,7)")
    ), 8))

    # African bell: 5 over 8
    sections.append((stack(
        mini("bd(5,8)"), mini("hh*8"), mini("sn(3,8)"),
        mini("cp(2,5)")
    ), 12))

    # 3 over 8 with gameboy
    sections.append((stack(
        mini("bd(3,8)"), mini("hh(5,8)"),
        mini("gameboy(3,8)")
    ), 8))

    # Full polyrhythm climax
    sections.append((stack(
        mini("bd(5,8)"), mini("hh(7,12)"), mini("sn(3,8)"),
        mini("cp(5,12)"), mini("gameboy(2,5)"),
        mini("bass(3,8)")
    ), 16))

    # Wind down
    sections.append((stack(
        mini("bd(3,8)"), mini("hh(5,8)")
    ), 8))

    return sections


# ─────────────────────────────────────────────────────────
# Song 3: Chippy Evolve — 8-bit + bytebeat builds
# ─────────────────────────────────────────────────────────
def song_chippy_evolve():
    """Gameboy arpeggios and bytebeat that builds in layers."""
    sections = []

    # Gameboy alone
    sections.append((mini("gameboy*2"), 8))

    # Add kick
    sections.append((stack(
        mini("gameboy*2"), mini("bd(3,8)")
    ), 8))

    # Add hats
    sections.append((stack(
        mini("gameboy*2"), mini("bd(3,8)"), mini("hh*4")
    ), 8))

    # Add classic bytebeat
    sections.append((stack(
        mini("gameboy*2"), mini("classic"),
        mini("bd(3,8)"), mini("hh*4")
    ), 12))

    # Strip to bytebeat only
    sections.append((stack(
        mini("classic"), mini("gameboy")
    ), 8))

    # Full 8-bit assault
    sections.append((stack(
        mini("gameboy*4"), mini("classic*2"),
        mini("bd*4"), mini("hh*8"), mini("sn(3,8)")
    ), 16))

    # Euclidean chippy
    sections.append((stack(
        mini("gameboy(5,8)"), mini("classic(3,8)"),
        mini("bd(3,8)"), mini("hh(7,12)")
    ), 12))

    # Breakdown with just gameboy + snare
    sections.append((stack(
        mini("gameboy*2"), mini("sn(2,5)")
    ), 8))

    # Build back up
    sections.append((stack(
        mini("gameboy*4"), mini("bd*4"), mini("hh*8"),
        mini("~ sn ~ sn"), mini("bass(3,8)")
    ), 16))

    # Outro
    sections.append((mini("gameboy*2"), 8))

    return sections


# ─────────────────────────────────────────────────────────
# Song 4: Minimal Techno — sparse, hypnotic, evolving
# ─────────────────────────────────────────────────────────
def song_minimal_techno():
    """Minimal techno: kick + one element at a time, slowly shifting."""
    sections = []

    # Just kick
    sections.append((mini("bd*4"), 8))

    # Kick + sparse hat
    sections.append((stack(mini("bd*4"), mini("hh(3,8)")), 8))

    # Kick + hat + bass pulse
    sections.append((stack(
        mini("bd*4"), mini("hh(3,8)"), mini("bass(2,8)")
    ), 12))

    # Drop hats, add clap
    sections.append((stack(
        mini("bd*4"), mini("bass(2,8)"), mini("cp(1,4)")
    ), 8))

    # Everything sparse
    sections.append((stack(
        mini("bd(3,8)"), mini("hh(2,5)"), mini("cp(1,8)")
    ), 12))

    # Build: more hats
    sections.append((stack(
        mini("bd*4"), mini("hh*8"), mini("bass(3,8)")
    ), 8))

    # Full but minimal
    sections.append((stack(
        mini("bd*4"), mini("hh(5,8)"), mini("~ sn ~ ~"),
        mini("bass(3,8)")
    ), 16))

    # Breakdown
    sections.append((stack(
        mini("hh(3,8)"), mini("bass")
    ), 8))

    # Return
    sections.append((stack(
        mini("bd*4"), mini("hh(5,8)"), mini("bass(3,8)")
    ), 12))

    # Kick out
    sections.append((mini("bd*4"), 8))

    return sections


# ─────────────────────────────────────────────────────────
# Generate all songs
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))

    songs = [
        ("four_on_floor", song_four_on_floor(), 130),
        ("euclidean_journey", song_euclidean_journey(), 125),
        ("chippy_evolve", song_chippy_evolve(), 140),
        ("minimal_techno", song_minimal_techno(), 128),
    ]

    print("=" * 50)
    print("Generating evolving pattern songs...")
    print("=" * 50)

    for name, sections, bpm in songs:
        print(f"\n  {name} ({bpm} BPM):")
        filename = os.path.join(out_dir, f"{name}.wav")
        render_song(sections, filename, bpm=bpm)

    print("\n" + "=" * 50)
    print("Done. Play with: afplay LABS/pattern-engine/<name>.wav")
    print("=" * 50)
