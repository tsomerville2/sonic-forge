"""
generate_samples.py — Generate TTS comparison samples with all working engines

Generates the same 6 captain's log narration lines with each engine,
using multiple voices per engine where available.

Engines:
  - kokoro:    Kokoro-82M via ONNX runtime (~300MB, fastest)
  - f5tts:     F5-TTS via MLX (~1.2GB, voice cloning)
  - vibevoice: VibeVoice 1.5B via PyTorch (~3GB, diffusion TTS)
  - macos-say: macOS built-in (baseline, concatenative)

Usage:
    python LABS/pattern-engine/tts-comparison/generate_samples.py
    python LABS/pattern-engine/tts-comparison/generate_samples.py --engines kokoro f5tts
    python LABS/pattern-engine/tts-comparison/generate_samples.py --play
"""

import os
import sys
import time
import subprocess
import soundfile as sf
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../.."))

TEXTS = [
    "captain's log",
    "clone detection. ten thousand clones across seventy two repos.",
    "semantic grouping. polyglot tokens.",
    "four sound systems evaluated. they said tidal was too rigid. they were wrong.",
    "we followed switch angel. five notes became a world.",
    "the forge makes music now. end of log.",
]

# Full narration as a single block (for comparing continuous speech quality)
FULL_TEXT = " ".join(TEXTS)


# ---------------------------------------------------------------------------
# Kokoro-ONNX
# ---------------------------------------------------------------------------

def generate_kokoro():
    """Generate samples with Kokoro-82M (ONNX)."""
    import kokoro_onnx

    model_dir = os.path.join(BASE_DIR, "kokoro-models")
    out_dir = os.path.join(SAMPLES_DIR, "kokoro")
    os.makedirs(out_dir, exist_ok=True)

    kokoro = kokoro_onnx.Kokoro(
        f"{model_dir}/kokoro-v1.0.onnx",
        f"{model_dir}/voices-v1.0.bin",
    )

    # All 54 Kokoro voices across 8 languages
    voices = {
        # American English — Female
        "af_alloy": "Alloy (American female)",
        "af_aoede": "Aoede (American female)",
        "af_bella": "Bella (American female, bright)",
        "af_heart": "Heart (American female, warm)",
        "af_jessica": "Jessica (American female)",
        "af_kore": "Kore (American female)",
        "af_nicole": "Nicole (American female)",
        "af_nova": "Nova (American female)",
        "af_river": "River (American female)",
        "af_sarah": "Sarah (American female)",
        "af_sky": "Sky (American female, young)",
        # American English — Male
        "am_adam": "Adam (American male)",
        "am_echo": "Echo (American male, deep)",
        "am_eric": "Eric (American male)",
        "am_fenrir": "Fenrir (American male)",
        "am_liam": "Liam (American male)",
        "am_michael": "Michael (American male)",
        "am_onyx": "Onyx (American male)",
        "am_puck": "Puck (American male)",
        "am_santa": "Santa (American male)",
        # British English — Female
        "bf_alice": "Alice (British female)",
        "bf_emma": "Emma (British female)",
        "bf_isabella": "Isabella (British female)",
        "bf_lily": "Lily (British female)",
        # British English — Male
        "bm_daniel": "Daniel (British male)",
        "bm_fable": "Fable (British male)",
        "bm_george": "George (British male)",
        "bm_lewis": "Lewis (British male)",
        # Spanish
        "ef_dora": "Dora (Spanish female)",
        "em_alex": "Alex (Spanish male)",
        "em_santa": "Santa (Spanish male)",
        # French
        "ff_siwis": "Siwis (French female)",
        # Hindi
        "hf_alpha": "Alpha (Hindi female)",
        "hf_beta": "Beta (Hindi female)",
        "hm_omega": "Omega (Hindi male)",
        "hm_psi": "Psi (Hindi male)",
        # Italian
        "if_sara": "Sara (Italian female)",
        "im_nicola": "Nicola (Italian male)",
        # Japanese
        "jf_alpha": "Alpha (Japanese female)",
        "jf_gongitsune": "Gongitsune (Japanese female)",
        "jf_nezumi": "Nezumi (Japanese female)",
        "jf_tebukuro": "Tebukuro (Japanese female)",
        "jm_kumo": "Kumo (Japanese male)",
        # Portuguese
        "pf_dora": "Dora (Portuguese female)",
        "pm_alex": "Alex (Portuguese male)",
        "pm_santa": "Santa (Portuguese male)",
        # Chinese
        "zf_xiaobei": "Xiaobei (Chinese female)",
        "zf_xiaoni": "Xiaoni (Chinese female)",
        "zf_xiaoxiao": "Xiaoxiao (Chinese female)",
        "zf_xiaoyi": "Xiaoyi (Chinese female)",
        "zm_yunjian": "Yunjian (Chinese male)",
        "zm_yunxi": "Yunxi (Chinese male)",
        "zm_yunxia": "Yunxia (Chinese male)",
        "zm_yunyang": "Yunyang (Chinese male)",
    }

    results = []

    # Individual lines with default voice
    for i, text in enumerate(TEXTS):
        t0 = time.perf_counter()
        samples, sr = kokoro.create(text, voice="af_heart", speed=1.0)
        gen_time = time.perf_counter() - t0
        path = os.path.join(out_dir, f"line_{i}.wav")
        sf.write(path, samples, sr)
        dur = len(samples) / sr
        results.append((f"line_{i}", dur, gen_time))
        print(f"    [{i+1}/6] {dur:.1f}s in {gen_time:.1f}s — \"{text[:50]}\"")

    # Full narration with each voice
    print(f"    Voice showcase ({len(voices)} voices)...")
    for voice_id, voice_name in voices.items():
        t0 = time.perf_counter()
        samples, sr = kokoro.create(FULL_TEXT, voice=voice_id, speed=1.0)
        gen_time = time.perf_counter() - t0
        path = os.path.join(out_dir, f"full_{voice_id}.wav")
        sf.write(path, samples, sr)
        dur = len(samples) / sr
        results.append((f"full_{voice_id}", dur, gen_time))
        print(f"      {voice_name}: {dur:.1f}s in {gen_time:.1f}s")

    return results


# ---------------------------------------------------------------------------
# F5-TTS (MLX)
# ---------------------------------------------------------------------------

def generate_f5tts():
    """Generate samples with F5-TTS (MLX)."""
    from f5_tts_mlx.generate import generate

    out_dir = os.path.join(SAMPLES_DIR, "f5tts")
    os.makedirs(out_dir, exist_ok=True)

    # Voice cloning reference samples
    voices_dir = os.path.join(PROJECT_ROOT, "harvest-cache/tsomerville2/term4-wez-cx/voices")
    ref_voices = {
        "alice": (os.path.join(voices_dir, "en-Alice_woman.wav"), "Alice (cloned female)"),
        "frank": (os.path.join(voices_dir, "en-Frank_man.wav"), "Frank (cloned male)"),
    }

    results = []

    # Individual lines with default voice
    for i, text in enumerate(TEXTS):
        path = os.path.join(out_dir, f"line_{i}.wav")
        t0 = time.perf_counter()
        generate(generation_text=text, output_path=path)
        gen_time = time.perf_counter() - t0
        info = sf.info(path)
        dur = info.duration
        results.append((f"line_{i}", dur, gen_time))
        print(f"    [{i+1}/6] {dur:.1f}s in {gen_time:.1f}s — \"{text[:50]}\"")

    # Full narration with default + cloned voices
    print(f"    Voice cloning showcase...")

    # Default voice
    path = os.path.join(out_dir, "full_default.wav")
    t0 = time.perf_counter()
    generate(generation_text=FULL_TEXT, output_path=path)
    gen_time = time.perf_counter() - t0
    info = sf.info(path)
    print(f"      Default: {info.duration:.1f}s in {gen_time:.1f}s")
    results.append(("full_default", info.duration, gen_time))

    # Cloned voices — need reference audio in mono 24kHz
    for voice_key, (ref_path, voice_name) in ref_voices.items():
        if not os.path.exists(ref_path):
            print(f"      {voice_name}: SKIP (no reference file)")
            continue

        # Convert ref to mono 24kHz for F5-TTS
        ref_converted = os.path.join(out_dir, f"_ref_{voice_key}.wav")
        subprocess.run(
            ["afconvert", "-f", "WAVE", "-d", "LEI16@24000", "-c", "1",
             ref_path, ref_converted],
            check=True, capture_output=True,
        )

        path = os.path.join(out_dir, f"full_{voice_key}.wav")
        t0 = time.perf_counter()
        try:
            generate(
                generation_text=FULL_TEXT,
                ref_audio_path=ref_converted,
                ref_audio_text="Hey Frank, did you check out the new model yet?",
                output_path=path,
            )
            gen_time = time.perf_counter() - t0
            info = sf.info(path)
            print(f"      {voice_name}: {info.duration:.1f}s in {gen_time:.1f}s")
            results.append((f"full_{voice_key}", info.duration, gen_time))
        except Exception as e:
            print(f"      {voice_name}: FAILED ({e})")

        if os.path.exists(ref_converted):
            os.remove(ref_converted)

    return results


# ---------------------------------------------------------------------------
# VibeVoice
# ---------------------------------------------------------------------------

def generate_vibevoice():
    """Generate samples with VibeVoice 1.5B."""
    import torch
    from vibevoice.modular.modeling_vibevoice_inference import (
        VibeVoiceForConditionalGenerationInference,
    )
    from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor

    MODEL_ID = "microsoft/VibeVoice-1.5B"
    voices_dir = os.path.join(PROJECT_ROOT, "harvest-cache/tsomerville2/term4-wez-cx/voices")
    out_dir = os.path.join(SAMPLES_DIR, "vibevoice")
    os.makedirs(out_dir, exist_ok=True)

    voice_samples = {
        "alice": os.path.join(voices_dir, "en-Alice_woman.wav"),
        "frank": os.path.join(voices_dir, "en-Frank_man.wav"),
    }

    print("    Loading VibeVoice model (1.5B)...")
    processor = VibeVoiceProcessor.from_pretrained(MODEL_ID)
    model = VibeVoiceForConditionalGenerationInference.from_pretrained(
        MODEL_ID, torch_dtype=torch.float32, attn_implementation="sdpa",
    )
    model = model.to("mps")
    model.eval()
    model.set_ddpm_inference_steps(20)

    results = []

    def _generate(text, wav_path, voice_key="alice"):
        script = f"Speaker 0: {text}\n"
        encoded = processor(
            text=[script],
            voice_samples=[[voice_samples[voice_key]]],
            padding=True, return_tensors="pt", return_attention_mask=True,
        )
        for key, value in encoded.items():
            if torch.is_tensor(value):
                encoded[key] = value.to("mps")

        outputs = model.generate(
            **dict(encoded), cfg_scale=3.0, tokenizer=processor.tokenizer,
            is_prefill=True, return_speech=True, verbose=False, max_length_times=2.0,
        )
        if not outputs.speech_outputs or outputs.speech_outputs[0] is None:
            return 0.0
        audio = outputs.speech_outputs[0].detach().cpu()
        processor.save_audio(audio, output_path=wav_path)
        return audio.shape[-1] / 24000.0

    # Individual lines
    for i, text in enumerate(TEXTS):
        path = os.path.join(out_dir, f"line_{i}.wav")
        t0 = time.perf_counter()
        dur = _generate(text, path)
        gen_time = time.perf_counter() - t0
        results.append((f"line_{i}", dur, gen_time))
        print(f"    [{i+1}/6] {dur:.1f}s in {gen_time:.1f}s — \"{text[:50]}\"")

    # Full narration with each voice
    print("    Voice showcase (alice, frank)...")
    for voice_key in ["alice", "frank"]:
        path = os.path.join(out_dir, f"full_{voice_key}.wav")
        t0 = time.perf_counter()
        dur = _generate(FULL_TEXT, path, voice_key)
        gen_time = time.perf_counter() - t0
        print(f"      {voice_key}: {dur:.1f}s in {gen_time:.1f}s")
        results.append((f"full_{voice_key}", dur, gen_time))

    return results


# ---------------------------------------------------------------------------
# macOS say
# ---------------------------------------------------------------------------

def generate_macos_say():
    """Generate samples with macOS built-in say command."""
    out_dir = os.path.join(SAMPLES_DIR, "macos-say")
    os.makedirs(out_dir, exist_ok=True)

    voices = {
        # Standard human voices
        "Samantha": "Samantha (default female)",
        "Alex": "Alex (male)",
        "Daniel": "Daniel (British male)",
        "Moira": "Moira (Irish female)",
        "Karen": "Karen (Australian female)",
        "Rishi": "Rishi (Indian male)",
        "Tessa": "Tessa (South African female)",
        "Fred": "Fred (classic male)",
        "Kathy": "Kathy (classic female)",
        # Robotic / Novelty
        "Albert": "Albert (old-school robot)",
        "Bad News": "Bad News (gloomy robot)",
        "Bahh": "Bahh (sheep robot)",
        "Bells": "Bells (bell-tone speech)",
        "Boing": "Boing (bouncy robot)",
        "Bubbles": "Bubbles (underwater)",
        "Cellos": "Cellos (cello instrument voice)",
        "Good News": "Good News (chipper robot)",
        "Jester": "Jester (silly)",
        "Junior": "Junior (child robot)",
        "Organ": "Organ (pipe organ voice)",
        "Ralph": "Ralph (gruff robot)",
        "Superstar": "Superstar (dramatic)",
        "Trinoids": "Trinoids (alien)",
        "Whisper": "Whisper (whispered speech)",
        "Wobble": "Wobble (wobbly robot)",
        "Zarvox": "Zarvox (sci-fi robot)",
        # German
        "Anna": "Anna (German female)",
        # Character families (English US)
        "Eddy (English (US))": "Eddy (character voice)",
        "Flo (English (US))": "Flo (character voice)",
        "Grandma (English (US))": "Grandma (character voice)",
        "Grandpa (English (US))": "Grandpa (character voice)",
        "Reed (English (US))": "Reed (character voice)",
        "Rocko (English (US))": "Rocko (character voice)",
        "Sandy (English (US))": "Sandy (character voice)",
        "Shelley (English (US))": "Shelley (character voice)",
    }

    results = []

    # Individual lines with default voice
    for i, text in enumerate(TEXTS):
        path = os.path.join(out_dir, f"line_{i}.wav")
        aiff = path + ".aiff"
        t0 = time.perf_counter()
        subprocess.run(["say", "-v", "Samantha", "-o", aiff, text],
                       check=True, capture_output=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", aiff, path],
                       check=True, capture_output=True)
        os.remove(aiff)
        gen_time = time.perf_counter() - t0
        info = sf.info(path)
        results.append((f"line_{i}", info.duration, gen_time))
        print(f"    [{i+1}/6] {info.duration:.1f}s in {gen_time:.1f}s — \"{text[:50]}\"")

    # Full narration with each voice
    print(f"    Voice showcase ({len(voices)} voices)...")
    for voice_id, voice_name in voices.items():
        # Sanitize filename: "Bad News" → "Bad_News", "Eddy (English (US))" → "Eddy_English_US"
        safe_name = voice_id.replace(" ", "_").replace("(", "").replace(")", "").strip("_")
        path = os.path.join(out_dir, f"full_{safe_name}.wav")
        aiff = path + ".aiff"
        t0 = time.perf_counter()
        subprocess.run(["say", "-v", voice_id, "-o", aiff, FULL_TEXT],
                       check=True, capture_output=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", aiff, path],
                       check=True, capture_output=True)
        os.remove(aiff)
        gen_time = time.perf_counter() - t0
        info = sf.info(path)
        print(f"      {voice_name}: {info.duration:.1f}s in {gen_time:.1f}s")
        results.append((f"full_{safe_name}", info.duration, gen_time))

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ENGINES = {
    "kokoro": ("Kokoro-82M (ONNX)", generate_kokoro),
    "f5tts": ("F5-TTS (MLX)", generate_f5tts),
    "vibevoice": ("VibeVoice 1.5B", generate_vibevoice),
    "macos-say": ("macOS say", generate_macos_say),
}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate TTS comparison samples")
    parser.add_argument("--engines", nargs="*", default=None,
                        help=f"Engines to test (default: all). Options: {', '.join(ENGINES.keys())}")
    parser.add_argument("--play", action="store_true", help="Play full narration after each engine")
    args = parser.parse_args()

    engines = args.engines or list(ENGINES.keys())

    print(f"\n  TTS Comparison Sample Generator")
    print(f"  {len(engines)} engines, 6 narration lines + voice showcases")
    print(f"  Output: {SAMPLES_DIR}\n")

    total_results = {}

    for engine_key in engines:
        if engine_key not in ENGINES:
            print(f"  Unknown engine: {engine_key}")
            continue

        name, gen_fn = ENGINES[engine_key]
        print(f"\n{'='*50}")
        print(f"  {name}")
        print(f"{'='*50}")

        t0 = time.perf_counter()
        try:
            results = gen_fn()
            total_time = time.perf_counter() - t0
            total_results[engine_key] = {
                "name": name,
                "results": results,
                "total_time": total_time,
            }
            print(f"  Total: {total_time:.1f}s")
        except Exception as e:
            total_time = time.perf_counter() - t0
            print(f"  FAILED after {total_time:.1f}s: {e}")
            total_results[engine_key] = {"name": name, "error": str(e)}

        if args.play:
            # Play the first full narration sample
            for fname in os.listdir(os.path.join(SAMPLES_DIR, engine_key)):
                if fname.startswith("full_"):
                    print(f"  Playing {fname}...")
                    subprocess.run(["afplay", os.path.join(SAMPLES_DIR, engine_key, fname)])
                    break

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Engine':20s}  {'Lines':>8s}  {'Total':>8s}  {'Status'}")
    print(f"  {'-'*20}  {'-'*8}  {'-'*8}  {'-'*10}")
    for key in engines:
        if key in total_results:
            r = total_results[key]
            if "error" in r:
                print(f"  {r['name']:20s}  {'—':>8s}  {'—':>8s}  FAILED")
            else:
                n = len([x for x in r["results"] if x[0].startswith("line_")])
                print(f"  {r['name']:20s}  {n:>8d}  {r['total_time']:>7.1f}s  OK")

    print(f"\n  Play comparison: bash LABS/pattern-engine/tts-comparison/play-comparison.sh\n")


if __name__ == "__main__":
    main()
