# 2026-04-17 — Edge-TTS Integration: Third Engine, Twenty Languages, Zero Dollars

**Context:** Building HCSP training video narration for a client. They had a script with English body text but wanted some lessons in Telugu for their Indian provider audience. Kokoro — our local, high-quality TTS engine — choked on Telugu script. This diary entry captures the full investigation, the architecture decision, and the wider commercial landscape discoveries that shaped the outcome.

---

## The Trigger

The client script contained this passage:

```
మా CICD పైప్‌లైన్‌లో రెండు మోడ్‌లు ఉన్నాయి. Devలో టెస్ట్‌లు మరియు క్వాలిటీ గేట్‌లు ఉంటాయి...
```

Running it through Kokoro produced garbage audio. Reason: Kokoro-82M's voice catalog covers 8 languages — English (US+UK), Spanish, French, Hindi, Italian, Japanese, Portuguese, and Chinese. Telugu isn't in there. There's no voice for `te` locale, and the phonemizer it ships with has no rules for Telugu script.

This wasn't a bug in our code. Kokoro is deliberately a focused model. You can't just throw arbitrary Unicode at it and expect reasonable output — it silently mispronounces or produces noise for unsupported scripts.

---

## The Investigation: What Else Exists?

### Tier 1 — "Free via undocumented API"

Companies that expose TTS free via endpoints intended for their own products. Technically could be shut off or rate-limited, but currently unmonitored.

| Service | Mechanism | Languages | Risks |
|---------|-----------|-----------|-------|
| **edge-tts** | Reverse-engineered the WebSocket endpoint Microsoft Edge uses for its "Read Aloud" feature | 100+ languages, 400+ voices | Could be shut down anytime; undocumented; no SLA |
| **gTTS** (Google) | Reverse-engineered Google Translate's TTS playback endpoint | 60+ languages | Lower audio quality than Azure Neural; same shutdown risk |
| **pyttsx3** | Uses the host OS TTS (macOS `say`, Windows SAPI, Linux espeak) | Many | Not actually streaming from a service — just wraps what the OS has |

### Tier 2 — "Open source, runs locally, actually free forever"

| Service | Quality | Languages | Notes |
|---------|---------|-----------|-------|
| **Kokoro-82M** | Excellent | 8 | Our current primary. ~80MB model, runs on CPU. |
| **Coqui XTTS-v2** | Excellent | 17 incl. Hindi | Voice cloning from 6 seconds of reference audio. Parent company Coqui shut down but the model and community live on. |
| **F5-TTS** | Excellent | English + multilingual fork | Voice cloning, slightly better prosody than XTTS. We have this too — used it for one of the lesson variants. |
| **Piper** | Good | 30+ | Designed for Home Assistant; very fast, small models. |
| **IndicTTS** (AI4Bharat) | Very good | **22 Indian languages** — Telugu, Tamil, Kannada, Malayalam, Marathi, Bengali, Gujarati, Assamese, Punjabi, Odia, etc. | Indian government research org. Not a startup — won't disappear. Free forever. This is the sleeper gem. |
| **MMS-TTS** (Meta) | Decent | **1,100+ languages** | Massively Multilingual Speech. Covers languages nobody else bothers with. |
| **ChatTTS** | Good | 2 (English, Chinese) | Conversational style, good for dialogue/podcasts. |

### Tier 3 — "Freemium, free tier is real but capped"

| Service | Free tier | Paid starts at |
|---------|-----------|---------------|
| **ElevenLabs** | 10k chars/month (~10 min audio) | $5/mo |
| **Play.HT** | 12.5k chars/month | $39/mo |
| **Azure Speech** (official) | 500k chars/month neural | $16 per 1M chars |
| **Google Cloud TTS** | 1M chars/month standard + 1M neural | $16 per 1M chars |
| **Amazon Polly** | 5M chars/month for first 12 months, then smaller ongoing free allocation | $16 per 1M chars |

---

## The Market Economics: Why Everyone Gives TTS Away Now

The whole category is racing to zero on the serving layer. Here's why:

**The real cost of TTS is in training the model, not serving inference.** Training a competitive neural TTS model requires weeks of GPU time on a large multilingual speech corpus. That's a fixed, amortized cost. Once you have the model, serving one request is pennies of CPU time.

So every major vendor's strategic play now is:

- **Microsoft**: gives Edge voices away to make Edge browser's "Read Aloud" feature a selling point vs Chrome. The free endpoint is the taste — Azure Speech API is the paid product behind it.
- **Google**: gives 1M chars/month free via Cloud TTS to keep developers inside the Google Cloud ecosystem. Loss leader for broader GCP adoption.
- **Amazon**: gives Polly free for 12 months (5M chars/month) to hook enterprise AWS customers before switching them. Same playbook as giving away S3 storage credits.
- **Meta**: open-sourced MMS for 1,100 languages specifically to prevent any competitor from cornering the multilingual TTS market. Strategic defense — cheaper to release it free than to let Google dominate it.
- **AI4Bharat** (Indian Government): open-sourced IndicTTS for 22 Indian languages specifically to break foreign vendor dependency. Sovereignty play — India doesn't want healthcare, education, and government services in Indian languages to be hostage to US cloud providers.

The result: **as a developer, there is now no scenario where you need to pay for TTS.** The only reason to pay is if you need:
- SLA guarantees (uptime, response time)
- Custom voice training (clone a specific person's voice)
- SSML control (precise prosody, pronunciation, breaks)
- Enterprise compliance (HIPAA BAA, FedRAMP)
- Very high volume (>10M chars/month sustained)

None of those apply to our use case (content production, not a product feature). So free-tier everything.

---

## The Architecture Decision

Given the above, we decided on a **three-tier engine stack**:

### Tier 1: Kokoro (primary)
- **Use when:** English, or any of its 8 supported languages
- **Why:** Runs locally, zero network dependency, ~200ms latency, best quality-per-watt
- **Trade-off:** Limited language coverage

### Tier 2: Edge-TTS (fallback for unsupported languages)
- **Use when:** Telugu, Tamil, Kannada, Malayalam, Arabic, Korean, etc. — anything Kokoro doesn't have
- **Why:** 20+ languages we care about, real neural quality, completely free, no API key setup
- **Trade-off:** Cloud dependency, could be shut down by Microsoft someday

### Tier 3: IndicTTS (future safety net)
- **Use when:** If Edge-TTS ever disappears, OR if we need more Telugu/Tamil voice variety than Edge's 2-4 voices per language
- **Why:** Sovereign, open-source, local, covers all 22 Indian languages
- **Trade-off:** Requires ~2GB model download; best with GPU; not yet integrated into sonic-forge

This stack means: as long as you're doing English, we never hit the network. For Indic or other non-Western languages, we hit Microsoft. If Microsoft kills the endpoint, we have a known escape hatch (IndicTTS) ready to be wired in.

---

## The Human-Friendly Input Problem

The brutal reality of Kokoro voice IDs: `am_onyx`, `af_heart`, `bf_emma`, `te-IN-MohanNeural`. No human types those from memory.

Before this session, the CLI required you to know the full voice ID. The help text even showed `--voice heart` as an example — but there was no code mapping `heart` to `af_heart`. That example didn't work.

The user insight was: **"I'm a human, I'll never remember that voice ID. I'll be thinking 'make this in Telugu', and the CLI should figure out the rest."**

So we built the resolver around three human-friendly axes:

### Axis 1: Short voice names → full IDs
```
onyx    → am_onyx       (Kokoro American male, deep)
heart   → af_heart      (Kokoro American female, warm)
bella   → af_bella      (Kokoro American female, friendly)
george  → bm_george     (Kokoro British male)
emma    → bf_emma       (Kokoro British female)
```

### Axis 2: Language → best engine + default voice
```
--lang english   → kokoro am_onyx   (local, male default)
--lang french    → kokoro ff_siwis  (Kokoro has French)
--lang telugu    → edge te-IN-MohanNeural   (Kokoro can't, so Edge)
--lang tamil     → edge ta-IN-ValluvarNeural
--lang arabic    → edge ar-SA-HamedNeural
```

### Axis 3: Gender preference within a language
```
--lang telugu --voice female   → edge te-IN-ShrutiNeural
--lang english --voice female  → kokoro af_heart
--lang hindi --voice female    → kokoro hf_alpha
```

All three axes compose. Full edge IDs and full Kokoro IDs still work for power users and backward compatibility.

---

## The Resolver Logic

Living in `src/sonic_forge/tts.py` as the `resolve_voice()` function. Priority order:

1. **If `--lang X`:** use it to pick engine (Kokoro if supported, else Edge) + gender default. This is the most common path now.
2. **If voice looks like a full Edge ID** (`xx-XX-NameNeural` pattern): engine=edge, voice=as-given.
3. **If voice is a Kokoro shortname** (`onyx`, `heart`, `bella`, etc., looked up in `_KOKORO_SHORTNAMES` dict): engine=kokoro, voice=expanded ID.
4. **If voice has a Kokoro prefix** (`af_`, `am_`, `bf_`, `bm_`, `hf_`, etc.): engine=kokoro, voice=as-given.
5. **If `--engine` explicitly set:** use it with its default voice.
6. **Fallback:** macOS `say` with Samantha.

Order matters because of the overlap — `--lang telugu` hits rule 1 and short-circuits. `--voice te-IN-MohanNeural` alone hits rule 2. `--voice onyx` hits rule 3. `--voice af_heart` hits rule 4.

The resolver has **14 unit tests** covering every branch. All pass.

---

## What Edge-TTS Actually Is

`edge-tts` is a Python package (install via `pipx install edge-tts`) that reverse-engineers the WebSocket protocol Microsoft Edge uses for its "Read Aloud" feature.

When you open a webpage in Edge and click the speaker icon, Edge opens a WebSocket to `speech.platform.bing.com`, streams the page text, and receives audio chunks back. The package mimics that handshake — no API key, no auth, no rate limit (that's enforced client-side).

It returns MP3. We pipe that through `ffmpeg -ar 44100 -ac 1` to convert to WAV so it plays nicely with our existing pipeline (robotize FX, music mixing, talking head sync — all expect 44100Hz mono WAV).

The `_edge_to_wav()` helper in `tts.py` does exactly that:

```python
def _edge_to_wav(text, wav_path, voice="en-US-GuyNeural"):
    mp3_path = wav_path + ".mp3"
    subprocess.run(["edge-tts", "--voice", voice, "--text", text,
                    "--write-media", mp3_path], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", mp3_path,
                    "-ar", "44100", "-ac", "1", wav_path], check=True)
    os.remove(mp3_path)
```

Dead simple. No SDK dependency. Just shells out to two CLI tools.

---

## The Language Catalog We Shipped

Edge has 100+ languages available, but we curated down to the 20 most likely to come up for our use cases. Each gets a male voice and a female voice, stored as `(locale, male_voice, female_voice)` tuples in `_EDGE_LANGUAGES`:

| Language | Locale | Male | Female |
|----------|--------|------|--------|
| english | en-US | GuyNeural | JennyNeural |
| british | en-GB | RyanNeural | SoniaNeural |
| telugu | te-IN | MohanNeural | ShrutiNeural |
| hindi | hi-IN | MadhurNeural | SwaraNeural |
| tamil | ta-IN | ValluvarNeural | PallaviNeural |
| kannada | kn-IN | GaganNeural | SapnaNeural |
| malayalam | ml-IN | MidhunNeural | SobhanaNeural |
| spanish | es-ES | AlvaroNeural | ElviraNeural |
| french | fr-FR | HenriNeural | DeniseNeural |
| german | de-DE | ConradNeural | KatjaNeural |
| italian | it-IT | DiegoNeural | ElsaNeural |
| portuguese | pt-BR | AntonioNeural | FranciscaNeural |
| japanese | ja-JP | KeitaNeural | NanamiNeural |
| korean | ko-KR | InJoonNeural | SunHiNeural |
| chinese | zh-CN | YunxiNeural | XiaoxiaoNeural |
| arabic | ar-SA | HamedNeural | ZariyahNeural |
| russian | ru-RU | DmitryNeural | SvetlanaNeural |
| bengali | bn-IN | BashkarNeural | TanishaaNeural |
| marathi | mr-IN | ManoharNeural | AarohiNeural |
| gujarati | gu-IN | NiranjanNeural | DhwaniNeural |

If Edge has a language we didn't add, users can still pass the full ID via `--voice xx-XX-NameNeural` and it'll work (rule 2 in the resolver).

---

## The Kokoro Shortname Mapping

27 Kokoro English voices got short aliases. Now any of these work:

| Short | Full | Character |
|-------|------|-----------|
| onyx | am_onyx | Deep American male |
| heart | af_heart | Warm American female (our default for most narration) |
| bella | af_bella | Friendly American female |
| sarah | af_sarah | Professional American female |
| nicole | af_nicole | Polished American female |
| adam | am_adam | Steady American male |
| eric | am_eric | Approachable American male |
| michael | am_michael | Mature American male |
| fenrir | am_fenrir | Deep American male (alt to onyx) |
| george | bm_george | British male, distinguished |
| daniel | bm_daniel | British male |
| emma | bf_emma | British female, professional |
| alice | bf_alice | British female |
| ...and 14 more |  |  |

Collision handling: if a shortname would be ambiguous (e.g., "alpha" exists in both Hindi and Japanese Kokoro), it's NOT in the shortname map — you have to use the full ID. Only unambiguous short names got aliased.

---

## Cross-Language Educational Aside: Tamil vs Telugu

Picked up some domain knowledge worth preserving. These are frequently conflated by non-South-Asians, including me before this session.

- Both are **Dravidian languages** (unrelated to Hindi, which is Indo-European).
- Tamil's closest cousins: Malayalam, Kannada. Telugu is on its own branch (South-Central Dravidian).
- **They are NOT mutually intelligible.** Two native speakers cannot converse across them. Same family, but diverged thousands of years ago.
- Scripts are visually distinct: Tamil is angular/geometric (`தமிழ்`), Telugu is rounded/loopy (`తెలుగు`).
- Tamil has a ~2,300-year continuous literary tradition (one of 6 Indian languages with "classical" status). Telugu also classical, ~1,500 years of literature.
- Telugu absorbed more Sanskrit vocabulary; Tamil actively resisted Sanskrit influence and kept Dravidian roots.
- Speaker counts: Telugu ~83M, Tamil ~75M. Telugu actually bigger, but Tamil gets more global attention due to diaspora (Singapore, Malaysia, Sri Lanka).
- **For HCSP-style training content**: "South Indian" is not a language. You must ask which of the four — Tamil, Telugu, Kannada, or Malayalam. Picking wrong is a real cultural/usability error.
- Edge's `te-IN` and `ta-IN` are the two we care about most. Kokoro has neither — that's why this epic existed.

---

## Files Changed in This Session

### `src/sonic_forge/tts.py`
- Added `_edge_to_wav(text, wav_path, voice)` — shells to `edge-tts` + `ffmpeg`, produces 44100Hz mono WAV.
- Added `_KOKORO_SHORTNAMES` dict — 27 short names → full Kokoro voice IDs.
- Added `_EDGE_LANGUAGES` dict — 20 language names → (locale, male_voice, female_voice) tuples.
- Added `_KOKORO_LANGUAGES` set — which of the 20 languages Kokoro can handle (so we prefer local).
- Added `resolve_voice(voice=None, engine=None, lang=None)` function — the six-priority resolver described above.
- Updated `speak(text, engine=None, voice=None, lang=None, ...)` — added `lang` param, delegates resolution to `resolve_voice()`.
- Updated `generate_to_wav(...)` — same `lang` addition.
- Added `"edge"` dispatch branch in both `speak()` and `generate_to_wav()`.
- Updated module docstring with new usage examples.

### `src/sonic_forge/cli.py`
- Added `--lang / -l` option to `speak_cmd`.
- Pass `lang` through to `speak()` in both the visual-mode and plain-mode code paths.
- Rewrote `speak_cmd` help text with comprehensive examples covering:
  - Short voice names (`--voice onyx`)
  - Language-driven selection (`--lang telugu`)
  - Gender within language (`--lang english --voice female`)
  - Save-to-WAV for video workflows
  - All existing patterns (FX, music, visual)
- Updated `--voice` help string to describe all four input patterns.
- Updated `--engine` help string to include `edge`.
- Added `_list_edge_voices(lang_filter)` function — lists all 20 Edge languages with install-state check (`shutil.which("edge-tts")`).
- Updated `voices_cmd` to include Edge in the default listing and respond to `--engine edge`.
- Updated `voices_cmd` help text to mention `--lang telugu`, `--lang hindi`, and the Kokoro/Edge language split.

---

## End-to-End Verification

All three engines confirmed working via the `sonic-forge speak` CLI from a fresh shell:

```bash
# Telugu via Edge — Microsoft's Mohan voice
sonic-forge speak --text "మా CICD పైప్‌లైన్‌లో రెండు మోడ్‌లు ఉన్నాయి" --lang telugu -o /tmp/test-telugu.wav --no-play
# → 294KB WAV, clean Telugu audio

# Tamil via Edge — Valluvar voice
sonic-forge speak --text "வணக்கம். தமிழ் மற்றும் தெலுங்கு இரண்டும் திராவிட மொழிகள்." --lang tamil -o /tmp/tamil.wav --no-play
# → Clean Tamil audio, clearly distinct from Telugu

# Kokoro Onyx via shortname
sonic-forge speak --text "Testing the onyx voice with a short name" --voice onyx -o /tmp/test-onyx.wav --no-play
# → 140KB WAV, Onyx's deep male voice

# Kokoro Heart via --lang english --voice female
sonic-forge speak --text "This should be Kokoro Heart" --lang english --voice female -o /tmp/test-en-female.wav --no-play
# → Kokoro af_heart output
```

Resolver unit tests: 14/14 pass.

---

## What's Still Open

- **IndicTTS integration** — not wired in yet. When/if edge-tts ever breaks, this is the fallback. Would involve downloading ~2GB model, adding `_indictts_to_wav()`, and expanding `_EDGE_LANGUAGES` to route Indic languages preferentially through IndicTTS with Edge as the fallback.
- **Voice cloning path** — F5-TTS and XTTS-v2 are installed but not integrated into sonic-forge. For use cases like "clone Travis's voice and have it speak Japanese," we'd add a `--clone-from reference.wav` parameter.
- **SSML / pause control** — currently relying on em-dashes (`— — —`) to force pauses. Edge supports real SSML which would give us precise breath/pause/emphasis control. Worth adding as a future `--ssml` flag.
- **Segment-gap helper** — the HCSP video work showed we need 2-3 second silence between major sections. Currently done with ad-hoc ffmpeg concat commands. Should probably become a first-class `sonic-forge segments.yaml` input format with automatic gap insertion.

---

## The Business Lesson

The whole reason this week's work happened is that a client ran a demo, saw what was possible, and asked "can we do this in our voice, for our languages, in our LMS?" They expected a multi-month evaluation of ElevenLabs, Azure Speech, Google Cloud TTS, maybe a custom pipeline build.

What they actually need: three engines, none paid, 20+ languages, their exact lesson audio can be generated from a Markdown script in seconds. Total out-of-pocket cost: $0. Total integration effort for sonic-forge: one afternoon.

This is the kind of outcome that looks like magic to a non-technical stakeholder but is actually just the result of knowing the TTS market's race-to-zero dynamics and having the CLI infrastructure already built to compose new engines quickly. Worth remembering next time someone asks "can we do X?" in any commoditizing space — voice, images, translation, transcription, summarization. The answer is almost always "yes, and it's probably free."
