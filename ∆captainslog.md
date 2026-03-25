---
ship: sonic-forge
topics:
  - origin
  - switch-angel
  - tidal-cycles
  - release
  - pypi
  - tui
  - bytebeat
  - engine
  - python
  - kokoro
  - tts
  - voices
  - yaml
  - format
  - sharing
  - ollama
  - llm
  - granite4
  - bakeoff
  - gemma3
  - tiering
  - prompting
  - technique
  - claude
  - sonic-forge
  - ace-step
  - vocals
  - sft
  - turbo
  - music-generation
  - thinking
  - lm
  - audio-codes
  - api
  - endpoints
  - parameters
  - models
  - base
  - capabilities
  - singing
  - bark
  - macos
  - voice
  - acappella
  - mixing
  - stems
  - song-generation
  - timing
  - bug
  - pr-241
  - lyrics
  - dit
  - startup
  - commands
  - reference
entries:
  - date: '2026-03-13'
    stardate: '2026.72'
    type: note
    impact: medium
    title: 'ACE-Step startup: full command reference'
  - date: '2026-03-13'
    stardate: '2026.72'
    type: note
    impact: medium
    title: 'PR #241 ghost bug: lyrics not passed from LM to DiT'
  - date: '2026-03-13'
    stardate: '2026.72'
    type: discovery
    impact: medium
    title: 'Europop model bakeoff: 8 LLMs writing songs'
  - date: '2026-03-13'
    stardate: '2026.72'
    type: discovery
    impact: medium
    title: 'ACE-Step a cappella works: isolated vocals for mixing'
  - date: '2026-03-13'
    stardate: '2026.72'
    type: discovery
    impact: medium
    title: 'Singing voice research: exhaustive 2026 landscape'
  - date: '2026-03-13'
    stardate: '2026.72'
    type: discovery
    impact: high
    title: 'ACE-Step model zoo: turbo vs SFT vs base capabilities'
  - date: '2026-03-13'
    stardate: '2026.72'
    type: discovery
    impact: medium
    title: 'ACE-Step API: correct endpoints and parameter names'
  - date: '2026-03-13'
    stardate: '2026.72'
    type: breakthrough
    impact: high
    title: 'ACE-Step vocal recipe: thinking=false is critical'
  - date: '2026-03-13'
    stardate: '2026.72'
    type: breakthrough
    impact: high
    title: 'ACE-Step vocals SOLVED: SFT model, not turbo'
  - date: '2026-03-13'
    stardate: '2026.71'
    type: breakthrough
    impact: high
    title: 'YAML bakeoff complete: claude -p haiku is only model with 0 YAML errors'
  - date: '2026-03-13'
    stardate: '2026.71'
    type: breakthrough
    impact: high
    title: 'gemma3:1b prompting technique — describe format, never show example JSON'
  - date: '2026-03-13'
    stardate: '2026.71'
    type: discovery
    impact: high
    title: Ollama model tier list for structured JSON briefings
  - date: '2026-03-13'
    stardate: '2026.71'
    type: discovery
    impact: high
    title: 'Ollama model bakeoff: granite4:latest vs granite4:3b are different models'
  - date: '2026-03-12'
    stardate: '2026.71'
    type: note
    impact: medium
    title: YAML is the right song format
  - date: '2026-03-12'
    stardate: '2026.71'
    type: discovery
    impact: medium
    title: Kokoro-82M neural TTS is incredible
  - date: '2026-03-12'
    stardate: '2026.71'
    type: discovery
    impact: high
    title: Bytebeat pattern engine works
  - date: '2026-03-12'
    stardate: '2026.71'
    type: breakthrough
    impact: high
    title: 'v0.6.0 shipped to PyPI — 27 tracks, 10 commands'
  - date: '2026-03-12'
    stardate: '2026.71'
    type: breakthrough
    impact: high
    title: Project born from Switch.Angel
---

## 2026-03-13 - ACE-Step startup: full command reference [MEDIUM IMPACT]

**Type:** note

Quick reference for ACE-Step vocal generation on Apple Silicon: (1) Install: git clone clockworksquirrel/ace-step-apple-silicon, uv sync (requires Python 3.11). (2) Download SFT model: uv run python -c 'from acestep.model_downloader import download_submodel, get_checkpoints_dir; download_submodel("acestep-v15-sft", get_checkpoints_dir())'. (3) Start API: ACESTEP_CONFIG_PATH=acestep-v15-sft uv run acestep-api --port 8001. (4) Generate: POST /release_task with {prompt: 'genre, solo [gender] vocalist singing clearly, instruments', lyrics: '[Verse]\nlyrics here', vocal_language: 'en', audio_duration: 30, inference_steps: 50, guidance_scale: 7.0, batch_size: 4, thinking: false}. (5) Poll: POST /query_result with {task_id_list: ['id']}. (6) Audio cached in .cache/acestep/tmp/api_audio/*.mp3. (7) Optional MPS stability: export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

---

## 2026-03-13 - PR #241 ghost bug: lyrics not passed from LM to DiT [MEDIUM IMPACT]

**Type:** note

ACE-Step had a core bug (PR #241, fixed Feb 7 2026) where LM-generated lyrics were not passed from Phase 1 (language model) to Phase 2 (DiT diffusion model). Without that conditioning, DiT had no vocal signal and produced instrumentals. The clockworksquirrel Apple Silicon fork includes this fix. A separate bug (issue #200, fixed in #207): SFT model in service mode was initialized with turbo defaults — max steps capped at 20 instead of 200. The fork also has an auto-applied CFG patch (patches/sft_cfg_fix.py) that fixes repeated CFG doubling in the non-cover path. These bugs are why searching GitHub issues was essential — the code alone didn't reveal these historical fixes.

---

## 2026-03-13 - Europop model bakeoff: 8 LLMs writing songs [MEDIUM IMPACT]

**Type:** discovery

Tested 8 models writing europop YAML songs for sonic-forge rendering. Timing: claude-haiku 7.2s, claude-sonnet 23.1s, claude-opus-4.5 10.8s, claude-opus-4.6 11.9s (best writing — 'neon cathedral'), gemma3:4b 1.2s, qwen3.5:4b 2.4s (needs think:false), qwen3.5:9b 16.3s (needed 2 fixes — invented note names fa3/ac3), gemma3n:e4b 12.1s (needed 1 fix — wrong euclidean notation args). All rendered to WAV in bakeoff-songs/. Key finding: opus 4.6 writes the most creative lyrics, gemma3:4b is fastest for iteration, haiku is the best cost/quality ratio.

---

## 2026-03-13 - ACE-Step a cappella works: isolated vocals for mixing [MEDIUM IMPACT]

**Type:** discovery

ACE-Step can generate pure vocals (no instruments) by setting caption to 'a cappella, solo [gender] voice singing, no instruments, no accompaniment, dry recording, close microphone'. This produces isolated vocal stems that could be mixed with sonic-forge bytebeat instrumentals or other backing tracks. Alternative approach: use demucs (Meta's vocal separator) to strip instruments from a full ACE-Step mix. demucs not currently installed but available via pip.

---

## 2026-03-13 - Singing voice research: exhaustive 2026 landscape [MEDIUM IMPACT]

**Type:** discovery

Exhaustive search for cheap/fast singing TTS on Mac (2026-03-13): (1) macOS TUNE embedded commands are DEAD on macOS 26 Tahoe — say reads markup literally. (2) macOS novelty voices (Cellos, Good News, Bells, Trinoids) sing fixed hardcoded melodies — rate-controllable but melody not programmable. (3) Kokoro TTS: 82M params, 54 voices, fast CPU — NO pitch/melody control whatsoever. API is text+voice+speed only. Voice blending possible but doesn't enable singing. (4) Bark: real singing via ♪ lyrics ♪ notation, ~90s per 13s clip on Mac, inconsistent quality, sometimes switches to spoken word mid-clip. (5) ACE-Step 1.5: the winner. True text-to-singing. Generates melody, rhythm, AND sung vocals together. SFT model required for vocals. ~30s per 30s track. This is the Suno replacement.

---

## 2026-03-13 - ACE-Step model zoo: turbo vs SFT vs base capabilities [HIGH IMPACT]

**Type:** discovery

ACE-Step 1.5 has multiple DiT models in the registry (model_downloader.py SUBMODEL_REGISTRY): acestep-v15-turbo (default, 8 steps, no CFG, fast drafts, instrumentals-only effectively), acestep-v15-sft (50 steps, CFG enabled, vocal generation works, ~30s/track on MPS), acestep-v15-base (does NOT support LM at all), acestep-v15-turbo-shift1, acestep-v15-turbo-shift3, acestep-v15-turbo-continuous. The main model download only includes turbo. SFT must be downloaded separately. LM models: 0.6B, 1.7B (default), 4B. The 4B is auto-selected on 27GB unified memory. MLX backend used on Apple Silicon for LM inference.

---

## 2026-03-13 - ACE-Step API: correct endpoints and parameter names [MEDIUM IMPACT]

**Type:** discovery

The ACE-Step API (clockworksquirrel fork) does NOT use /v1/generate. The correct flow: POST /release_task to submit a job (returns task_id), then POST /query_result with {task_id_list: [id]} to poll results. Key parameter names: 'prompt' (not caption), 'lyrics', 'audio_duration' (not duration), 'inference_steps', 'guidance_scale', 'vocal_language'. The API determines instrumental mode from lyrics content via _is_instrumental() — empty lyrics = instrumental. Model selection via ACESTEP_CONFIG_PATH env var (default: acestep-v15-turbo). Multi-model support via ACESTEP_CONFIG_PATH2/3.

---

## 2026-03-13 - ACE-Step vocal recipe: thinking=false is critical [HIGH IMPACT]

**Type:** breakthrough

Even with the SFT model, vocals did NOT appear when thinking=true. The LM generates audio codes that condition the DiT, but these codes appear to bias the model toward instrumental arrangements. Setting thinking=false skips LM audio code generation and lets the DiT handle lyric conditioning directly from the text. The working recipe: SFT model + 50 steps + CFG 7.0 + thinking=false + use_cot_caption=false + use_cot_language=false. Caption must include explicit vocal descriptors like 'solo male vocalist singing clearly' — generic terms like 'with vocals' are too vague. Lyrics need [Verse]/[Chorus] tags with 6-10 syllables per line. Batch 2-4 and pick best — vocal emergence has randomness.

---

## 2026-03-13 - ACE-Step vocals SOLVED: SFT model, not turbo [HIGH IMPACT]

**Type:** breakthrough

After hours of debugging why ACE-Step 1.5 produced only instrumentals despite correct lyrics, the root cause was identified: the turbo model (acestep-v15-turbo) is architecturally incapable of vocal generation. It uses only 8 diffusion steps with NO classifier-free guidance (CFG). CFG is the primary mechanism that makes the model follow lyric/caption conditioning. Without it, the DiT generates whatever is statistically easiest — instrumentals. The fix: switch to the SFT model (acestep-v15-sft) which uses 50 steps with CFG enabled (guidance_scale=7.0). Download via the model_downloader registry. Start API with ACESTEP_CONFIG_PATH=acestep-v15-sft. The clockworksquirrel Apple Silicon fork auto-applies a CFG bugfix patch on SFT load.

---

## 2026-03-13 - YAML bakeoff complete: claude -p haiku is only model with 0 YAML errors [HIGH IMPACT]

**Type:** breakthrough

Full YAML song writing bakeoff across 3 providers. claude -p haiku: 2/2 perfect renders, zero invented keys, smart musical choices (72 BPM ambient, 137 trance), 14.5s avg. gemma3:4b: 1/2 clean (invented synth:synth in dark ambient), 4.7s avg. qwen3.5:4b no-think: 1/2 clean (invented bass:saw key in acid trance), 8.9s avg. For JSON briefings all 3 are reliable. claude -p writes best but costs 6.7s. gemma3:4b is 1.2s warm. qwen3.5 is 2.4s. Current code order: claude-p first, gemma3:4b as Ollama default. The 14s YAML tradeoff is real — worth exploring if Ollama models can be prompted better for YAML. See LABS/forge-reports/ollama-bakeoff-2026-03-13.md for full data.

---

## 2026-03-13 - gemma3:1b prompting technique — describe format, never show example JSON [HIGH IMPACT]

**Type:** breakthrough

gemma3:1b is a pattern copier. If you show example JSON like {"sections":["...","..."]}, it generates 3-5 complete JSON objects (variations on the pattern). The fix: DESCRIBE the format instead of demonstrating it. 'You are a JSON API. Output a single JSON object with two keys: title (string) and sections (array of 4 short strings).' This produces clean single-object JSON 4/4 times tested. Alternative that also works: skip JSON entirely, ask for 'Write 4 short sentences, one per line, no other text' — 4/4 clean output. The principle: small models copy what they see. Describe, don't demonstrate.

---

## 2026-03-13 - Ollama model tier list for structured JSON briefings [HIGH IMPACT]

**Type:** discovery

Tier 1 (reliable JSON, good writing): gemma3:4b (best writer, ~4s, wraps in markdown fence which _coerce_json handles), granite4:latest (most consistent format, ~3.4s). Tier 2 (usable with caveats): gemma3:1b (1.5s, needs special prompting — see next entry). Tier 3 (unusable for structured output): granite4:3b (inconsistent), granite4:1b-h (truncates mid-JSON), granite4:350m and gemma3:270m (pure echo machines that parrot the example), deepcoder:1.5b (run-on garbage), lfm2.5-thinking:1.2b (single-word fragments). qwen3.5:4b produces OK JSON but takes 120s due to thinking overhead — too slow. Everything under 2B parameters fails at structured JSON output.

---

## 2026-03-13 - Ollama model bakeoff: granite4:latest vs granite4:3b are different models [HIGH IMPACT]

**Type:** discovery

granite4:latest and granite4:3b have same param count (3.4B Q4_K_M) but different blob hashes and produce different output. granite4:latest writes full sentences consistently across 5 topics. granite4:3b degrades to 2-word fragment headers on 3/5 topics (e.g. 'Mission Accomplished' instead of 'Victory declared, mission completed with precision'). Always prefer granite4:latest. Tested with sonic-forge testmodel command across boost morale, solar storm, mission celebration, shore leave, and first contact prompts.

---

## 2026-03-12 - YAML is the right song format [MEDIUM IMPACT]

**Type:** note

Songs as YAML files means: version controllable, shareable, LLM-composable, human-readable. An LLM can read 'sonic-forge dsl' and compose original songs. Users share .yaml files and install them with 'sonic-forge install'. The format is simple enough to write by hand but expressive enough for multi-section compositions with voiceovers.

---

## 2026-03-12 - Kokoro-82M neural TTS is incredible [MEDIUM IMPACT]

**Type:** discovery

54 voices across 8 languages, runs locally via ONNX. Auto-downloads 80MB model on first use. Voice quality is stunning for a local model — especially af_heart, bm_daniel, bf_emma. Combined with robot FX (helmet, intercom, droid) you get sci-fi voiceovers that sound professional. pip install sonic-forge[kokoro] to enable.

---

## 2026-03-12 - Bytebeat pattern engine works [HIGH IMPACT]

**Type:** discovery

Pure Python bytebeat synthesis: 5 pitched synths (acid, saw, pluck, pad, bass), 6 drum sounds, Tidal/Strudel mini-notation parser with euclidean rhythms. Renders to 44100Hz 16-bit WAV. No dependencies beyond PyYAML and typer. The entire music engine is ~400 lines of Python.

---

## 2026-03-12 - v0.6.0 shipped to PyPI — 27 tracks, 10 commands [HIGH IMPACT]

**Type:** breakthrough

27 bundled tracks (8 bytebeat YAML, 11 ChucK generative, 8 templates). Interactive TUI launcher. Volume control (music_volume, voice_volume). Friendly voice names (just say 'daniel' not 'bm_daniel'). Export command. FX clarity ratings. Song creation guide in TUI. All YAML files now have commented-out reference showing every available option.

---

## 2026-03-12 - Project born from Switch.Angel [HIGH IMPACT]

**Type:** breakthrough

Watched Switch.Angel's Tidal Cycles live coding streams second by second. Recreated her acid trance session in Python bytebeat. That became the pattern engine, which became sonic-forge. She opened our eyes to generative computer music. https://www.youtube.com/@Switch-Angel

---
# Captain's Log: sonic-forge

