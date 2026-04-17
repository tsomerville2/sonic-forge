"""TTS engine abstraction — macOS say, Kokoro-82M, Edge-TTS, with optional robot FX.

Usage:
    from sonic_forge.tts import speak

    speak("Hello world")                              # macOS say, default voice
    speak("Hello world", engine="kokoro")             # Kokoro-82M, default voice
    speak("Hello world", voice="af_heart")            # auto-detects kokoro from voice prefix
    speak("Hello world", engine="edge")               # Edge-TTS, default en-US voice
    speak("Hello world", voice="te-IN-MohanNeural")   # auto-detects edge from voice pattern
    speak("Hello world", fx="helmet")                 # macOS say + helmet robot effect
    speak("Hello world", engine="kokoro", fx="droid") # Kokoro + droid effect
"""

import os
import subprocess
import tempfile
import wave
import array


# ---------------------------------------------------------------------------
# Engine: macOS say
# ---------------------------------------------------------------------------

def _say_to_wav(text, wav_path, voice="Samantha", rate=None):
    """Generate speech WAV via macOS say at 44100Hz mono."""
    aiff_path = wav_path + ".aiff"
    cmd = ["say", "-v", voice, "-o", aiff_path]
    if rate:
        cmd.extend(["-r", str(int(rate))])
    cmd.append(text)
    subprocess.run(cmd, check=True, capture_output=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100",
                    aiff_path, wav_path],
                   check=True, capture_output=True)
    os.remove(aiff_path)


# ---------------------------------------------------------------------------
# Engine: Kokoro-82M ONNX
# ---------------------------------------------------------------------------

_kokoro_instance = None

_KOKORO_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
_KOKORO_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"


def _download_kokoro_models():
    """Auto-download Kokoro ONNX model files on first use."""
    from urllib.request import urlretrieve

    dest = os.path.expanduser("~/.starforge/models/kokoro")
    os.makedirs(dest, exist_ok=True)
    model_path = os.path.join(dest, "kokoro-v1.0.onnx")
    voices_path = os.path.join(dest, "voices-v1.0.bin")

    for url, path, label in [
        (_KOKORO_MODEL_URL, model_path, "kokoro-v1.0.onnx (~37 MB)"),
        (_KOKORO_VOICES_URL, voices_path, "voices-v1.0.bin (~43 MB)"),
    ]:
        if not os.path.exists(path):
            print(f"  Downloading {label}...")
            urlretrieve(url, path)
            print(f"  Saved to {path}")

    return model_path, voices_path


def _get_kokoro():
    """Lazy-load Kokoro model (singleton)."""
    global _kokoro_instance
    if _kokoro_instance is not None:
        return _kokoro_instance

    try:
        import kokoro_onnx
    except ImportError:
        raise ImportError(
            "Kokoro not installed. Install: pip install 'sonic-forge[kokoro]'"
        )

    # Look for model files in standard locations
    search_dirs = [
        os.path.expanduser("~/.starforge/models/kokoro"),
        os.path.join(os.path.dirname(__file__), "..", "..", "kokoro-models"),
        os.path.expanduser("~/kokoro-models"),
    ]

    model_path = voices_path = None
    for d in search_dirs:
        m = os.path.join(d, "kokoro-v1.0.onnx")
        v = os.path.join(d, "voices-v1.0.bin")
        if os.path.exists(m) and os.path.exists(v):
            model_path, voices_path = m, v
            break

    if not model_path:
        # Auto-download from Hugging Face
        model_path, voices_path = _download_kokoro_models()

    _kokoro_instance = kokoro_onnx.Kokoro(model_path, voices_path)
    return _kokoro_instance


def _kokoro_to_wav(text, wav_path, voice="af_heart", speed=1.0):
    """Generate speech WAV via Kokoro-82M ONNX."""
    import soundfile as sf

    kokoro = _get_kokoro()
    samples, sr = kokoro.create(text, voice=voice, speed=speed)
    sf.write(wav_path, samples, sr)


# ---------------------------------------------------------------------------
# Engine: Edge-TTS (Microsoft Neural voices — 400+ voices, 100+ languages)
# ---------------------------------------------------------------------------

def _edge_to_wav(text, wav_path, voice="en-US-GuyNeural"):
    """Generate speech via edge-tts (Microsoft Edge Neural TTS).

    Requires: pipx install edge-tts (or pip install edge-tts)
    Produces MP3, converts to WAV for FX compatibility.
    """
    mp3_path = wav_path + ".mp3"
    cmd = ["edge-tts", "--voice", voice, "--text", text, "--write-media", mp3_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"edge-tts failed: {result.stderr}")

    # Convert MP3 → WAV for consistent pipeline (FX, mixing, etc.)
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", wav_path],
        check=True, capture_output=True,
    )
    os.remove(mp3_path)


# ---------------------------------------------------------------------------
# Voice & engine resolution — human-friendly names → full IDs
# ---------------------------------------------------------------------------

# Kokoro voice prefixes
_KOKORO_PREFIXES = {"af_", "am_", "bf_", "bm_", "ef_", "em_", "ff_",
                     "hf_", "hm_", "if_", "im_", "jf_", "jm_",
                     "pf_", "pm_", "zf_", "zm_"}

# Kokoro short names → full voice IDs
_KOKORO_SHORTNAMES = {
    "alloy": "af_alloy", "aoede": "af_aoede", "bella": "af_bella",
    "heart": "af_heart", "jessica": "af_jessica", "kore": "af_kore",
    "nicole": "af_nicole", "nova": "af_nova", "river": "af_river",
    "sarah": "af_sarah", "sky": "af_sky",
    "adam": "am_adam", "echo": "am_echo", "eric": "am_eric",
    "fenrir": "am_fenrir", "liam": "am_liam", "michael": "am_michael",
    "onyx": "am_onyx", "puck": "am_puck",
    "alice": "bf_alice", "emma": "bf_emma", "isabella": "bf_isabella",
    "lily": "bf_lily",
    "daniel": "bm_daniel", "fable": "bm_fable", "george": "bm_george",
    "lewis": "bm_lewis",
}

# Edge-TTS language catalog — human names → (locale, male_voice, female_voice)
_EDGE_LANGUAGES = {
    "english":    ("en-US", "en-US-GuyNeural",      "en-US-JennyNeural"),
    "british":    ("en-GB", "en-GB-RyanNeural",      "en-GB-SoniaNeural"),
    "telugu":     ("te-IN", "te-IN-MohanNeural",     "te-IN-ShrutiNeural"),
    "hindi":      ("hi-IN", "hi-IN-MadhurNeural",    "hi-IN-SwaraNeural"),
    "tamil":      ("ta-IN", "ta-IN-ValluvarNeural",   "ta-IN-PallaviNeural"),
    "kannada":    ("kn-IN", "kn-IN-GaganNeural",     "kn-IN-SapnaNeural"),
    "malayalam":  ("ml-IN", "ml-IN-MidhunNeural",    "ml-IN-SobhanaNeural"),
    "spanish":    ("es-ES", "es-ES-AlvaroNeural",    "es-ES-ElviraNeural"),
    "french":     ("fr-FR", "fr-FR-HenriNeural",     "fr-FR-DeniseNeural"),
    "german":     ("de-DE", "de-DE-ConradNeural",    "de-DE-KatjaNeural"),
    "italian":    ("it-IT", "it-IT-DiegoNeural",     "it-IT-ElsaNeural"),
    "portuguese": ("pt-BR", "pt-BR-AntonioNeural",   "pt-BR-FranciscaNeural"),
    "japanese":   ("ja-JP", "ja-JP-KeitaNeural",     "ja-JP-NanamiNeural"),
    "korean":     ("ko-KR", "ko-KR-InJoonNeural",    "ko-KR-SunHiNeural"),
    "chinese":    ("zh-CN", "zh-CN-YunxiNeural",     "zh-CN-XiaoxiaoNeural"),
    "arabic":     ("ar-SA", "ar-SA-HamedNeural",     "ar-SA-ZariyahNeural"),
    "russian":    ("ru-RU", "ru-RU-DmitryNeural",    "ru-RU-SvetlanaNeural"),
    "bengali":    ("bn-IN", "bn-IN-BashkarNeural",   "bn-IN-TanishaaNeural"),
    "marathi":    ("mr-IN", "mr-IN-ManoharNeural",   "mr-IN-AarohiNeural"),
    "gujarati":   ("gu-IN", "gu-IN-NiranjanNeural",  "gu-IN-DhwaniNeural"),
}

# Languages that Kokoro handles (prefer local over cloud)
_KOKORO_LANGUAGES = {
    "english", "british", "spanish", "french", "hindi",
    "italian", "japanese", "portuguese", "chinese",
}


def resolve_voice(voice=None, engine=None, lang=None):
    """Resolve human-friendly voice/lang/engine into (engine, full_voice_id).

    Examples:
        resolve_voice(voice="onyx")                → ("kokoro", "am_onyx")
        resolve_voice(voice="heart")               → ("kokoro", "af_heart")
        resolve_voice(lang="telugu")               → ("edge", "te-IN-MohanNeural")
        resolve_voice(lang="telugu", voice="female")→ ("edge", "te-IN-ShrutiNeural")
        resolve_voice(voice="te-IN-MohanNeural")   → ("edge", "te-IN-MohanNeural")
        resolve_voice(voice="af_heart")             → ("kokoro", "af_heart")
        resolve_voice(engine="say")                 → ("say", "Samantha")
    """
    # 1. If lang is specified, use it to pick engine + voice
    if lang:
        lang_key = lang.lower()
        if lang_key in _EDGE_LANGUAGES:
            _, male_v, female_v = _EDGE_LANGUAGES[lang_key]
            # Prefer kokoro for supported languages (local = faster)
            if not engine and lang_key in _KOKORO_LANGUAGES:
                engine = "kokoro"
            else:
                engine = engine or "edge"

            if engine == "edge":
                if voice and voice.lower() == "female":
                    return "edge", female_v
                elif voice and voice.lower() == "male":
                    return "edge", male_v
                elif voice and "-" in voice:
                    return "edge", voice  # full edge voice ID passed
                else:
                    return "edge", male_v  # default male

            if engine == "kokoro":
                # Pick a sensible kokoro default for the language
                lang_defaults = {
                    "english":  ("am_onyx", "af_heart"),    # (male, female)
                    "british":  ("bm_george", "bf_emma"),
                    "spanish":  ("em_alex", "ef_dora"),
                    "french":   ("ff_siwis", "ff_siwis"),   # only one voice
                    "hindi":    ("hm_omega", "hf_alpha"),
                    "italian":  ("im_nicola", "if_sara"),
                    "japanese": ("jm_kumo", "jf_alpha"),
                    "portuguese": ("pm_alex", "pf_dora"),
                    "chinese":  ("zm_yunxi", "zf_xiaoxiao"),
                }
                male_k, female_k = lang_defaults.get(lang_key, ("am_onyx", "af_heart"))
                if voice and voice.lower() == "female":
                    return "kokoro", female_k
                elif voice and voice.lower() == "male":
                    return "kokoro", male_k
                # If voice is a shortname or prefixed ID, fall through to step 3/4
                # Otherwise use male default for this language
                if not voice:
                    return "kokoro", male_k

    # 2. If voice looks like a full edge ID (xx-XX-NameNeural)
    if voice and "-" in voice and voice.endswith("Neural"):
        return "edge", voice

    # 3. If voice is a kokoro short name (heart, onyx, bella, etc.)
    if voice and voice.lower() in _KOKORO_SHORTNAMES:
        return "kokoro", _KOKORO_SHORTNAMES[voice.lower()]

    # 4. If voice has a kokoro prefix (af_heart, am_onyx, etc.)
    if voice and any(voice.startswith(p) for p in _KOKORO_PREFIXES):
        return "kokoro", voice

    # 5. Engine explicitly set
    if engine == "kokoro":
        return "kokoro", voice or "af_heart"
    if engine == "edge":
        return "edge", voice or "en-US-GuyNeural"

    # 6. Default: macOS say
    return engine or "say", voice or "Samantha"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def speak(text, engine=None, voice=None, lang=None, rate=None, speed=1.0,
          fx=None, output_path=None, play=True):
    """Speak text aloud. Auto-detects engine from voice/lang if not specified.

    Args:
        text: Text to speak.
        engine: "say", "kokoro", or "edge". Auto-detected if omitted.
        voice: Voice name — short ("onyx", "heart"), full ("af_heart"),
               edge ID ("te-IN-MohanNeural"), or gender ("male"/"female").
        lang: Language name ("telugu", "hindi", "french", etc.).
              Auto-selects the best engine for that language.
        rate: Words per minute (macOS say only).
        speed: Speed multiplier (kokoro only).
        fx: Robot effect to apply: helmet, intercom, droid, ringmod, bitcrush.
        output_path: Save WAV to this path instead of a temp file.
        play: If True, play the audio after generating.

    Returns:
        Path to the generated WAV file (if output_path set).
    """
    engine, voice = resolve_voice(voice=voice, engine=engine, lang=lang)

    # Generate to file
    keep_file = output_path is not None
    if output_path:
        wav_path = output_path
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = tmp.name
        tmp.close()

    try:
        if engine == "kokoro":
            _kokoro_to_wav(text, wav_path, voice=voice, speed=speed)
        elif engine == "edge":
            _edge_to_wav(text, wav_path, voice=voice)
        else:
            _say_to_wav(text, wav_path, voice=voice, rate=rate)

        # Apply robot FX if requested
        if fx:
            wav_path = _apply_fx(wav_path, fx)

        if play:
            subprocess.run(["afplay", wav_path])

        if keep_file:
            return wav_path
    finally:
        if not keep_file and os.path.exists(wav_path):
            os.remove(wav_path)

    return None


def _apply_fx(wav_path, effect_name):
    """Apply a robot effect to a WAV file, return path to processed file."""
    import numpy as np
    import soundfile as sf
    from sonic_forge import robotize

    data, sr = sf.read(wav_path)
    if data.ndim > 1:
        data = data.mean(axis=1)

    # Normalize to int16 range for robotize functions
    data_int = (data * 32767).astype(np.int16)

    fx_map = {
        "ringmod": robotize.ringmod,
        "bitcrush": robotize.bitcrush,
        "vocoder": robotize.vocoder_effect,
        "droid": robotize.droid,
        "helmet": robotize.helmet,
        "intercom": robotize.intercom,
    }

    fx_func = fx_map.get(effect_name)
    if not fx_func:
        raise ValueError(f"Unknown effect: {effect_name}. Available: {list(fx_map.keys())}")

    processed = fx_func(data_int, sr)

    out_path = wav_path.replace(".wav", f"_{effect_name}.wav")
    # robotize functions return normalized floats (-1.0 to 1.0), write directly
    sf.write(out_path, processed.astype(np.float64), sr)

    # Clean up original, return processed
    os.remove(wav_path)
    return out_path


def generate_to_wav(text, wav_path, engine=None, voice=None, lang=None,
                    rate=None, speed=1.0):
    """Generate speech to a WAV file without playing. For use in mix pipelines."""
    engine, voice = resolve_voice(voice=voice, engine=engine, lang=lang)

    if engine == "kokoro":
        _kokoro_to_wav(text, wav_path, voice=voice, speed=speed)
    elif engine == "edge":
        _edge_to_wav(text, wav_path, voice=voice)
    else:
        _say_to_wav(text, wav_path, voice=voice, rate=rate)
