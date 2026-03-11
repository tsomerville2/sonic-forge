# How We Achieved switch.angel's Live-Coding Technique

## Date: 2026-03-10

## The Problem

switch.angel streams live Strudel sessions where she builds trance tracks in
real time — starting with a bare arp, adding kick, switching synths, cranking
filters, layering bass, riding the energy. It sounds incredible because the
song EVOLVES. Each change is a moment. The listener hears the journey.

Our first attempts with tidal.py (acid_session.py) were "too rigid" — all
sections pre-composed, no sense of live evolution. The engine was blamed.
The engine was not the problem.

## The Breakthrough

**Section-based evolution.** Each section in the song represents a REAL MOMENT
where switch.angel changed her code live. We followed her session screenshot
by screenshot, adding sections as she made changes:

```python
sections = []
sections.append((pluck_arp, 7))                                    # 0:00 bare arp
sections.append((acid_arp, 3))                                      # 0:12 switch to acid
sections.append((stack(acid_arp, mini("bd*4")), 3))                # 0:18 kick enters
sections.append((stack(acid_arp, mini("bd*4"), bass_pulse), 10))   # 0:28 bass joins
sections.append((stack(bright_arp, mini("bd*4"), supersaw_bass), 10))  # 0:46 supersaw
# ... each section = a live change she made
```

The key insight: **the song IS the session**. Not "a song inspired by" — literally
following her code changes as time-stamped sections.

## The Voiceover Layer

macOS `say` command generates speech WAV files. We mix them into the music at
specific timestamps, narrating each change ~2 seconds before it hits:

```python
voiceovers = [
    (0.5,  "in the beginning, there were five notes"),
    (10.0, "now let's switch to sawtooth, with an acid envelope"),
    (16.0, "here comes the kick drum, four on the floor"),
    # ... voice leads the change, overlapping with the transition
]
```

The `mix_voiceover()` function:
1. Uses `say -o file.aiff "text"` to generate speech
2. Converts to 44100Hz WAV with `afconvert`
3. Mixes speech samples into the music buffer at the right offset
4. Clamps to prevent clipping

## The Tech Stack (Simpler Than You'd Think)

Everything here is pure Python + macOS built-ins. No npm, no Haskell, no
SuperCollider, no browser, no WebAudio.

- **tidal.py** — Pattern engine. Strudel-inspired mini-notation parser,
  Bjorklund/Euclidean rhythms, pattern-as-function model, `stack()`, `fast()`,
  `cat()`, `atom()`, `mini()`.

- **5 pitched synths** (all pure math, no samples):
  - `acid` — TB-303 saw + resonant filter envelope snap
  - `saw` — 4 detuned saws (= supersaw)
  - `pluck` — bright attack, exponential decay
  - `pad` — slow attack, detuned triangles
  - `bass` — detuned saw pair + low-pass filter

- **6 drum synths**: `bd`, `sn`, `hh`, `oh`, `cp` + classic bytebeat

- **songs.py** — Section renderer. Takes `(pattern, n_cycles)` tuples, renders
  each section sequentially into one WAV buffer. Applies simple comb-filter reverb.

- **macOS `say`** — Text-to-speech. Free. Instant. Multiple voices available.

- **`afconvert`** — macOS built-in audio format converter. AIFF to WAV.

- **Output**: Standard 44100Hz 16-bit mono WAV. Play with `afplay`.

Total external dependencies: **zero**. Python standard library + macOS.

## What switch.angel Uses vs What We Use

| Her Tool | Our Equivalent | Notes |
|---|---|---|
| Strudel (browser) | tidal.py (Python) | Same DSL concepts, offline rendering |
| `s("sawtooth")` | `atom("acid:g2")` | Pitched synth with note |
| `s("supersaw").detune(rand)` | `atom("saw:g2")` | 4 detuned saws |
| `.acidenv(slider(0.85))` | Section change to brighter synth | No per-note params yet |
| `s("tbd:2!4")` aka `bd*4` | `mini("bd*4")` | Identical mini-notation |
| `.duck().duckdepth(.8)` | (not implemented) | Sidechain compression |
| `<0 4 0 9 7>*16` | `fast(16, cat(atom(...), ...))` | Same pattern, explicit |
| `s("top:1/2").fit()` | `mini("oh*2")` | Cymbal wash approximation |
| Live sliders | New section with different synth | Discrete steps, not continuous |
| WebAudio real-time | WAV file rendering | Offline but instant |

## What's NOT Here (Yet)

- **Continuous parameter changes** — her sliders sweep smoothly. We jump between
  sections. Could add per-sample parameter interpolation to synths.
- **Sidechain ducking** — `.duck()` compresses synths when kick hits. Classic
  trance pumping effect. Would need amplitude envelope tracking.
- **Sample playback** — `top:1/2` plays a real audio sample slowed down. We
  approximate with synths. Could add WAV sample loading.
- **Real-time rendering** — she hears changes instantly. We render the whole WAV
  then play. Could stream sections to `afplay` pipe.
- **AI-driven evolution** — the voiceover proves an AI can narrate the build.
  The next step: AI DECIDES what to add next and generates the section code.

## The Bigger Vision

This is a seed for something much larger:

1. **DSL-to-music pipeline**: Write mini-notation patterns → get WAV
2. **AI composer**: LLM generates section progressions, narrates the journey
3. **Interactive mode**: Human says "add bass" → AI adds the right pattern
4. **Web player**: Render in browser, show piano roll, live visualization
5. **Shareable sessions**: Export as self-contained HTML like Strudel

The pattern engine + voiceover mixer + section evolution = a complete music
creation framework hiding inside a code archaeology tool's LABS folder.

## Files

- `tidal.py` — Core pattern engine (synths, mini-notation parser, renderer)
- `songs.py` — Section-based song renderer with reverb
- `trance1_1.py` — THE breakthrough: switch.angel session recreation with voiceover
- `trance.py` — First successful trance track (pure, no voiceover)
- `trance2.py` — Extended version with pad chords and dual melodies
- `acid_session.py` — Earlier attempt (functional but "too rigid")
