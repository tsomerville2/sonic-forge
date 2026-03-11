"""
trance2.py -- "LET US TRANCE ONCE MORE" v2

Same core arp but longer, more sections, huge synth pads that swell in
at key moments, second arp melody that weaves in, more dramatic arc.

Usage:
    python LABS/pattern-engine/trance2.py

Generates trance2.wav (~4 min) — play with afplay.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from songs import render_song
from tidal import mini, stack, fast, slow, cat, atom


def trance2():
    """Extended trance with huge synth pads at key moments."""

    # === Core arp: <0 4 0 9 7>*16 in G minor, down an octave ===
    arp = fast(16, cat(
        atom("pluck:g2"),
        atom("pluck:d3"),
        atom("pluck:g2"),
        atom("pluck:bb3"),
        atom("pluck:g3"),
    ))

    saw_arp = fast(16, cat(
        atom("saw:g2"),
        atom("saw:d3"),
        atom("saw:g2"),
        atom("saw:bb3"),
        atom("saw:g3"),
    ))

    # === Second melody: higher register, slower, weaves around the arp ===
    melody = fast(8, cat(
        atom("pluck:g4"),
        atom("pluck:bb4"),
        atom("pluck:d5"),
        atom("pluck:bb4"),
        atom("pluck:g4"),
        atom("pluck:f4"),
        atom("pluck:d4"),
        atom("pluck:f4"),
    ))

    # === Huge pad chords — these are the "massive synths" ===
    pad_gm = mini("pad:g3 pad:bb3 pad:d4")     # G minor chord
    pad_eb = mini("pad:eb3 pad:g3 pad:bb3")     # Eb major
    pad_cm = mini("pad:c3 pad:eb3 pad:g3")      # C minor
    pad_d  = mini("pad:d3 pad:f3 pad:a3")       # D minor (dominant feel)

    # === Bass following the arp root ===
    bass = fast(4, cat(
        atom("bass:g1"),
        atom("bass:d2"),
        atom("bass:g1"),
        atom("bass:bb2"),
        atom("bass:g2"),
    ))

    # === Acid version of the arp for peak sections ===
    acid_arp = fast(16, cat(
        atom("acid:g2"),
        atom("acid:d3"),
        atom("acid:g2"),
        atom("acid:bb3"),
        atom("acid:g3"),
    ))

    sections = []

    # 1. INTRO: arp alone, pure (5 cycles)
    sections.append((arp, 5))

    # 2. KICK enters (5 cycles)
    sections.append((stack(arp, mini("bd*4")), 5))

    # 3. HATS join (5 cycles)
    sections.append((stack(
        arp,
        mini("bd*4"),
        mini("~ hh ~ hh ~ hh ~ hh"),
    ), 5))

    # 4. FIRST HUGE PAD — Gm chord swells in (10 cycles)
    sections.append((stack(
        arp, saw_arp,
        pad_gm,
        mini("bd*4"),
        mini("~ hh ~ hh ~ hh ~ hh"),
        mini("~ ~ cp ~"),
    ), 10))

    # 5. PAD shifts to Eb, melody enters (10 cycles)
    sections.append((stack(
        arp, saw_arp,
        melody,
        pad_eb,
        mini("bd*4"),
        mini("[hh hh hh ~]*4"),
        mini("~ ~ cp ~"),
        bass,
    ), 10))

    # 6. BREAKDOWN — drop everything, just arp + huge Cm pad (5 cycles)
    sections.append((stack(
        arp,
        pad_cm,
    ), 5))

    # 7. REBUILD — kick returns, pad shifts to D (tension) (5 cycles)
    sections.append((stack(
        arp,
        pad_d,
        mini("bd*4"),
        mini("hh(5,8)"),
    ), 5))

    # 8. FIRST DROP — full power, Gm pad, melody, snare (15 cycles)
    sections.append((stack(
        arp, saw_arp,
        melody,
        pad_gm,
        mini("bd*4"),
        mini("[hh hh hh ~]*4"),
        mini("~ sn ~ sn"),
        mini("cp(3,8)"),
        bass,
    ), 15))

    # 9. VARIATION — acid arp replaces pluck, Eb pad (10 cycles)
    sections.append((stack(
        acid_arp, saw_arp,
        pad_eb,
        mini("bd*4"),
        mini("hh*8"),
        mini("~ sn ~ sn"),
        bass,
    ), 10))

    # 10. SECOND BREAKDOWN — pads only, huge and wide (5 cycles)
    sections.append((stack(
        pad_gm,
        pad_cm,
        arp,
    ), 5))

    # 11. BUILD to peak — D pad (tension), melody returns (5 cycles)
    sections.append((stack(
        arp, saw_arp,
        melody,
        pad_d,
        mini("bd*4"),
        mini("[hh hh hh ~]*4"),
        mini("cp(3,8)"),
    ), 5))

    # 12. PEAK — everything at once, acid + pluck + saw + pad + melody (15 cycles)
    sections.append((stack(
        arp, acid_arp, saw_arp,
        melody,
        pad_gm,
        mini("bd*4"),
        mini("[hh hh hh ~]*4"),
        mini("~ sn ~ sn"),
        mini("cp(3,8)"),
        bass,
    ), 15))

    # 13. OUTRO — strip layers, pad sustains (5 cycles)
    sections.append((stack(
        arp, saw_arp,
        pad_eb,
        mini("bd*4"),
    ), 5))

    # 14. FINAL — just arp and huge pad fading (5 cycles)
    sections.append((stack(
        arp,
        pad_gm,
    ), 5))

    # 15. END — arp alone (3 cycles)
    sections.append((arp, 3))

    return sections


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(out_dir, "trance2.wav")

    print("=" * 50)
    print('  LET US TRANCE ONCE MORE v2')
    print('  huge synth pads + dual arps + acid')
    print("=" * 50)

    sections = trance2()
    render_song(sections, filename, bpm=138)

    print(f"\n  Play: afplay {filename}")
