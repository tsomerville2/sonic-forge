# MATERIALS-BAY Plan: Extract pattern-engine to its own repo

**Date:** 2026-03-11
**Goal:** Reorganize all TTS, voice mods, music DSL, and demo work into a clean
repo structure, push to starshipagentic, harvest back into starforge cache.

## What We Have (Inventory)

### Core Music Engine (~4,100 LOC Python)
- `tidal.py` (1,072 LOC) — Bjorklund/Euclidean rhythms, mini-notation parser, 5 pitched synths, 6 drum synths, bytebeat
- `songs.py` (350 LOC) — section-based song rendering, comb-filter reverb
- `songfile.py` (339 LOC) — CLI entry point, YAML→WAV pipeline
- `templates.py` (527 LOC) — 8 genre templates (trance, lofi, cinematic, ambient, acid, hiphop, minimal, anthem)

### TTS Voice System
- `tts-comparison/generate_samples.py` — multi-engine TTS sample generator (Kokoro, F5-TTS, VibeVoice, macOS say)
- `tts-comparison/robotize.py` — 6 voice effects (ringmod, bitcrush, vocoder, droid, helmet, intercom)
- `tts-comparison/play-comparison.sh` — interactive curses comparison player
- `tts-comparison/REPORT.md` — full engine comparison report

### Demos
- `demos/` — 8 macOS say template demos + curses player
- `demos-vibevoice/` — 8 VibeVoice neural demos + curses player
- `render_vibevoice_demos.py` — VibeVoice demo renderer

### Song Specs (YAML DSL)
- `captains_log_*.yaml` — 8 genre templates as YAML specs
- `switch_angel_*.yaml` — live session reconstruction

### Generated/Cached (NOT shipped in repo)
- `tts-comparison/kokoro-models/` (~337MB ONNX models)
- `tts-comparison/samples/` (~100+ WAV files)
- `demos/*.wav`, `demos-vibevoice/*.wav`

## Proposed Repo Structure

```
starshipagentic/pattern-engine/
├── pyproject.toml              ← pip installable, CLI entry point
├── README.md                   ← generated from REPORT.md + usage
├── .gitignore                  ← *.wav, *.onnx, *.bin, __pycache__
│
├── src/
│   └── pattern_engine/
│       ├── __init__.py
│       ├── tidal.py            ← core: rhythms, synths, mini-notation, bytebeat
│       ├── songs.py            ← section renderer, reverb, mixing
│       ├── songfile.py         ← YAML→WAV CLI pipeline
│       ├── templates.py        ← 8 genre templates
│       ├── robotize.py         ← voice effect processor (helmet, droid, etc.)
│       └── cli.py              ← Typer CLI entry point
│
├── songs/                      ← YAML song specs
│   ├── captains_log_trance.yaml
│   ├── captains_log_lofi.yaml
│   ├── captains_log_cinematic.yaml
│   ├── captains_log_ambient.yaml
│   ├── captains_log_acid.yaml
│   ├── captains_log_hiphop.yaml
│   ├── captains_log_minimal.yaml
│   ├── captains_log_anthem.yaml
│   └── switch_angel_*.yaml
│
├── tts/                        ← TTS integration
│   ├── engines.py              ← multi-engine TTS wrapper (kokoro, f5, vibe, say)
│   ├── generate_samples.py     ← sample generator for comparison
│   ├── play_comparison.sh      ← interactive curses player
│   └── REPORT.md               ← engine comparison report
│
└── demos/                      ← demo scripts and players
    ├── play_demos.sh           ← macOS say demo player
    └── play_vibevoice.sh       ← VibeVoice demo player
```

## Steps to Execute

### Phase 1: MATERIALS-BAY (reorganize in place)
1. Create `LABS/MATERIALS-BAY/pattern-engine/` with the structure above
2. Copy source files, reorganize imports
3. Create `pyproject.toml` (hatchling build, `pattern-engine` CLI entry point)
4. Create `cli.py` with Typer commands: `render`, `play`, `robotize`, `tts-compare`
5. Add `__init__.py` with version
6. Update internal imports (tidal → pattern_engine.tidal, etc.)
7. Test: `pip install -e .` and verify `pattern-engine render songs/captains_log_trance.yaml` works

### Phase 2: BEAM UP (push to GitHub)
1. Use starforge's teleport module OR `gh repo create`:
   ```bash
   cd LABS/MATERIALS-BAY/pattern-engine
   git init && git add -A && git commit -m "Initial: pattern-engine — bytebeat music DSL + TTS voice system"
   gh repo create starshipagentic/pattern-engine --private --source=. --push
   ```
2. Tag: `git tag v0.1.0`
3. Verify on GitHub

### Phase 3: HARVEST (pull back into starforge cache)
1. Run `starforge harvest` — it auto-discovers new repos in starshipagentic org
2. Or targeted: add to harvest list and run single-repo harvest
3. Verify it appears in catalog with proper tags/gems

### Phase 4: MOON REGISTRATION (optional, captain's call)
1. Add to `moons.py` registry if we want starforge to depend on it
2. Add `starforge doctor --fix` support for auto-install
3. Wire into `starforge` CLI: `starforge render` → calls pattern-engine behind scenes

## Dependencies for pyproject.toml
```toml
[project]
name = "pattern-engine"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pyyaml",
    "numpy",
    "soundfile",
    "typer",
]

[project.optional-dependencies]
kokoro = ["kokoro-onnx", "onnxruntime"]
tts = ["kokoro-onnx", "onnxruntime", "f5-tts-mlx"]
vibevoice = ["vibevoice", "torch", "torchaudio"]

[project.scripts]
pattern-engine = "pattern_engine.cli:app"
```

## What Ships vs What Doesn't

**Ships (in git):**
- All Python source (~4,500 LOC)
- YAML song specs (~10KB)
- Shell scripts (players)
- REPORT.md, README.md

**Does NOT ship (gitignored):**
- WAV files (generated on demand)
- ONNX models (downloaded on first use)
- Voice model caches
- __pycache__

## Open Questions for Captain
- **Repo name:** `pattern-engine`? `sonic-forge`? `soundforge`? `bytebeat-engine`?
- **Moon or standalone?** Register as moon in starforge, or keep independent?
- **Public or private?** Start private, go public when polished?
- **CLI name:** `pattern-engine`? `sonic`? `forge-audio`?
