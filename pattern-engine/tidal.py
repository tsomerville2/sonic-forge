"""
tidal.py -- Minimal TidalCycles/Strudel-inspired pattern engine in pure Python.

Zero external dependencies. Uses only stdlib: fractions, re, wave, struct, math.

Implements:
  1. Bjorklund/Euclidean rhythm algorithm
  2. Pattern-as-function model with combinators
  3. Mini-notation parser (recursive descent)
  4. WAV output via bytebeat synthesis

Run:  python tidal.py
"""

from __future__ import annotations

import math
import re
import struct
import wave
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, List, Optional


# ─────────────────────────────────────────────────────────
# 1. Bjorklund / Euclidean Algorithm
# ─────────────────────────────────────────────────────────

def bjorklund(k: int, n: int, rotation: int = 0) -> list[int]:
    """Distribute k onsets evenly across n steps. Returns list of 0/1.

    Uses the Bjorklund algorithm (same as Bresenham line-drawing, same as
    Euclid's GCD algorithm applied to rhythm). Classic reference:
    Toussaint, "The Euclidean Algorithm Generates Traditional Musical Rhythms".

    >>> bjorklund(3, 8)
    [1, 0, 0, 1, 0, 0, 1, 0]
    >>> bjorklund(5, 8)
    [1, 0, 1, 1, 0, 1, 1, 0]
    """
    if k >= n:
        return [1] * n
    if k == 0:
        return [0] * n

    # Build groups: k groups of [1], (n-k) groups of [0]
    groups = [[1]] * k + [[0]] * (n - k)

    while True:
        # How many of the shorter tail can we distribute?
        remainder = len(groups) - k
        if remainder <= 1:
            break
        to_distribute = min(k, remainder)
        new_groups = []
        for i in range(to_distribute):
            new_groups.append(groups[i] + groups[len(groups) - to_distribute + i])
        for i in range(to_distribute, len(groups) - to_distribute):
            new_groups.append(groups[i])
        groups = new_groups
        k = to_distribute

    flat = [step for group in groups for step in group]
    # Apply rotation
    if rotation:
        rotation = rotation % len(flat)
        flat = flat[rotation:] + flat[:rotation]
    return flat


# ─────────────────────────────────────────────────────────
# 2. Pattern-as-Function Model
# ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Event:
    """A single event in a pattern. Times are fractions of a cycle."""
    begin: Fraction   # start time (cycle-relative)
    end: Fraction     # end time
    value: str        # sound / note name

    def __repr__(self):
        return f"Event({float(self.begin):.3f}-{float(self.end):.3f} '{self.value}')"


class Pattern:
    """A pattern is a function from a time-span (begin, end) to a list of Events.

    This is the core Tidal insight: patterns are not data structures,
    they are continuous functions over time. You query them for any
    time window and they tell you what happens there.
    """

    def __init__(self, query_fn: Callable[[Fraction, Fraction], list[Event]]):
        self._query = query_fn

    def query(self, begin: Fraction, end: Fraction) -> list[Event]:
        """Query for events in the half-open interval [begin, end)."""
        return self._query(begin, end)

    # Convenience: query a single cycle
    def first_cycle(self) -> list[Event]:
        return self.query(Fraction(0), Fraction(1))


# --- Primitive constructors ---

def silence() -> Pattern:
    """A pattern that produces no events (rest)."""
    return Pattern(lambda b, e: [])


def atom(value: str) -> Pattern:
    """A pattern that produces one event per cycle spanning the whole cycle.

    This is the simplest possible pattern: the value fills the entire cycle.
    """
    def query_fn(begin: Fraction, end: Fraction) -> list[Event]:
        events = []
        # For each cycle that overlaps [begin, end), produce an event
        cycle_start = int(begin) if begin >= 0 else int(begin) - 1
        if Fraction(cycle_start) == begin or begin < 0:
            cycle_start = math.floor(begin)
        else:
            cycle_start = math.floor(begin)
        cycle = cycle_start
        while Fraction(cycle) < end:
            ev_begin = Fraction(cycle)
            ev_end = Fraction(cycle + 1)
            # Only include if the event overlaps [begin, end)
            if ev_end > begin and ev_begin < end:
                events.append(Event(begin=ev_begin, end=ev_end, value=value))
            cycle += 1
        return events
    return Pattern(query_fn)


# --- Combinators ---

def _split_queries(begin: Fraction, end: Fraction):
    """Split a query span into per-cycle sub-spans.

    Yields (cycle_number, sub_begin, sub_end) for each cycle touched.
    """
    cycle = math.floor(begin)
    while Fraction(cycle) < end:
        sub_begin = max(Fraction(cycle), begin)
        sub_end = min(Fraction(cycle + 1), end)
        if sub_begin < sub_end:
            yield cycle, sub_begin, sub_end
        cycle += 1


def sequence(*items) -> Pattern:
    """Divide the cycle equally among items. Each item can be a Pattern or a string.

    sequence("bd", "sn", "hh") makes bd play in [0, 1/3), sn in [1/3, 2/3), hh in [2/3, 1).
    """
    n = len(items)
    if n == 0:
        return silence()

    # Coerce strings to atoms
    pats = [atom(x) if isinstance(x, str) else x for x in items]

    def query_fn(begin: Fraction, end: Fraction) -> list[Event]:
        events = []
        for cycle, sub_begin, sub_end in _split_queries(begin, end):
            cycle_offset = Fraction(cycle)
            for i, pat in enumerate(pats):
                # Slot i occupies [cycle + i/n, cycle + (i+1)/n)
                slot_begin = cycle_offset + Fraction(i, n)
                slot_end = cycle_offset + Fraction(i + 1, n)
                # Does this slot overlap our query?
                ov_begin = max(slot_begin, sub_begin)
                ov_end = min(slot_end, sub_end)
                if ov_begin >= ov_end:
                    continue
                # Map query into the sub-pattern's own time:
                # The slot [slot_begin, slot_end) maps to one full cycle in the sub-pattern.
                # We need to query the sub-pattern for the portion that corresponds to [ov_begin, ov_end).
                scale = Fraction(n)
                inner_begin = (ov_begin - slot_begin) * scale + cycle_offset
                inner_end = (ov_end - slot_begin) * scale + cycle_offset
                inner_events = pat.query(inner_begin, inner_end)
                # Map events back to outer time
                for ev in inner_events:
                    mapped_begin = slot_begin + (ev.begin - cycle_offset) / scale
                    mapped_end = slot_begin + (ev.end - cycle_offset) / scale
                    # Clamp to slot
                    mapped_begin = max(mapped_begin, slot_begin)
                    mapped_end = min(mapped_end, slot_end)
                    if mapped_begin < mapped_end:
                        events.append(Event(begin=mapped_begin, end=mapped_end, value=ev.value))
        return events
    return Pattern(query_fn)


def stack(*patterns) -> Pattern:
    """Play all patterns simultaneously (union of events)."""
    pats = [atom(p) if isinstance(p, str) else p for p in patterns]

    def query_fn(begin: Fraction, end: Fraction) -> list[Event]:
        events = []
        for pat in pats:
            events.extend(pat.query(begin, end))
        return events
    return Pattern(query_fn)


def fast(factor: int, pattern: Pattern) -> Pattern:
    """Speed up a pattern by factor n -- it plays n times per cycle."""
    n = Fraction(factor)

    def query_fn(begin: Fraction, end: Fraction) -> list[Event]:
        # Query the inner pattern for a compressed time range
        inner_begin = begin * n
        inner_end = end * n
        inner_events = pattern.query(inner_begin, inner_end)
        # Map events back: divide times by n
        return [
            Event(begin=ev.begin / n, end=ev.end / n, value=ev.value)
            for ev in inner_events
        ]
    return Pattern(query_fn)


def slow(factor: int, pattern: Pattern) -> Pattern:
    """Slow down a pattern -- it takes n cycles to complete once."""
    n = Fraction(factor)

    def query_fn(begin: Fraction, end: Fraction) -> list[Event]:
        inner_begin = begin / n
        inner_end = end / n
        inner_events = pattern.query(inner_begin, inner_end)
        return [
            Event(begin=ev.begin * n, end=ev.end * n, value=ev.value)
            for ev in inner_events
        ]
    return Pattern(query_fn)


def euclid(k: int, n: int, pattern: Pattern, rotation: int = 0) -> Pattern:
    """Apply a Euclidean rhythm to a pattern.

    The pattern only sounds on the 'hit' steps of bjorklund(k, n).
    The cycle is divided into n equal slots; the pattern plays in slots where
    the Bjorklund sequence is 1, silence elsewhere.
    """
    hits = bjorklund(k, n, rotation)

    def query_fn(begin: Fraction, end: Fraction) -> list[Event]:
        events = []
        for cycle, sub_begin, sub_end in _split_queries(begin, end):
            cycle_offset = Fraction(cycle)
            for i in range(n):
                if not hits[i]:
                    continue
                slot_begin = cycle_offset + Fraction(i, n)
                slot_end = cycle_offset + Fraction(i + 1, n)
                ov_begin = max(slot_begin, sub_begin)
                ov_end = min(slot_end, sub_end)
                if ov_begin >= ov_end:
                    continue
                # Query the inner pattern scaled to this slot
                scale = Fraction(n)
                inner_begin = (ov_begin - slot_begin) * scale + cycle_offset
                inner_end = (ov_end - slot_begin) * scale + cycle_offset
                inner_events = pattern.query(inner_begin, inner_end)
                for ev in inner_events:
                    mapped_begin = slot_begin + (ev.begin - cycle_offset) / scale
                    mapped_end = slot_begin + (ev.end - cycle_offset) / scale
                    mapped_begin = max(mapped_begin, slot_begin)
                    mapped_end = min(mapped_end, slot_end)
                    if mapped_begin < mapped_end:
                        events.append(Event(begin=mapped_begin, end=mapped_end, value=ev.value))
        return events
    return Pattern(query_fn)


def cat(*patterns) -> Pattern:
    """Concatenate patterns: each gets one full cycle in turn.

    cat(a, b, c) plays a in cycle 0, b in cycle 1, c in cycle 2, then loops.
    The result is slowed so the full sequence takes len(patterns) cycles.
    """
    pats = [atom(p) if isinstance(p, str) else p for p in patterns]
    n = len(pats)
    if n == 0:
        return silence()

    def query_fn(begin: Fraction, end: Fraction) -> list[Event]:
        events = []
        for cycle, sub_begin, sub_end in _split_queries(begin, end):
            idx = cycle % n
            pat = pats[idx]
            # Each outer cycle maps to one full cycle of the chosen pattern
            inner_events = pat.query(sub_begin, sub_end)
            events.extend(inner_events)
        return events
    return Pattern(query_fn)


# ─────────────────────────────────────────────────────────
# 3. Mini-Notation Parser (Recursive Descent)
# ─────────────────────────────────────────────────────────

# Token types
_TOK_WORD = "WORD"       # e.g. bd, sn, hh, cp
_TOK_NUM = "NUM"         # integer
_TOK_LBRACK = "["
_TOK_RBRACK = "]"
_TOK_LPAREN = "("
_TOK_RPAREN = ")"
_TOK_STAR = "*"
_TOK_COMMA = ","
_TOK_DOT = "."
_TOK_TILDE = "~"
_TOK_EOF = "EOF"


@dataclass
class _Token:
    type: str
    value: str


def _tokenize(text: str) -> list[_Token]:
    """Tokenize mini-notation string into a flat list of tokens."""
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in " \t\n\r":
            i += 1
        elif ch == "[":
            tokens.append(_Token(_TOK_LBRACK, ch)); i += 1
        elif ch == "]":
            tokens.append(_Token(_TOK_RBRACK, ch)); i += 1
        elif ch == "(":
            tokens.append(_Token(_TOK_LPAREN, ch)); i += 1
        elif ch == ")":
            tokens.append(_Token(_TOK_RPAREN, ch)); i += 1
        elif ch == "*":
            tokens.append(_Token(_TOK_STAR, ch)); i += 1
        elif ch == ",":
            tokens.append(_Token(_TOK_COMMA, ch)); i += 1
        elif ch == ".":
            tokens.append(_Token(_TOK_DOT, ch)); i += 1
        elif ch == "~":
            tokens.append(_Token(_TOK_TILDE, ch)); i += 1
        elif ch.isdigit():
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            tokens.append(_Token(_TOK_NUM, text[i:j]))
            i = j
        elif ch.isalpha() or ch in "_-":
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] in "_-:"):
                j += 1
            tokens.append(_Token(_TOK_WORD, text[i:j]))
            i = j
        else:
            i += 1  # skip unknown chars
    tokens.append(_Token(_TOK_EOF, ""))
    return tokens


class _Parser:
    """Recursive descent parser for Tidal mini-notation.

    Grammar (simplified):
        top       = stack_expr
        stack_expr = seq_expr (',' seq_expr)*
        seq_expr  = element+ ('.' element+)*
        element   = atom_expr ('*' NUM)?  |  atom_expr '(' NUM ',' NUM ')'
        atom_expr = WORD | '~' | '[' top ']'
    """

    def __init__(self, tokens: list[_Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> _Token:
        return self.tokens[self.pos]

    def advance(self) -> _Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, ttype: str) -> _Token:
        tok = self.advance()
        if tok.type != ttype:
            raise SyntaxError(f"Expected {ttype}, got {tok.type} ('{tok.value}')")
        return tok

    def parse(self) -> Pattern:
        pat = self.parse_stack()
        return pat

    def parse_stack(self) -> Pattern:
        """stack_expr = seq_expr (',' seq_expr)*"""
        parts = [self.parse_seq()]
        while self.peek().type == _TOK_COMMA:
            self.advance()  # consume ','
            parts.append(self.parse_seq())
        if len(parts) == 1:
            return parts[0]
        return stack(*parts)

    def parse_seq(self) -> Pattern:
        """seq_expr = element+ ('.' element+)*

        The '.' operator groups elements on each side into sub-sequences,
        then sequences those groups.  "bd sn . hh hh hh" becomes
        sequence(sequence(bd, sn), sequence(hh, hh, hh)).
        """
        # Collect groups separated by '.'
        groups: list[list[Pattern]] = [[]]
        stop_tokens = {_TOK_COMMA, _TOK_RBRACK, _TOK_EOF, _TOK_RPAREN}

        while self.peek().type not in stop_tokens:
            if self.peek().type == _TOK_DOT:
                self.advance()  # consume '.'
                groups.append([])
            else:
                groups[-1].append(self.parse_element())

        # Build patterns from groups
        def group_to_pat(g: list[Pattern]) -> Pattern:
            if len(g) == 0:
                return silence()
            if len(g) == 1:
                return g[0]
            return sequence(*g)

        pats = [group_to_pat(g) for g in groups if g]  # skip empty groups

        if len(pats) == 0:
            return silence()
        if len(pats) == 1:
            return pats[0]
        return sequence(*pats)

    def parse_element(self) -> Pattern:
        """element = atom_expr suffix?
        suffix  = '*' NUM | '(' NUM ',' NUM ')'
        """
        pat = self.parse_atom()

        # Check for *N (fast)
        if self.peek().type == _TOK_STAR:
            self.advance()
            num_tok = self.expect(_TOK_NUM)
            pat = fast(int(num_tok.value), pat)

        # Check for (k, n) euclidean
        elif self.peek().type == _TOK_LPAREN:
            self.advance()  # consume '('
            k_tok = self.expect(_TOK_NUM)
            self.expect(_TOK_COMMA)
            n_tok = self.expect(_TOK_NUM)
            # Optional rotation
            rot = 0
            if self.peek().type == _TOK_COMMA:
                self.advance()
                rot_tok = self.expect(_TOK_NUM)
                rot = int(rot_tok.value)
            self.expect(_TOK_RPAREN)
            pat = euclid(int(k_tok.value), int(n_tok.value), pat, rot)

        return pat

    def parse_atom(self) -> Pattern:
        """atom_expr = WORD | '~' | '[' top ']'"""
        tok = self.peek()

        if tok.type == _TOK_WORD:
            self.advance()
            return atom(tok.value)

        elif tok.type == _TOK_TILDE:
            self.advance()
            return silence()

        elif tok.type == _TOK_LBRACK:
            self.advance()  # consume '['
            inner = self.parse_stack()
            self.expect(_TOK_RBRACK)
            return inner

        else:
            raise SyntaxError(
                f"Unexpected token {tok.type} ('{tok.value}') at position {self.pos}"
            )


def mini(notation: str) -> Pattern:
    """Parse a Tidal mini-notation string and return a Pattern.

    Examples:
        mini("bd sn hh")           -> sequence of three sounds
        mini("[bd sn] hh")         -> nested sequence
        mini("bd*4")               -> bd repeated 4 times
        mini("bd(3,8)")            -> euclidean rhythm
        mini("bd,sn")              -> stack (simultaneous)
        mini("~")                  -> silence
        mini("bd sn . hh hh hh")  -> dot-grouped sequence
    """
    tokens = _tokenize(notation)
    parser = _Parser(tokens)
    return parser.parse()


# ─────────────────────────────────────────────────────────
# 4. Rendering: events to timestamps
# ─────────────────────────────────────────────────────────

def render_events(pattern: Pattern, cycles: int = 4, bpm: float = 130.0):
    """Query pattern for N cycles, return list of (time_seconds, duration_seconds, value).

    BPM controls the tempo: one cycle = one "bar" = 4 beats at the given BPM.
    So one cycle = 4 * 60 / bpm seconds.
    """
    cycle_duration = 4.0 * 60.0 / bpm  # seconds per cycle

    events = pattern.query(Fraction(0), Fraction(cycles))
    result = []
    for ev in events:
        t_start = float(ev.begin) * cycle_duration
        t_end = float(ev.end) * cycle_duration
        duration = t_end - t_start
        result.append((t_start, duration, ev.value))
    # Sort by start time, then by value for determinism
    result.sort(key=lambda x: (x[0], x[2]))
    return result


# ─────────────────────────────────────────────────────────
# 5. WAV Output via Bytebeat Synthesis
# ─────────────────────────────────────────────────────────

def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# Note name to MIDI number
_NOTE_MAP = {
    'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11,
}

def _parse_note(name: str) -> float:
    """Parse note name like 'c2', 'eb3', 'f#4' to frequency in Hz."""
    name = name.lower().strip()
    if not name:
        return 55.0
    i = 0
    if i < len(name) and name[i] in _NOTE_MAP:
        note = _NOTE_MAP[name[i]]
        i += 1
    else:
        return 55.0
    # Sharp/flat
    if i < len(name) and name[i] in ('b', 'f'):  # b=flat (after note letter)
        if name[i] == 'b':
            note -= 1
        i += 1
    elif i < len(name) and name[i] == '#':
        note += 1
        i += 1
    elif i < len(name) and name[i] == 's':  # 's' for sharp (eb = e flat, es also works)
        note += 1
        i += 1
    # Octave
    octave = 3  # default
    if i < len(name):
        try:
            octave = int(name[i:])
        except ValueError:
            pass
    midi = (octave + 1) * 12 + note
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _parse_value(value: str):
    """Split 'synth:note' into (synth_name, frequency).
    If no colon, returns (value, None).
    """
    if ':' in value:
        parts = value.split(':', 1)
        return parts[0], _parse_note(parts[1])
    return value, None


def _simple_reverb(samples: list[float], sr: int, wet: float = 0.3) -> list[float]:
    """Simple comb filter reverb. Adds space without external deps."""
    delays = [int(sr * d) for d in [0.029, 0.037, 0.044, 0.053]]
    out = list(samples)
    for delay in delays:
        feedback = 0.4
        for i in range(delay, len(out)):
            out[i] += out[i - delay] * feedback * wet
    # Normalize if clipping
    peak = max(abs(s) for s in out) if out else 1.0
    if peak > 1.0:
        scale = 0.95 / peak
        out = [s * scale for s in out]
    return out


def _synth_kick(t: float, duration: float, sr: int) -> list[float]:
    """Synthesize a kick drum: sine wave with pitch envelope + saturation."""
    n_samples = int(duration * sr)
    samples = []
    for i in range(n_samples):
        pos = i / sr  # time in seconds from note start
        env = math.exp(-pos * 12.0)  # amplitude envelope
        # Pitch drops from ~150Hz to ~50Hz
        freq = 50.0 + 100.0 * math.exp(-pos * 30.0)
        phase = 2.0 * math.pi * freq * pos
        sample = math.sin(phase) * env
        # Soft clip for thump
        sample = math.tanh(sample * 2.0) * 0.55
        samples.append(sample)
    return samples


def _synth_snare(t: float, duration: float, sr: int) -> list[float]:
    """Synthesize a snare: sine body + noise burst."""
    n_samples = int(duration * sr)
    samples = []
    # Simple LCG for deterministic noise (no random import needed)
    noise_state = 12345 + int(t * 1000)
    for i in range(n_samples):
        pos = i / sr
        env = math.exp(-pos * 15.0)
        # Tonal body at ~180Hz
        body = math.sin(2.0 * math.pi * 180.0 * pos) * env * 0.5
        # Noise component
        noise_state = (noise_state * 1103515245 + 12345) & 0x7FFFFFFF
        noise = (noise_state / 0x7FFFFFFF) * 2.0 - 1.0
        noise_env = math.exp(-pos * 20.0)
        sample = body + noise * noise_env * 0.6
        samples.append(_clamp(sample))
    return samples


def _synth_hihat(t: float, duration: float, sr: int) -> list[float]:
    """Synthesize a hi-hat: filtered noise burst."""
    n_samples = int(duration * sr)
    samples = []
    noise_state = 67890 + int(t * 1000)
    for i in range(n_samples):
        pos = i / sr
        env = math.exp(-pos * 40.0)  # very short decay
        noise_state = (noise_state * 1103515245 + 12345) & 0x7FFFFFFF
        noise = (noise_state / 0x7FFFFFFF) * 2.0 - 1.0
        # Bandpass-ish: mix several high-freq sines for metallic quality
        metallic = (
            math.sin(2.0 * math.pi * 3500.0 * pos) * 0.3
            + math.sin(2.0 * math.pi * 5200.0 * pos) * 0.2
            + math.sin(2.0 * math.pi * 7800.0 * pos) * 0.15
        )
        sample = (noise * 0.5 + metallic) * env * 0.7
        samples.append(_clamp(sample))
    return samples


def _synth_clap(t: float, duration: float, sr: int) -> list[float]:
    """Synthesize a clap: multiple short noise bursts."""
    n_samples = int(duration * sr)
    samples = []
    noise_state = 11111 + int(t * 1000)
    for i in range(n_samples):
        pos = i / sr
        # Multiple attack spikes to simulate hand clap cluster
        env = 0.0
        for burst in range(4):
            burst_time = burst * 0.008
            if pos >= burst_time:
                env += math.exp(-(pos - burst_time) * 30.0) * 0.4
        # Main tail
        env += math.exp(-pos * 12.0) * 0.6
        env = min(env, 1.0)
        noise_state = (noise_state * 1103515245 + 12345) & 0x7FFFFFFF
        noise = (noise_state / 0x7FFFFFFF) * 2.0 - 1.0
        # Bandpass character
        bp = math.sin(2.0 * math.pi * 1200.0 * pos)
        sample = (noise * 0.6 + bp * 0.3) * env * 0.7
        samples.append(_clamp(sample))
    return samples


def _synth_classic_bytebeat(t: float, duration: float, sr: int) -> list[float]:
    """The classic bytebeat: t*((t>>12|t>>8)&63&t>>4) mapped to audio."""
    n_samples = int(duration * sr)
    samples = []
    # Bytebeat runs at 8kHz conventionally
    bb_rate = 8000
    for i in range(n_samples):
        pos = i / sr
        env = math.exp(-pos * 3.0)
        bb_t = int((t + pos) * bb_rate) & 0xFFFFFFFF
        if bb_t == 0:
            bb_t = 1
        try:
            raw = bb_t * (((bb_t >> 12) | (bb_t >> 8)) & 63 & (bb_t >> 4))
            val = ((raw & 0xFF) / 127.5) - 1.0  # normalize to [-1, 1]
        except Exception:
            val = 0.0
        samples.append(_clamp(val * env * 0.5))
    return samples


def _synth_gameboy(t: float, duration: float, sr: int) -> list[float]:
    """Gameboy-esque square wave arpeggio."""
    n_samples = int(duration * sr)
    samples = []
    freqs = [220.0, 277.18, 329.63, 440.0]  # A3, C#4, E4, A4
    for i in range(n_samples):
        pos = i / sr
        env = math.exp(-pos * 5.0)
        # Switch notes every 60ms
        note_idx = int(pos / 0.06) % len(freqs)
        freq = freqs[note_idx]
        # Square wave via sign of sine
        phase = 2.0 * math.pi * freq * pos
        sample = 1.0 if math.sin(phase) >= 0 else -1.0
        samples.append(sample * env * 0.4)
    return samples


def _synth_bass(t: float, duration: float, sr: int, freq: float = 55.0) -> list[float]:
    """Bass: detuned saw pair with filter envelope."""
    n_samples = int(duration * sr)
    samples = []
    detune = 1.005
    phase1 = 0.0
    phase2 = 0.0
    filt_state = 0.0
    for i in range(n_samples):
        pos = i / sr
        env = min(pos * 100.0, 1.0) * math.exp(-pos * 4.0)
        # Two detuned saws
        phase1 += freq / sr
        phase2 += freq * detune / sr
        saw1 = (phase1 % 1.0) * 2.0 - 1.0
        saw2 = (phase2 % 1.0) * 2.0 - 1.0
        raw = (saw1 + saw2) * 0.5
        # Simple one-pole LPF: cutoff drops over time
        cutoff = 0.15 + 0.35 * math.exp(-pos * 8.0)
        filt_state += cutoff * (raw - filt_state)
        samples.append(_clamp(filt_state * env * 0.7))
    return samples


def _synth_acid(t: float, duration: float, sr: int, freq: float = 55.0) -> list[float]:
    """TB-303 acid: saw + high resonance filter with envelope snap."""
    n_samples = int(duration * sr)
    samples = []
    phase = 0.0
    filt_state = 0.0
    filt_prev = 0.0
    for i in range(n_samples):
        pos = i / sr
        env = min(pos * 200.0, 1.0) * math.exp(-pos * 6.0)
        # Saw oscillator
        phase += freq / sr
        saw = (phase % 1.0) * 2.0 - 1.0
        # Resonant filter: cutoff snaps open then decays
        cutoff = 0.05 + 0.45 * math.exp(-pos * 15.0)
        resonance = 0.45
        hp = saw - filt_state
        bp = filt_state - filt_prev
        filt_prev = filt_state
        filt_state += cutoff * hp + resonance * bp
        samples.append(_clamp(filt_state * env * 0.2))
    return samples


def _synth_saw(t: float, duration: float, sr: int, freq: float = 220.0) -> list[float]:
    """Supersaw: 4 detuned saws for thick sound."""
    n_samples = int(duration * sr)
    samples = []
    detunes = [0.995, 1.0, 1.005, 1.01]
    phases = [0.0] * 4
    filt_state = 0.0
    for i in range(n_samples):
        pos = i / sr
        env = min(pos * 50.0, 1.0) * math.exp(-pos * 2.5)
        raw = 0.0
        for d in range(4):
            phases[d] += freq * detunes[d] / sr
            raw += (phases[d] % 1.0) * 2.0 - 1.0
        raw *= 0.25
        cutoff = 0.1 + 0.3 * math.exp(-pos * 3.0)
        filt_state += cutoff * (raw - filt_state)
        samples.append(_clamp(filt_state * env * 0.7))
    return samples


def _synth_pluck(t: float, duration: float, sr: int, freq: float = 440.0) -> list[float]:
    """Pluck: bright attack, fast decay, metallic."""
    n_samples = int(duration * sr)
    samples = []
    phase = 0.0
    filt_state = 0.0
    for i in range(n_samples):
        pos = i / sr
        env = math.exp(-pos * 12.0)
        # Square + sine for brightness
        phase += freq / sr
        p = phase % 1.0
        sq = 1.0 if p < 0.5 else -1.0
        raw = sq * 0.6 + math.sin(2.0 * math.pi * freq * pos) * 0.4
        # Filter closes fast
        cutoff = 0.08 + 0.6 * math.exp(-pos * 20.0)
        filt_state += cutoff * (raw - filt_state)
        samples.append(_clamp(filt_state * env * 0.7))
    return samples


def _synth_pad(t: float, duration: float, sr: int, freq: float = 220.0) -> list[float]:
    """Pad: slow attack, sustained, detuned triangles."""
    n_samples = int(duration * sr)
    samples = []
    detunes = [0.997, 1.0, 1.003]
    phases = [0.0] * 3
    for i in range(n_samples):
        pos = i / sr
        # Slow attack, slow release
        attack = min(pos * 5.0, 1.0)
        release = min((duration - pos) * 5.0, 1.0) if pos > duration - 0.2 else 1.0
        env = attack * release
        raw = 0.0
        for d in range(3):
            phases[d] += freq * detunes[d] / sr
            # Triangle wave
            p = phases[d] % 1.0
            raw += (4.0 * abs(p - 0.5) - 1.0)
        raw *= 0.33
        samples.append(_clamp(raw * env * 0.5))
    return samples


# Registry of synthesizers keyed by pattern value
SYNTHS = {
    "bd":      _synth_kick,
    "kick":    _synth_kick,
    "sn":      _synth_snare,
    "snare":   _synth_snare,
    "hh":      _synth_hihat,
    "hat":     _synth_hihat,
    "oh":      _synth_hihat,
    "cp":      _synth_clap,
    "clap":    _synth_clap,
    "classic": _synth_classic_bytebeat,
    "gameboy": _synth_gameboy,
    "bass":    _synth_bass,
    "acid":    _synth_acid,
    "saw":     _synth_saw,
    "pluck":   _synth_pluck,
    "pad":     _synth_pad,
}

# Synths that accept a frequency parameter
_PITCHED_SYNTHS = {"bass", "acid", "saw", "pluck", "pad"}


def _synth_default(t: float, duration: float, sr: int) -> list[float]:
    """Fallback synth: a short beep at 440Hz."""
    n_samples = int(duration * sr)
    samples = []
    for i in range(n_samples):
        pos = i / sr
        env = math.exp(-pos * 10.0)
        sample = math.sin(2.0 * math.pi * 440.0 * pos) * env * 0.5
        samples.append(sample)
    return samples


def render_wav(
    pattern: Pattern,
    filename: str,
    cycles: int = 8,
    bpm: float = 130.0,
    sample_rate: int = 44100,
):
    """Render a pattern to a WAV file using bytebeat/synth formulas as voices.

    Each unique value in the pattern maps to a synthesizer function.
    Events are mixed additively into a mono 16-bit PCM buffer.
    """
    cycle_duration = 4.0 * 60.0 / bpm
    total_duration = cycles * cycle_duration
    n_samples = int(total_duration * sample_rate)
    buffer = [0.0] * n_samples

    # Get all events
    timed_events = render_events(pattern, cycles=cycles, bpm=bpm)

    for (t_start, dur, value) in timed_events:
        synth_name, freq = _parse_value(value)
        synth_fn = SYNTHS.get(synth_name, _synth_default)
        # Limit individual note duration for percussion
        note_dur = min(dur, 0.5) if synth_name not in _PITCHED_SYNTHS else min(dur, 2.0)
        if freq is not None and synth_name in _PITCHED_SYNTHS:
            note_samples = synth_fn(t_start, note_dur, sample_rate, freq)
        else:
            note_samples = synth_fn(t_start, note_dur, sample_rate)

        start_idx = int(t_start * sample_rate)
        for j, s in enumerate(note_samples):
            idx = start_idx + j
            if 0 <= idx < n_samples:
                buffer[idx] += s

    # Apply reverb
    buffer = _simple_reverb(buffer, sample_rate, wet=0.25)

    # Normalize to prevent clipping
    peak = max(abs(s) for s in buffer) if buffer else 1.0
    if peak > 0:
        gain = 0.9 / peak
    else:
        gain = 1.0

    # Write WAV
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        raw = b""
        for s in buffer:
            val = int(_clamp(s * gain) * 32767)
            raw += struct.pack("<h", val)
        wf.writeframes(raw)

    print(f"  Wrote {filename} ({total_duration:.1f}s, {n_samples} samples, {len(timed_events)} events)")


# ─────────────────────────────────────────────────────────
# Demo / Test
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("tidal.py -- Minimal Pattern Engine Demo")
    print("=" * 60)

    # --- 1. Bjorklund tests ---
    print("\n--- Bjorklund / Euclidean Rhythms ---")
    test_cases = [
        (3, 8, 0, [1, 0, 0, 1, 0, 0, 1, 0]),     # Cuban tresillo
        (5, 8, 0, [1, 0, 1, 1, 0, 1, 1, 0]),       # West African bell
        (7, 16, 0, [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]),
        (3, 8, 1, [0, 0, 1, 0, 0, 1, 0, 1]),       # Tresillo rotated by 1
    ]
    all_pass = True
    for k, n, rot, expected in test_cases:
        result = bjorklund(k, n, rot)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  bjorklund({k}, {n}, rot={rot}) = {result}  [{status}]")
        if result != expected:
            print(f"    expected: {expected}")

    # --- 2. Pattern combinators ---
    print("\n--- Pattern Combinators ---")

    print("\n  atom('bd') cycle 0-1:")
    for ev in atom("bd").first_cycle():
        print(f"    {ev}")

    print("\n  sequence('bd', 'sn', 'hh') cycle 0-1:")
    for ev in sequence("bd", "sn", "hh").first_cycle():
        print(f"    {ev}")

    print("\n  fast(2, sequence('bd', 'sn')) cycle 0-1:")
    for ev in fast(2, sequence("bd", "sn")).first_cycle():
        print(f"    {ev}")

    print("\n  slow(2, sequence('bd', 'sn')) cycles 0-2:")
    for ev in slow(2, sequence("bd", "sn")).query(Fraction(0), Fraction(2)):
        print(f"    {ev}")

    print("\n  euclid(3, 8, atom('bd')) cycle 0-1:")
    for ev in euclid(3, 8, atom("bd")).first_cycle():
        print(f"    {ev}")

    print("\n  stack(atom('bd'), atom('hh')) cycle 0-1:")
    for ev in stack(atom("bd"), atom("hh")).first_cycle():
        print(f"    {ev}")

    print("\n  cat('bd', 'sn', 'hh') cycles 0-3:")
    for ev in cat("bd", "sn", "hh").query(Fraction(0), Fraction(3)):
        print(f"    {ev}")

    # --- 3. Mini-notation ---
    print("\n--- Mini-Notation Parser ---")

    test_notations = [
        "bd sn hh",
        "[bd sn] hh",
        "bd*4",
        "bd(3,8)",
        "bd,sn",
        "~",
        "bd sn . hh hh hh",
        "[bd bd] sn [hh hh hh hh] cp",
    ]

    for notation in test_notations:
        print(f"\n  mini(\"{notation}\") cycle 0-1:")
        pat = mini(notation)
        events = pat.first_cycle()
        if not events:
            print("    (silence)")
        for ev in events:
            print(f"    {ev}")

    # --- 4. Combined: stack of mini-notation patterns ---
    print("\n--- Combined: stack(mini('bd(3,8)'), mini('hh*4')) ---")
    combined = stack(mini("bd(3,8)"), mini("hh*4"))
    for ev in combined.first_cycle():
        print(f"  {ev}")

    # --- 5. Render events (timed) ---
    print("\n--- Rendered Events (2 cycles @ 130 BPM) ---")
    rendered = render_events(mini("bd sn hh cp"), cycles=2, bpm=130.0)
    for (t, dur, val) in rendered:
        print(f"  t={t:6.3f}s  dur={dur:.3f}s  {val}")

    # --- 6. WAV output ---
    print("\n--- WAV Output ---")
    import os
    out_dir = os.path.dirname(os.path.abspath(__file__))

    # A four-on-the-floor pattern with hihat and snare
    four_on_floor = stack(
        mini("bd*4"),
        mini("~ sn ~ sn"),
        mini("hh*8"),
    )
    render_wav(four_on_floor, os.path.join(out_dir, "four_on_floor.wav"),
               cycles=4, bpm=130)

    # Euclidean rhythm demo
    euclidean_beat = stack(
        mini("bd(3,8)"),
        mini("hh(5,8)"),
        mini("cp(2,5)"),
    )
    render_wav(euclidean_beat, os.path.join(out_dir, "euclidean_beat.wav"),
               cycles=4, bpm=120)

    # Bytebeat/gameboy demo
    chippy = stack(
        mini("gameboy*2"),
        mini("bd(3,8)"),
        mini("hh*4"),
    )
    render_wav(chippy, os.path.join(out_dir, "chippy.wav"),
               cycles=4, bpm=140)

    print("\n" + "=" * 60)
    print("All demos complete." + (" All Bjorklund tests passed." if all_pass else " SOME TESTS FAILED."))
    print("=" * 60)
