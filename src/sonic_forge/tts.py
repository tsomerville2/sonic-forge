"""TTS engine abstraction — macOS say, Kokoro-82M, with optional robot FX.

Usage:
    from sonic_forge.tts import speak

    speak("Hello world")                              # macOS say, default voice
    speak("Hello world", engine="kokoro")             # Kokoro-82M, default voice
    speak("Hello world", voice="af_heart")            # auto-detects kokoro from voice prefix
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

    voice = _resolve_kokoro_voice(voice)
    kokoro = _get_kokoro()
    samples, sr = kokoro.create(text, voice=voice, speed=speed)
    sf.write(wav_path, samples, sr)


# ---------------------------------------------------------------------------
# Auto-detect engine from voice name
# ---------------------------------------------------------------------------

# Kokoro voice prefixes: af_, am_, bf_, bm_, ef_, em_, ff_, hf_, hm_, if_, im_, jf_, jm_, pf_, pm_, zf_, zm_
_KOKORO_PREFIXES = {"af_", "am_", "bf_", "bm_", "ef_", "em_", "ff_",
                     "hf_", "hm_", "if_", "im_", "jf_", "jm_",
                     "pf_", "pm_", "zf_", "zm_"}

# Friendly name → kokoro voice ID lookup (case-insensitive)
_KOKORO_NAME_MAP = {
    "alloy": "af_alloy", "aoede": "af_aoede", "bella": "af_bella",
    "heart": "af_heart", "jessica": "af_jessica", "kore": "af_kore",
    "nicole": "af_nicole", "nova": "af_nova", "river": "af_river",
    "sarah": "af_sarah", "sky": "af_sky",
    "adam": "am_adam", "echo": "am_echo", "eric": "am_eric",
    "fenrir": "am_fenrir", "liam": "am_liam", "michael": "am_michael",
    "onyx": "am_onyx", "puck": "am_puck",
    "alice": "bf_alice", "emma": "bf_emma",
    "isabella": "bf_isabella", "lily": "bf_lily",
    "daniel": "bm_daniel", "fable": "bm_fable",
    "george": "bm_george", "lewis": "bm_lewis",
    "siwis": "ff_siwis",
    "xiaobei": "zf_xiaobei", "xiaoni": "zf_xiaoni",
    "xiaoxiao": "zf_xiaoxiao", "xiaoyi": "zf_xiaoyi",
    "yunjian": "zm_yunjian", "yunxi": "zm_yunxi",
    "yunxia": "zm_yunxia", "yunyang": "zm_yunyang",
    "gongitsune": "jf_gongitsune", "nezumi": "jf_nezumi",
    "tebukuro": "jf_tebukuro", "kumo": "jm_kumo",
    "nicola": "im_nicola",
}
# Names shared across languages (dora, alex, santa, alpha, beta, etc.)
# resolve to the first/most-common variant
_KOKORO_NAME_MAP.update({
    "dora": "ef_dora", "alex": "em_alex", "santa": "am_santa",
    "alpha": "hf_alpha", "beta": "hf_beta", "omega": "hm_omega", "psi": "hm_psi",
    "sara": "if_sara",
})


def _resolve_kokoro_voice(voice):
    """Resolve a friendly name like 'daniel' to 'bm_daniel'."""
    if not voice:
        return "af_heart"
    # Already a full kokoro ID
    if any(voice.startswith(p) for p in _KOKORO_PREFIXES):
        return voice
    # Try friendly name lookup (case-insensitive)
    resolved = _KOKORO_NAME_MAP.get(voice.lower())
    if resolved:
        return resolved
    # If it looks like a kokoro ID but with wrong case, try lowercase
    if "_" in voice:
        resolved = _KOKORO_NAME_MAP.get(voice.lower().split("_", 1)[-1])
        if resolved:
            return resolved
    # Give a helpful error
    raise ValueError(
        f"Unknown Kokoro voice: '{voice}'\n"
        f"  Use a full ID (e.g. bm_daniel) or just the name (e.g. daniel).\n"
        f"  Run 'sonic-forge voices --engine kokoro' to see all 54 voices."
    )


def _detect_engine(voice):
    """Guess engine from voice name."""
    if not voice:
        return "say"
    if any(voice.startswith(p) for p in _KOKORO_PREFIXES):
        return "kokoro"
    # Kokoro friendly names are lowercase (heart, daniel, alice).
    # macOS say voices are capitalized (Samantha, Daniel, Zarvox).
    # Only match kokoro if the input is already lowercase.
    if voice[0].islower() and voice.lower() in _KOKORO_NAME_MAP:
        return "kokoro"
    return "say"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def speak(text, engine=None, voice=None, rate=None, speed=1.0, fx=None,
          output_path=None, play=True, visual=None):
    """Speak text aloud. Auto-detects engine from voice name if not specified.

    Args:
        text: Text to speak.
        engine: "say" or "kokoro". Auto-detected from voice if omitted.
        voice: Voice name. Defaults: Samantha (say), af_heart (kokoro).
        rate: Words per minute (macOS say only).
        speed: Speed multiplier (kokoro only).
        fx: Robot effect to apply: helmet, intercom, droid, ringmod, bitcrush.
        output_path: Save WAV to this path instead of a temp file.
        play: If True, play the audio after generating.
        visual: Talking head spec: "droid", "alien:pixel", "human:pixel:nes".

    Returns:
        Path to the generated WAV file (if output_path set).
    """
    if not engine:
        engine = _detect_engine(voice)

    if not voice:
        voice = "af_heart" if engine == "kokoro" else "Samantha"

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
        else:
            _say_to_wav(text, wav_path, voice=voice, rate=rate)

        # Apply robot FX if requested
        if fx:
            wav_path = _apply_fx(wav_path, fx)

        if play:
            if visual:
                _play_with_visual(wav_path, text, visual)
            else:
                subprocess.run(["afplay", wav_path])

        if keep_file:
            return wav_path
    finally:
        if not keep_file and os.path.exists(wav_path):
            os.remove(wav_path)

    return None


def _play_with_visual(wav_path, text, visual_spec):
    """Play audio with talking head animation."""
    parts = visual_spec.split(":")
    char_name = parts[0] if parts else "droid"
    style = parts[1] if len(parts) > 1 else "ascii"
    palette = parts[2] if len(parts) > 2 else "nes"

    try:
        from sonic_forge.talking_heads import animate_character
        animate_character(wav_path, char_name=char_name, text=text,
                          style=style, palette_name=palette)
    except Exception:
        # Fallback: just play audio normally
        subprocess.run(["afplay", wav_path])


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


def generate_to_wav(text, wav_path, engine=None, voice=None, rate=None, speed=1.0):
    """Generate speech to a WAV file without playing. For use in mix pipelines."""
    if not engine:
        engine = _detect_engine(voice)
    if not voice:
        voice = "af_heart" if engine == "kokoro" else "Samantha"

    if engine == "kokoro":
        _kokoro_to_wav(text, wav_path, voice=voice, speed=speed)
    else:
        _say_to_wav(text, wav_path, voice=voice, rate=rate)
