"""
trance.py -- "LET US TRANCE ONCE MORE"

Recreates: n("<0 4 0 9 7>*16").scale("g:minor").trans(-12)

That's a trance arpeggio: fast 16th note repetitions on a single pitch,
changing pitch each bar through G minor scale degrees.

Usage:
    python LABS/pattern-engine/trance.py

Generates trance.wav — play with afplay.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from songs import render_song
from tidal import mini, stack, fast, cat, atom


def trance_session():
    """n("<0 4 0 9 7>*16").scale("g:minor").trans(-12)"""

    # G minor scale degrees, transposed down one octave:
    # 0=G2, 4=D3, 0=G2, 9=Bb3, 7=G3
    # <0 4 0 9 7>*16 = the 5-note alternation sped up 16x
    # = 16 notes per cycle rapidly cycling through all 5 notes
    # G2 D3 G2 Bb3 G3 G2 D3 G2 Bb3 G3 G2 D3 G2 Bb3 G3 G2

    arp = fast(16, cat(
        atom("pluck:g2"),
        atom("pluck:d3"),
        atom("pluck:g2"),
        atom("pluck:bb3"),
        atom("pluck:g3"),
    ))

    # Same thing on a saw for thickness
    saw_arp = fast(16, cat(
        atom("saw:g2"),
        atom("saw:d3"),
        atom("saw:g2"),
        atom("saw:bb3"),
        atom("saw:g3"),
    ))

    sections = []

    # Intro: just the pluck arp alone (5 cycles = one full rotation)
    sections.append((arp, 5))

    # Add kick (10 cycles = 2 rotations)
    sections.append((stack(arp, mini("bd*4")), 10))

    # Add hats + kick (10 cycles)
    sections.append((stack(arp, mini("bd*4"), mini("~ hh ~ hh ~ hh ~ hh")), 10))

    # Layer saw underneath for thickness (10 cycles)
    sections.append((stack(
        arp, saw_arp,
        mini("bd*4"),
        mini("~ hh ~ hh ~ hh ~ hh"),
        mini("~ ~ cp ~"),
    ), 10))

    # Full with bass (15 cycles)
    sections.append((stack(
        arp, saw_arp,
        mini("bd*4"),
        mini("[hh hh hh ~]*4"),
        mini("~ sn ~ sn"),
        mini("cp(3,8)"),
        fast(4, cat(
            atom("bass:g1"),
            atom("bass:d2"),
            atom("bass:g1"),
            atom("bass:bb2"),
            atom("bass:g2"),
        )),
    ), 15))

    # Breakdown: just arp + pad (5 cycles)
    sections.append((stack(
        arp,
        mini("pad:g2 pad:bb2"),
    ), 5))

    # Final build back (15 cycles)
    sections.append((stack(
        arp, saw_arp,
        mini("bd*4"),
        mini("[hh hh hh ~]*4"),
        mini("~ sn ~ sn"),
        fast(4, cat(
            atom("bass:g1"),
            atom("bass:d2"),
            atom("bass:g1"),
            atom("bass:bb2"),
            atom("bass:g2"),
        )),
    ), 15))

    # Outro: arp alone (5 cycles)
    sections.append((arp, 5))

    return sections


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(out_dir, "trance.wav")

    print("=" * 50)
    print('  LET US TRANCE ONCE MORE')
    print('  n("<0 4 0 9 7>*16").scale("g:minor").trans(-12)')
    print("=" * 50)

    sections = trance_session()
    render_song(sections, filename, bpm=138)

    print(f"\n  Play: afplay {filename}")
