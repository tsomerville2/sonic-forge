# TTS Engine Comparison Report

**Date:** 2026-03-10
**Platform:** macOS Apple Silicon (MPS), Python 3.14
**Test text:** Captain's log narration (6 lines, ~15s spoken)

## Engines Tested

| Engine | Model Size | Runtime | Voices | Speed (RTF) | Quality | Status |
|--------|-----------|---------|--------|-------------|---------|--------|
| **Kokoro-82M** | ~300MB | ONNX | 54 built-in | **0.15x** (6.7x faster than real-time) | Clean, professional | WORKS |
| **F5-TTS** | ~1.2GB | MLX | Default + cloning | 1.5x (slower than real-time) | Deep, human | WORKS |
| **VibeVoice 1.5B** | ~3GB | PyTorch/MPS | 2 cloned (Alice, Frank) | 2.4x (slower than real-time) | Neural, natural prosody | WORKS |
| **macOS say** | 0MB | System | 5+ built-in | **0.04x** (instant) | Concatenative, robotic | WORKS |
| **ChatTTS** | ~1.1GB | PyTorch | Random/seeded | — | — | BROKEN (transformers 5.0) |
| **Kokoro via mlx-audio** | ~300MB | MLX | 54 built-in | — | — | BROKEN (Python 3.14/spacy) |

## Speed Comparison (full narration, ~15s of speech)

| Engine | Generation Time | Real-Time Factor | Load Time |
|--------|----------------|------------------|-----------|
| macOS say | **0.7s** | 0.04x | 0s |
| Kokoro-ONNX | **2.9s** | 0.15x | 0.4s |
| F5-TTS | 31s | 1.5x | ~3s |
| VibeVoice | 92s | ~6x | ~5s |

## Quality Assessment

### Kokoro-82M (ONNX) — RECOMMENDED for most uses
- **Vibe:** Clean, professional, broadcast-quality
- **Pros:** Blazing fast (6.7x real-time), 54 voices across 4 languages, tiny model
- **Cons:** Slightly "perfect" — lacks the imperfections that make speech feel human
- **Best voices:** af_heart (warm female), am_adam (clear male), bf_emma (British female)
- **Best for:** Song narration, CLI output, any use needing fast turnaround

### F5-TTS (MLX) — Best for human feel
- **Vibe:** Deeply human, natural cadence
- **Pros:** Most natural-sounding speech, MLX-native (Apple Silicon optimized)
- **Cons:** 1.5x slower than real-time, voice cloning needs exact transcript match
- **Voice cloning:** FAILED with our Alice/Frank samples (transcript mismatch)
- **Default voice:** Excellent quality, conversational tone
- **Best for:** When quality matters more than speed

### VibeVoice 1.5B — Best for speaker cloning
- **Vibe:** Neural, natural prosody, multi-speaker
- **Pros:** True speaker cloning from WAV samples, multi-speaker dialogue
- **Cons:** Slowest (6x real-time), largest model (3GB), requires PyTorch
- **Note:** transformers version conflict with mlx-audio — can't coexist in same venv
- **Best for:** When you need a specific voice character

### macOS say — Baseline
- **Vibe:** Robotic but reliable
- **Pros:** Instant, zero setup, multiple voices, always available
- **Cons:** Obviously synthetic, limited expressiveness
- **Best for:** Quick prototyping, when speed is everything

## Dependency Conflicts

The main challenge is **transformers version conflicts**:
- VibeVoice requires `transformers==4.51.3`
- mlx-audio (Kokoro via MLX) installed `transformers==5.0.0rc3`
- ChatTTS uses `encode_plus` which was removed in transformers 5.0

**Solution used:** Kokoro-ONNX (no transformers dependency) + downgrade transformers to 4.51.3 for VibeVoice.

### Engines that didn't work on Python 3.14:
- **Kokoro via mlx-audio:** Requires spacy → pydantic v1 → broken on Python 3.14
- **ChatTTS:** Uses `BertTokenizer.encode_plus` removed in transformers 5.0

## Samples Generated

```
tts-comparison/samples/
├── kokoro/           # 7 full voices + 6 individual lines
│   ├── full_af_heart.wav    (warm female)
│   ├── full_af_bella.wav    (bright female)
│   ├── full_af_sky.wav      (young female)
│   ├── full_am_adam.wav     (male)
│   ├── full_am_echo.wav     (deep male)
│   ├── full_bf_emma.wav     (British female)
│   ├── full_bm_daniel.wav   (British male)
│   └── line_0..5.wav        (individual narration lines)
├── f5tts/            # 1 full voice + 6 individual lines
│   ├── full_default.wav     (default voice)
│   └── line_0..5.wav
├── vibevoice/        # 2 full voices + 6 individual lines
│   ├── full_alice.wav       (cloned female)
│   ├── full_frank.wav       (cloned male)
│   └── line_0..5.wav
└── macos-say/        # 5 full voices + 6 individual lines
    ├── full_Samantha.wav    (default female)
    ├── full_Alex.wav        (male)
    ├── full_Daniel.wav      (British male)
    ├── full_Moira.wav       (Irish female)
    ├── full_Karen.wav       (Australian female)
    └── line_0..5.wav
```

## How to Listen

### Interactive comparison player:
```bash
bash LABS/pattern-engine/tts-comparison/play-comparison.sh
```
- LEFT/RIGHT: switch engine
- UP/DOWN: select voice
- ENTER/SPACE: play
- TAB: toggle between voice showcase and individual lines
- 'a': play all engines back-to-back
- 'q': quit

### VibeVoice template demos (separate, with music):
```bash
bash LABS/pattern-engine/demos-vibevoice/play-demos.sh
```

### macOS say template demos (separate, with music):
```bash
bash LABS/pattern-engine/demos/play-demos.sh
```

### Regenerate all samples:
```bash
python LABS/pattern-engine/tts-comparison/generate_samples.py
python LABS/pattern-engine/tts-comparison/generate_samples.py --engines kokoro f5tts  # specific engines
```

## Recommendation

**For the pattern engine / songfile.py integration:**

1. **Default TTS:** Kokoro-82M via ONNX — fast enough for real-time song narration, high quality, 54 voices
2. **Premium TTS:** F5-TTS — when you want the most human-sounding narration and don't mind the wait
3. **Speaker cloning:** VibeVoice — when you need a specific voice character (but note the venv conflict)
4. **Quick prototyping:** macOS say — instant, always available, good enough for testing

A `--tts` flag in songfile.py could switch between engines:
```bash
python songfile.py song.yaml --tts kokoro --voice af_heart
python songfile.py song.yaml --tts f5tts
python songfile.py song.yaml --tts say --voice Daniel    # current default
```

## Install Commands

```bash
# Kokoro-ONNX (recommended)
pip install kokoro-onnx onnxruntime soundfile
# Download models (~337MB one-time):
curl -sLO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -sLO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

# F5-TTS (MLX)
pip install f5-tts-mlx

# VibeVoice (needs transformers==4.51.3)
pip install vibevoice torch torchaudio

# macOS say — built-in, no install needed
```
