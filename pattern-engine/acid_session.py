"""
acid_session.py -- Switch.angel-style acid session using tidal.py

Pitched acid bass, supersaw stabs, pluck melodies, euclidean drums.
Uses the mini-notation with pitch: acid:c2, saw:eb3, pluck:g4

Usage:
    python LABS/pattern-engine/acid_session.py

Generates acid_session.wav (~3 min) — play with afplay.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from songs import render_song
from tidal import mini, stack


def acid_session():
    """Switch.angel-style acid session: builds from acid bass to full rave."""
    sections = []

    # === INTRO: acid bass alone, simple pattern (8 cycles) ===
    sections.append((stack(
        mini("[acid:c2 acid:c2 acid:eb2 acid:c2] [acid:f2 acid:eb2 acid:c2 acid:bb1]"),
    ), 8))

    # === ADD KICK: four-on-floor under acid (8 cycles) ===
    sections.append((stack(
        mini("bd*4"),
        mini("[acid:c2 acid:c2 acid:eb2 acid:c2] [acid:f2 acid:eb2 acid:c2 acid:bb1]"),
    ), 8))

    # === ADD HATS: offbeat (8 cycles) ===
    sections.append((stack(
        mini("bd*4"),
        mini("~ hh ~ hh ~ hh ~ hh"),
        mini("[acid:c2 acid:c2 acid:eb2 acid:c2] [acid:f2 acid:eb2 acid:c2 acid:bb1]"),
    ), 8))

    # === FIRST BUILD: add clap, acid gets wilder (8 cycles) ===
    sections.append((stack(
        mini("bd*4"),
        mini("~ hh ~ hh ~ hh ~ hh"),
        mini("~ ~ cp ~"),
        mini("[acid:c2 acid:eb2 acid:f2 acid:ab2] [acid:bb2 acid:ab2 acid:f2 acid:eb2]"),
    ), 8))

    # === BREAKDOWN: drop kick, pads enter (8 cycles) ===
    sections.append((stack(
        mini("hh(5,8)"),
        mini("pad:c3 pad:eb3"),
        mini("acid:c2(3,8)"),
    ), 8))

    # === REBUILD: kick returns, pluck melody (8 cycles) ===
    sections.append((stack(
        mini("bd*4"),
        mini("~ hh ~ hh ~ hh ~ hh"),
        mini("~ ~ cp ~"),
        mini("[acid:c2 acid:c2 acid:eb2 acid:c2] [acid:f2 acid:eb2 acid:c2 acid:bb1]"),
        mini("[pluck:c4 ~ pluck:eb4 ~] [pluck:f4 pluck:eb4 ~ ~]"),
    ), 8))

    # === DROP: full power, euclidean everything (12 cycles) ===
    sections.append((stack(
        mini("bd*4"),
        mini("[hh hh hh ~]*4"),
        mini("~ sn ~ sn"),
        mini("cp(3,8)"),
        mini("[acid:c2 acid:eb2 acid:f2 acid:ab2]*2"),
        mini("[pluck:c4 pluck:eb4 pluck:g4 pluck:c5]*2"),
        mini("bass:c1(3,8)"),
    ), 12))

    # === VARIATION: shift the acid pattern (8 cycles) ===
    sections.append((stack(
        mini("bd*4"),
        mini("hh*8"),
        mini("~ sn ~ sn"),
        mini("[acid:f2 acid:f2 acid:ab2 acid:f2] [acid:bb2 acid:ab2 acid:f2 acid:eb2]"),
        mini("pluck:f4(5,8)"),
        mini("bass:f1(3,8)"),
    ), 8))

    # === PEAK: supersaw stabs join (12 cycles) ===
    sections.append((stack(
        mini("bd*4"),
        mini("[hh hh hh ~]*4"),
        mini("~ sn ~ sn"),
        mini("cp(3,8)"),
        mini("[acid:c2 acid:eb2 acid:f2 acid:ab2]*2"),
        mini("saw:c3(3,8)"),
        mini("[pluck:c5 ~ pluck:g4 ~] [pluck:eb5 pluck:c5 ~ ~]"),
        mini("bass:c1*2"),
    ), 12))

    # === BREAKDOWN 2: just pad + sparse acid (8 cycles) ===
    sections.append((stack(
        mini("pad:eb3 pad:c3"),
        mini("acid:c2(2,8)"),
        mini("hh(3,8)"),
    ), 8))

    # === FINAL BUILD: everything returns (12 cycles) ===
    sections.append((stack(
        mini("bd*4"),
        mini("hh*8"),
        mini("~ sn ~ sn"),
        mini("[acid:c2 acid:eb2 acid:f2 acid:ab2] [acid:c2 acid:bb1 acid:ab1 acid:c2]"),
        mini("[pluck:c4 pluck:eb4 pluck:g4 pluck:c5]*2"),
        mini("saw:c3(5,8)"),
        mini("bass:c1*2"),
    ), 12))

    # === OUTRO: strip to acid + kick (8 cycles) ===
    sections.append((stack(
        mini("bd*4"),
        mini("[acid:c2 acid:c2 acid:eb2 acid:c2] [acid:f2 acid:eb2 acid:c2 acid:bb1]"),
    ), 8))

    # === END: acid alone, fading (4 cycles) ===
    sections.append((
        mini("acid:c2(3,8)"),
    4))

    return sections


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(out_dir, "acid_session.wav")

    print("=" * 50)
    print("  Acid Session — switch.angel style")
    print("  Pitched acid bass, supersaw stabs, pluck melodies")
    print("=" * 50)

    sections = acid_session()
    render_song(sections, filename, bpm=136)

    print(f"\n  Play: afplay {filename}")
