# sonic-forge

Local speech, narration with frame-accurate timings, and music made from code, in one CLI.

- **`narrate`**: a script becomes one WAV plus `timing.json`, which gives the start and end of every paragraph and pause. You cut visuals (Remotion, DaVinci, ffmpeg) to the real voice instead of guessing. It is seedable, so the same input and seed give the same WAV.
- **`speak`**: text to speech with three engines: Kokoro-82M (local neural, any OS), Microsoft Edge neural voices (20+ languages) and macOS `say`.
- **Cloned voices**: 10–20 seconds of someone talking, and `narrate` speaks any script in that voice, locally (Chatterbox Turbo, MIT), on the GPU on Apple silicon.
- **Speech to text**: `transcribe` turns a recording into text with sentence and word times, as Whisper-style JSON (NVIDIA Parakeet on Apple silicon).
- **Voice FX**: helmet, intercom, droid, ringmod, bitcrush and vocoder.
- **Music**: bytebeat genre templates, a YAML song format, 27 bundled tracks, and sung songs via ACE-Step.
- **Built for agents too**: `sonic-forge --skill` hands any coding agent its skill card, and it installs itself for Claude Code, Codex and `~/.agents` agents.

## Install

```bash
pipx install "sonic-forge[kokoro]"     # the CLI plus the Kokoro neural voice engine (recommended)
pipx install sonic-forge               # CLI only: macOS say voices, music, FX
pipx install edge-tts                  # optional: 20+ languages via Microsoft Edge voices
pipx install "sonic-forge[kokoro,clone]"  # plus voice cloning (torch, about 2 GB)
pipx install "sonic-forge[kokoro,clone-mlx,stt-mlx]"  # Apple silicon: cloning and transcription on the GPU
```

`sonic-forge doctor` shows what an install can do (engines, the cloning backend, transcription).

On Linux, install the CPU build of torch first so pip doesn't fetch CUDA wheels:
`pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu`.

`narrate` needs `ffmpeg` and `ffprobe` on PATH. Kokoro's weights (about 340 MB) download once, on first use, to `~/.starforge/models/kokoro`.

## Narration for video

```bash
sonic-forge narrate script.txt narration.wav --engine kokoro --voice am_fenrir --seed 608 --pause-mode explicit
```

`script.txt` has paragraphs separated by blank lines. To set a pause, put a marker on a line of its own:

```text
Before you leave the room, say it back.

[pause: short]

Repeat the instruction in your own words.

[pause: xlong]

That is all it takes.
```

| Marker | Seconds |
|---|---|
| blank line (default) | medium, 0.55–1.10 |
| `[pause: tiny]` | 0.15–0.40 |
| `[pause: short]` | 0.30–0.68 |
| `[pause: medium]` | 0.55–1.10 |
| `[pause: long]` | 0.95–1.60 |
| `[pause: xlong]` | 1.50–2.35 |
| `[pause: 1.2]` | 1.2 ± 15 % |

Pauses are drawn from these pools so the voice doesn't sound metronomic, and `--seed` makes the draw reproducible.

**Use `--pause-mode explicit`.** With it, a marker sets the length of the gap it sits in. The default, `legacy`, keeps outputs from earlier versions byte-identical. In legacy mode every blank line also draws a medium pause and the longer one wins, so `[pause: short]` comes out medium.

Next to `narration.wav` you get `narration.timing.json`:

```json
{
  "total_duration": 64.524, "fps": 30, "total_frames": 1935, "pause_mode": "explicit",
  "segments": [
    {"kind": "text",  "index": 0, "start": 0.0,  "end": 4.21, "duration": 4.21, "text": "Before you leave the room, say it back."},
    {"kind": "pause", "index": 1, "start": 4.21, "end": 4.62, "duration": 0.41}
  ]
}
```

More options:
- `--phonics phonics.json` fixes pronunciation with whole-word replacements, longest key first, for example `{"CI/CD": "C I C D"}`.
- `--lang telugu` picks an engine and voice for a language.
- `-` reads the script from stdin.
- `--no-manifest` skips the timing file.

## Voices

```bash
sonic-forge voices                       # every engine
sonic-forge voices --engine kokoro       # 54 Kokoro voices, 28 of them English
sonic-forge voices --lang hindi          # who speaks Hindi
sonic-forge speak --text "Hello there" --voice onyx
sonic-forge speak --text "Welcome" --voice heart -o intro.wav --no-play
sonic-forge speak --text "Bonjour le monde" --lang french
```

| Engine | Runs | Languages |
|---|---|---|
| `kokoro` | locally on any OS (onnx) | English (US, UK), es, fr, hi, it, ja, pt, zh |
| `edge` | Microsoft cloud, free | 20+, including Telugu, Tamil, Arabic, Korean and German |
| `say` | macOS, offline | the system voices |

- **Kokoro short names:** `heart`, `bella`, `nova`, `sky` (female); `onyx`, `fenrir`, `adam`, `michael` (male); `emma`, `alice` (British female); `george`, `daniel` (British male). Full IDs look like `af_heart` and `am_fenrir`.
- **Default engine:** with no engine, voice or language given, a Mac uses `say`. Every other system uses Kokoro.

## Cloned voices

```bash
sonic-forge clone-prep phone-memo.m4a me.wav       # trim, level, 24 kHz mono, at most 20 s
sonic-forge narrate script.txt narration.wav --engine chatterbox --voice me.wav --seed 7
sonic-forge speak --text "Hello, it's me" --engine chatterbox --voice me.wav
```

- **Engine:** [Chatterbox Turbo](https://github.com/resemble-ai/chatterbox) by Resemble AI (MIT), run locally. Its weights download once from Hugging Face. Every clip carries Resemble's inaudible Perth watermark.
- **Two backends, one CLI:** with the `clone-mlx` extra on Apple silicon it runs on the GPU through [mlx-audio](https://github.com/Blaizzy/mlx-audio) (`mlx-community/chatterbox-turbo-fp16`, 2.8 GB). Everywhere else it is the PyTorch build on CPU (`clone` extra). `SONIC_FORGE_CLONE_BACKEND=mlx` or `torch` forces one. Pauses, `--seed`, levelling and the timing manifest behave the same on both. A seed gives the same audio every time on the same backend, but the two backends' audio differs.
- **The reference:** 10–20 seconds of one person speaking clearly in a quiet room. `clone-prep` refuses anything under 5 seconds.
- **Speed:** on the GPU (M2 Max), one process speaks about as fast as it talks: 0.6 to 0.9 seconds of work per second of speech, plus about 11 seconds to load. On CPU, generation is autoregressive, so threads stop helping early, and `narrate` speaks paragraphs in parallel processes instead (`--jobs`, by default one per four cores, at most four; on the GPU, one). Measured on 16 cores with 4 processes: about 0.7 seconds of compute per second of speech. One process on an 8-core Mac: about 3.4.
- **Consent:** only clone your own voice, or a voice whose owner has agreed.

## Speech to text

```bash
sonic-forge transcribe memo.m4a                     # the text, one sentence per line
sonic-forge transcribe memo.m4a --json --words      # Whisper verbose_json, with each word's times
sonic-forge transcribe memo.m4a --json -o memo.json
```

- **Engine:** NVIDIA Parakeet TDT 0.6B v2 through [parakeet-mlx](https://github.com/senstella/parakeet-mlx), on the Apple silicon GPU (`stt-mlx` extra). Its weights (2.3 GB) download once. `--model mlx-community/parakeet-tdt-0.6b-v3` hears 25 European languages.
- **The JSON** has the shape of OpenAI and Groq Whisper's `verbose_json`, so code written for hosted Whisper can switch to it: `{task, language, duration, text, model, segments: [{id, start, end, text}], words: [{word, start, end}]}`. Punctuation stays on its word.
- **Speed (M2 Max):** a 65-second recording in about 2.8 seconds and a 120-second one in about 5.7, plus about 2 seconds to load the model.

## Voice effects

```bash
sonic-forge speak --text "Copy that" --voice fenrir --fx intercom
sonic-forge robotize voice.wav --fx helmet --fx droid
```

## Music

```bash
sonic-forge                              # interactive launcher: browse and play the bundled tracks
sonic-forge beat ambient -d 60 -o bed.wav --no-play
sonic-forge templates                    # trance, lofi, cinematic, ambient, acid, hiphop, minimal, anthem, bluegrass
sonic-forge dsl                          # the YAML song format (also good for teaching an LLM to compose)
sonic-forge export acid-session          # copy a bundled song's source to remix
sonic-forge render song.yaml --play
sonic-forge sing "watching cranes move" --style bluegrass -o cranes.mp3
sonic-forge stop                         # silence everything that's playing
```

`play` and `speak` play audio aloud with macOS `afplay`; elsewhere, write a file with `-o`. ChucK tracks need `chuck` on PATH. `sing` downloads about 4 GB of ACE-Step models on first run.

## For coding agents

```bash
sonic-forge --skill                      # print the stock SKILL.md
sonic-forge --skill install              # (re)install it for every coding agent on this machine, and show where
sonic-forge --skill list                 # Skillflag-compatible listing (github.com/osolmaz/skillflag) …
sonic-forge --skill export | npx skillflag install --agent claude   # … so its installer works too
```

Every `sonic-forge` run silently installs or refreshes the card where an agent is present:
- `~/.claude/skills/sonic-forge/` (Claude Code)
- `~/.codex/skills/sonic-forge/` (Codex)
- `~/.agents/skills/sonic-forge/` (pi, omo, opencode, goose)

A copy you have edited is never overwritten. `SONIC_FORGE_NO_SKILLS=1` turns the silent install off.

## What's new in 0.12

- **Cloned voices on the Apple GPU.** `pipx install "sonic-forge[kokoro,clone-mlx,stt-mlx]"`, and `narrate --engine chatterbox` runs Chatterbox Turbo through mlx-audio instead of torch on CPU. The CLI and the output are unchanged, and every clip still carries the Perth watermark.
- **`sonic-forge transcribe`**: speech to text with Parakeet on the GPU, as Whisper-style JSON with word times.
- **`sonic-forge doctor [--json]`**: what this install can do, without loading a model.
- **Fixes for fresh installs of the `clone` extra:** it pins `setuptools<81`, because the watermarker needs `pkg_resources`. It also keeps the reference audio float32 under numpy 2, which used to fail with "expected m1 and m2 to have the same dtype". A worker process that can't load the model now fails the run with the reason, instead of hanging while multiprocessing respawns it forever.

## Python

```python
from sonic_forge.narrate import narrate
narrate("script.txt", "narration.wav", engine="kokoro", voice="am_fenrir", seed=608, pause_mode="explicit")
```

`sonic-forge --help` and `sonic-forge COMMAND --help` are the full manual, with examples for every option.
