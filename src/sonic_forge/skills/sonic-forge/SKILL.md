---
name: sonic-forge
description: Voiceovers, long-form narration with a frame-accurate timing manifest, TTS voices in 20+ languages, robot/radio voice effects and code-generated music, all from the local `sonic-forge` CLI. Use when the user wants a narration or voiceover WAV, spoken audio from text, timings to line visuals up with narration (Remotion, DaVinci, ffmpeg), to pick or audition a voice, to add pauses or fix pronunciation, droid/helmet/intercom voice FX, background music or bytebeat, or a sung song.
---
<!-- managed by sonic-forge: updated automatically on upgrade; edit freely and it will be left alone -->

# sonic-forge

A Python CLI for local, offline-first speech and music. The workhorse for video is `narrate`: it turns a
script into one WAV plus `<output>.timing.json`, which gives the start and end of every paragraph and pause in
seconds, so visuals can be cut to the voice instead of guessed.

## The recipe: script → narration + timings

```bash
sonic-forge narrate script.txt narration.wav --engine kokoro --voice am_fenrir --seed 608 --pause-mode explicit
```

- `script.txt`: paragraphs separated by blank lines. One paragraph becomes one timed segment.
- `narration.wav`: 24 kHz mono. `narration.timing.json` is written next to it.
- `--seed`: identical input and seed give an identical WAV, which makes builds reproducible and cacheable.
- `--pause-mode explicit`: a `[pause: …]` marker sets the gap it sits in. Use it for new work. The default,
  `legacy`, keeps old outputs byte-identical but lets the blank-line medium pause (0.55–1.10 s) swallow
  any shorter marker.
- `-` reads the script from stdin: `cat script.txt | sonic-forge narrate - out.wav`.

### Pause markup (a line of its own, between paragraphs)

| Marker | Seconds |
|---|---|
| blank line (default) | medium, 0.55–1.10 |
| `[pause: tiny]` | 0.15–0.40 |
| `[pause: short]` | 0.30–0.68 |
| `[pause: medium]` | 0.55–1.10 |
| `[pause: long]` | 0.95–1.60 |
| `[pause: xlong]` | 1.50–2.35 |
| `[pause: 1.2]` | 1.2 ± 15 % (never below 0.1) |

Durations are drawn from these pools for natural variation, and `--seed` fixes the draw.

### timing.json

```json
{"total_duration": 64.524, "fps": 30, "total_frames": 1935, "pause_mode": "explicit",
 "segments": [{"kind": "text", "index": 0, "start": 0.0, "end": 4.21, "duration": 4.21, "text": "…"},
              {"kind": "pause", "index": 1, "start": 4.21, "end": 4.62, "duration": 0.41}]}
```

Convert to frames with `round(start * fps)`. `--fps` only changes `total_frames`.

### Pronunciation fixes

`--phonics phonics.json` takes a JSON object of whole-word replacements applied before speech, longest key
first: `{"CI/CD": "C I C D", "Kubernetes": "koo-ber-net-eez"}`.

## Voices and engines

```bash
sonic-forge voices --engine kokoro      # 54 Kokoro voices, 28 English (local, high quality)
sonic-forge voices --lang hindi         # which engines and voices speak a language
sonic-forge speak --text "Hello there" --voice onyx           # hear one now
sonic-forge speak --text "Welcome" --voice heart -o intro.wav --no-play
```

| Engine | Where | Notes |
|---|---|---|
| `kokoro` | local, any OS | Kokoro-82M (onnx). Best English. Also es, fr, hi, it, ja, pt, zh. Needs `pip install "sonic-forge[kokoro]"`; the 340 MB of weights download once to `~/.starforge/models/kokoro`. |
| `edge` | cloud, free | Microsoft neural voices, 20+ languages (Telugu, Tamil, Arabic, Korean, German…). Needs `pipx install edge-tts`. |
| `say` | macOS only | Built-in system voices, offline. The default on a Mac when no voice or language is given. |

- Short Kokoro names: `heart`, `bella` (warm/friendly female), `onyx`, `fenrir` (deep male), `george` and
  `emma` (British). Full IDs look like `af_heart` and `am_fenrir`: a = American, b = British; f/m = female/male.
- `--lang telugu` (or any language name) picks the engine and a voice for you. Kokoro cannot do Telugu; edge can.
- Off macOS, a run with no engine, voice or language uses Kokoro. Passing `--engine kokoro` makes a script
  behave the same everywhere.

## Cloned voices

Needs the clone extra (`pipx install "sonic-forge[kokoro,clone]"`). Only clone a voice whose owner agreed.

```bash
sonic-forge clone-prep sample.m4a me.wav      # 10-20 s of clear speech → clean 24 kHz reference
sonic-forge narrate script.txt out.wav --engine chatterbox --voice me.wav --seed 7 --pause-mode explicit
```
Chatterbox Turbo (MIT) runs on CPU: about 0.7 s of compute per second of speech on 16 cores (paragraphs run in
parallel processes, `--jobs`), about 3.4 s on one 8-core Mac process. Output carries an inaudible watermark.

## Voice effects

```bash
sonic-forge speak --text "Copy that" --voice fenrir --fx intercom
sonic-forge robotize voice.wav --fx helmet --fx droid -o out/
```

The effects are `helmet` (muffled), `intercom` (radio), `droid` (R2-style), `ringmod` (metallic),
`bitcrush` (lo-fi) and `vocoder` (`robotize` only).

## Music

```bash
sonic-forge beat ambient -d 60 -o bed.wav --no-play      # instrumental bed from a genre template
sonic-forge templates                                     # trance, lofi, cinematic, ambient, acid, …
sonic-forge dsl                                           # the YAML song format, to write or teach songs
sonic-forge render song.yaml -o song.wav                  # render a YAML song (add --voice/--fx for vocals)
sonic-forge catalog                                       # built-in and installed tracks
sonic-forge sing "a song about cranes" --style bluegrass -o cranes.mp3 --no-play   # ACE-Step, ~4 GB first run
```

`play` and `speak` play audio out loud (macOS `afplay`). In scripts and agents, write files with `-o` and
`--no-play`, and stop stray audio with `sonic-forge stop`.

## Good to know

- `ffmpeg` and `ffprobe` must be on PATH for `narrate`.
- Long-form tip: write plain sentences. Stacked dots and ellipses make Kokoro hum ("mmm") between words.
  `kokoro-prep` exists for short punchy reads, not for narration.
- `sonic-forge --help` and `sonic-forge <command> --help` are the full manual, with examples for every option.
- `sonic-forge --skill` prints this card. `sonic-forge --skill install` (re)installs it for every coding agent
  on the machine and shows where.
