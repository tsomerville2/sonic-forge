# DSL: Text-to-Music YAML

A dead-simple YAML format for describing songs. You think in words, instruments, and timing — the converter handles the rest.

## Quick Start

```bash
python LABS/pattern-engine/songfile.py my_song.yaml --play
python LABS/pattern-engine/songfile.py my_song.yaml --voice Alex --lead 3.0
python LABS/pattern-engine/songfile.py my_song.yaml -o output.wav
```

## The Format

```yaml
title: name of your song
bpm: 128                    # tempo
voice: Samantha             # macOS voice for narration
voice_lead: 2.0             # seconds BEFORE each change to start speaking

sections:
  - say: "what to say out loud"
    cycles: 8               # how long this section lasts (1 cycle = 4 beats)
    layers:
      - synth: pluck
        notes: g2 d3 g2 bb3 g3
        fast: 16
      - mini: "bd*4"
```

That's it. Sections play in order. Each section has layers stacked on top of each other. The `say` text gets spoken right before the section starts.

## Sections

Each section is a moment in time. The song evolves by adding/removing/changing layers between sections — just like a DJ or live coder changing things on the fly.

```yaml
sections:
  - say: "just a bass pulse"          # section 1: sparse
    cycles: 8
    layers:
      - synth: bass
        notes: c1
        fast: 4

  - say: "now the arp comes in"       # section 2: building
    cycles: 8
    layers:
      - synth: bass
        notes: c1
        fast: 4
      - synth: acid
        notes: c2 eb2 f2 ab2
        fast: 16
      - mini: "bd*4"
```

### Timing

- `cycles` = how many loops this section plays
- At 128 BPM: 1 cycle = 4 beats = 1.875 seconds
- At 136 BPM: 1 cycle = 4 beats = 1.765 seconds
- 8 cycles at 128 BPM = 15 seconds
- Rule of thumb: 4-8 cycles for transitions, 12-20 cycles for jamming sections

## Layers

Two types:

### Pitched Synth Layer

```yaml
- synth: acid               # synth voice (see below)
  notes: c2 eb2 f2 ab2      # space-separated notes
  fast: 16                   # speed multiplier (optional, default 1)
```

The notes cycle in order. `fast: 16` means 16 notes per cycle (rapid arpeggio). `fast: 4` means 4 notes per cycle (quarter-note rhythm). No `fast` = one note fills the whole cycle (sustained).

### Mini-Notation Layer

```yaml
- mini: "bd*4"               # tidal mini-notation
- mini: "~ hh ~ hh ~ hh ~ hh"
- mini: "cp(3,8)"            # euclidean rhythm
- mini: "[hh hh hh ~]*4"
```

Full mini-notation from Strudel/TidalCycles. Supports `*` (repeat), `~` (rest), `[]` (grouping), `(k,n)` (euclidean).

## Available Synths

| Name    | Sound                                      | Good For                    |
|---------|--------------------------------------------|-----------------------------|
| `pluck` | Bright attack, fast decay                  | Arps, melodies, intros      |
| `acid`  | TB-303 saw + resonant filter snap          | Acid bass, trance arps      |
| `saw`   | 4 detuned saws (supersaw)                  | Fat leads, peak sections    |
| `pad`   | Slow attack, detuned triangles             | Chords, atmosphere          |
| `bass`  | Detuned saw pair + low-pass                | Sub bass, root pulses       |

## Available Drums (via mini-notation)

| Name | Sound       | Typical Pattern          |
|------|-------------|--------------------------|
| `bd` | Kick drum   | `bd*4` (four-on-floor)   |
| `sn` | Snare       | `~ sn ~ sn`             |
| `hh` | Hi-hat      | `hh*8` or `~ hh ~ hh`   |
| `oh` | Open hi-hat | `oh*2` (cymbal wash)     |
| `cp` | Clap        | `cp(3,8)` (euclidean)    |

## Voiceover / Narration

The `say` field on each section generates text-to-speech that plays over the music. It's timed to speak `voice_lead` seconds BEFORE the section starts — so the voice leads into the change.

```yaml
voice: Samantha       # any macOS voice
voice_lead: 2.0       # speak 2 seconds before the change hits
```

Override from command line:
```bash
python songfile.py song.yaml --voice Alex --lead 3.0
```

### Available macOS Voices

Run `say -v ?` to see all. Some good ones:
- **Samantha** — default female, clear
- **Alex** — male, natural
- **Daniel** — British male
- **Karen** — Australian female
- **Moira** — Irish female
- **Tessa** — South African female

The `say` text doesn't have to describe what's happening musically. It can be lyrics, poetry, narration, whatever you want spoken over the music.

## Notes Format

Standard note names: `c d e f g a b` with optional sharp `#` or flat `b`, plus octave number.

```
c3    = middle C
eb3   = E-flat 3
f#4   = F-sharp 4
bb2   = B-flat 2
g1    = low G (bass territory)
c5    = high C
```

Octaves: 1 = deep bass, 2 = bass, 3 = mid, 4 = melody, 5 = high

## Song Architecture Tips

### The Build

Start sparse, add layers. This is how every great electronic track works:

```yaml
sections:
  - cycles: 8                    # 1. bare element alone
    layers: [synth + notes]

  - cycles: 8                    # 2. add rhythm
    layers: [same synth, + bd*4]

  - cycles: 8                    # 3. add texture
    layers: [same, + hats, + bass]

  - cycles: 16                   # 4. full power — ride it
    layers: [everything stacked]
```

### The Breakdown

Drop most layers, leave something atmospheric:

```yaml
  - say: "and then, silence"
    cycles: 6
    layers:
      - synth: pad
        notes: c3 eb3 g3
```

### The Rebuild

Bring layers back one by one after the breakdown. Creates tension.

### Key Choices

Pick a key and stick with it. Common ones for electronic:
- **C minor**: c eb f g ab bb (dark, classic)
- **G minor**: g bb c d eb f (trance, emotional)
- **E minor**: e g a b c d (natural, moody)
- **F minor**: f ab bb c db eb (deep, heavy)

## Examples

### Minimal Acid

```yaml
title: acid minimal
bpm: 136
voice_lead: 2.0

sections:
  - say: "acid"
    cycles: 16
    layers:
      - synth: acid
        notes: c2 c2 eb2 c2 f2 eb2 c2 bb1
        fast: 16
      - mini: "bd*4"
      - mini: "~ hh ~ hh"
```

### Ambient Pad Piece

```yaml
title: drifting
bpm: 80
voice: Moira
voice_lead: 3.0

sections:
  - say: "close your eyes"
    cycles: 12
    layers:
      - synth: pad
        notes: c3 eb3 g3

  - say: "let go"
    cycles: 12
    layers:
      - synth: pad
        notes: ab2 c3 eb3
      - synth: pluck
        notes: g4 eb4 c4 eb4
        fast: 4
```

### Full Trance Build

See `trance1_1.yaml` — the switch.angel session recreation.

### Moody Night Drive

See `midnight.yaml` — slow build in C minor with Daniel's voice.

### Starforge Origin Story

See `my_song.yaml` — the forge awakens, in E minor with Alex.

## How It Works Under the Hood

1. **YAML parsed** → sections become `(pattern, cycles)` tuples
2. **Patterns built** from `synth/notes/fast` → `fast(N, cat(atom("synth:note"), ...))` via tidal.py
3. **Mini-notation** parsed directly by tidal.py's mini-notation parser
4. **Layers stacked** with `stack()` — all play simultaneously
5. **Music rendered** to WAV by songs.py (44100Hz 16-bit mono + comb reverb)
6. **Speech generated** per section via macOS `say` → AIFF → WAV conversion
7. **Mixed** — speech samples added to music buffer at calculated timestamps
8. **Output** — single WAV file, play with `afplay`

Zero external dependencies beyond Python + macOS built-ins. PyYAML auto-installs on first run.
