"""
render_vibevoice_demos.py — Generate all 8 template demos with VibeVoice TTS

Uses Microsoft VibeVoice 1.5B instead of macOS say for narration.
Same captain's log lyrics, same 8 genre templates, different voice engine.

Voice mapping (Alice=female, Frank=male):
  trance   → Alice     lofi     → Alice
  cinematic→ Frank     ambient  → Alice
  acid     → Frank     hiphop   → Frank
  minimal  → Frank     anthem   → Alice

Usage:
    python LABS/pattern-engine/render_vibevoice_demos.py
    python LABS/pattern-engine/render_vibevoice_demos.py --templates trance ambient
    python LABS/pattern-engine/render_vibevoice_demos.py --play
"""

import os
import sys
import time
import wave
import array
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
from vibevoice.modular.modeling_vibevoice_inference import (
    VibeVoiceForConditionalGenerationInference,
)
from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor

from songs import render_song
from songfile import parse_layer
from templates import TEMPLATES, apply_template
from tidal import stack

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL_ID = "microsoft/VibeVoice-1.5B"
VOICES_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../harvest-cache/tsomerville2/term4-wez-cx/voices",
)
VOICE_SAMPLES = {
    "alice": os.path.join(VOICES_DIR, "en-Alice_woman.wav"),
    "frank": os.path.join(VOICES_DIR, "en-Frank_man.wav"),
}

# Template → VibeVoice speaker
VOICE_MAP = {
    "trance":    "alice",
    "lofi":      "alice",
    "cinematic": "frank",
    "ambient":   "alice",
    "acid":      "frank",
    "hiphop":    "frank",
    "minimal":   "frank",
    "anthem":    "alice",
}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demos-vibevoice")

# Captain's log narration texts (same as say-based demos)
NARRATION_TEXTS = [
    "captain's log",
    "clone detection. ten thousand clones across seventy two repos.",
    "semantic grouping. polyglot tokens.",
    "four sound systems evaluated. they said tidal was too rigid. they were wrong.",
    "we followed switch angel. five notes became a world.",
    "the forge makes music now. end of log.",
]


# ---------------------------------------------------------------------------
# VibeVoice TTS engine
# ---------------------------------------------------------------------------

class VibeVoiceEngine:
    """Load model once, generate speech clips on demand."""

    def __init__(self, device="mps"):
        self.device = device
        print("  Loading VibeVoice processor...")
        self.processor = VibeVoiceProcessor.from_pretrained(MODEL_ID)

        print("  Loading VibeVoice model (1.5B params)...")
        self.model = VibeVoiceForConditionalGenerationInference.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float32,
            attn_implementation="sdpa",
        )
        self.model = self.model.to(device)
        self.model.eval()
        self.model.set_ddpm_inference_steps(20)
        print("  VibeVoice ready.\n")

    def generate_speech(self, text, wav_path, voice_sample):
        """Generate speech WAV at 44100Hz mono using VibeVoice."""
        # Format for VibeVoice
        script = f"Speaker 0: {text}\n"

        encoded = self.processor(
            text=[script],
            voice_samples=[[voice_sample]],
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )
        for key, value in encoded.items():
            if torch.is_tensor(value):
                encoded[key] = value.to(self.device)

        outputs = self.model.generate(
            **dict(encoded),
            cfg_scale=3.0,
            tokenizer=self.processor.tokenizer,
            is_prefill=True,
            return_speech=True,
            verbose=False,
            max_length_times=2.0,
        )

        if not outputs.speech_outputs or outputs.speech_outputs[0] is None:
            print(f"    WARNING: No audio for '{text[:40]}...'")
            return False

        audio = outputs.speech_outputs[0].detach().cpu()

        # Save 24kHz WAV via processor
        tmp_24k = wav_path + ".24k.wav"
        self.processor.save_audio(audio, output_path=tmp_24k)

        # Resample to 44100Hz mono using afconvert
        subprocess.run(
            ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", tmp_24k, wav_path],
            check=True, capture_output=True,
        )
        os.remove(tmp_24k)
        return True


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_demo(template_name, tts_engine, texts):
    """Render one template demo with VibeVoice narration."""
    voice_key = VOICE_MAP[template_name]
    voice_sample = VOICE_SAMPLES[voice_key]
    tmpl = TEMPLATES[template_name]
    bpm = tmpl["bpm"]
    voice_lead = tmpl["voice_lead"]
    music_volume = tmpl.get("music_volume", 1.0)

    print(f"\n{'='*50}")
    print(f"  {template_name.upper()} — {bpm} BPM — voice: {voice_key}")
    print(f"{'='*50}")

    # Get narrated sections from template
    song_data = apply_template(template_name, texts)
    raw_sections = song_data["sections"]

    cycle_dur = (60.0 / bpm) * 4

    # Build pattern sections and voiceover schedule
    sections = []
    voiceovers = []
    time_cursor = 0.0
    for sec in raw_sections:
        cycles = sec.get("cycles", 4)
        patterns = [parse_layer(l) for l in sec.get("layers", [])]
        pattern = stack(*patterns) if len(patterns) > 1 else patterns[0]
        sections.append((pattern, cycles))
        if sec.get("say"):
            vo_time = max(0.0, time_cursor - voice_lead)
            voiceovers.append((vo_time, sec["say"]))
        time_cursor += cycles * cycle_dur

    duration = time_cursor
    output_path = os.path.join(OUTPUT_DIR, f"captains_log_{template_name}.wav")

    # Render music
    print(f"  Rendering music ({len(sections)} sections, {duration:.0f}s)...")
    render_song(sections, output_path, bpm=bpm)

    # Scale music volume
    if music_volume < 1.0:
        with wave.open(output_path, "r") as wf:
            n_frames = wf.getnframes()
            rate = wf.getframerate()
            data = array.array("h", wf.readframes(n_frames))
        for j in range(len(data)):
            data[j] = int(data[j] * music_volume)
        with wave.open(output_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(data.tobytes())
        print(f"  Music volume: {int(music_volume * 100)}%")

    # Generate and mix voiceovers
    print(f"  Generating {len(voiceovers)} VibeVoice clips...")
    tmp_dir = OUTPUT_DIR

    with wave.open(output_path, "r") as wf:
        n_frames = wf.getnframes()
        rate = wf.getframerate()
        music_data = array.array("h", wf.readframes(n_frames))

    for i, (t_sec, text) in enumerate(voiceovers):
        short = text[:50] + ("..." if len(text) > 50 else "")
        print(f"    [{i+1}/{len(voiceovers)}] @{t_sec:.1f}s \"{short}\"")
        speech_wav = os.path.join(tmp_dir, f"_vv_{i}.wav")

        t0 = time.perf_counter()
        ok = tts_engine.generate_speech(text, speech_wav, voice_sample)
        gen_time = time.perf_counter() - t0

        if ok:
            with wave.open(speech_wav, "r") as sf:
                speech_data = array.array("h", sf.readframes(sf.getnframes()))

            start_sample = int(t_sec * rate)
            for j, sample in enumerate(speech_data):
                idx = start_sample + j
                if idx < len(music_data):
                    mixed = music_data[idx] + int(sample * 0.8)
                    music_data[idx] = max(-32768, min(32767, mixed))

            os.remove(speech_wav)
            print(f"           ({gen_time:.1f}s)")

    with wave.open(output_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(music_data.tobytes())

    mins = int(duration) // 60
    secs = int(duration) % 60
    print(f"  Saved: {output_path} ({mins}:{secs:02d})")
    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Render template demos with VibeVoice TTS")
    parser.add_argument("--templates", nargs="*", default=None,
                        help="Specific templates to render (default: all 8)")
    parser.add_argument("--play", action="store_true",
                        help="Play each demo after rendering")
    parser.add_argument("--device", default="mps",
                        help="Torch device (mps, cuda, cpu)")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    template_names = args.templates or list(TEMPLATES.keys())
    for name in template_names:
        if name not in TEMPLATES:
            print(f"  Unknown template: {name}")
            print(f"  Available: {', '.join(TEMPLATES.keys())}")
            sys.exit(1)

    print(f"\n  VibeVoice Demo Renderer")
    print(f"  {len(template_names)} templates, {len(NARRATION_TEXTS)} narration lines")
    print(f"  Output: {OUTPUT_DIR}\n")

    # Load model once
    tts = VibeVoiceEngine(device=args.device)

    t_total = time.perf_counter()
    results = []

    for name in template_names:
        t0 = time.perf_counter()
        path = render_demo(name, tts, NARRATION_TEXTS)
        elapsed = time.perf_counter() - t0
        results.append((name, path, elapsed))

        if args.play:
            print(f"  Playing...")
            subprocess.run(["afplay", path])

    total = time.perf_counter() - t_total

    print(f"\n{'='*50}")
    print(f"  ALL DONE — {len(results)} demos in {total:.0f}s")
    print(f"{'='*50}")
    for name, path, elapsed in results:
        voice = VOICE_MAP[name]
        print(f"  {name:12s}  {voice:6s}  {elapsed:.0f}s  {os.path.basename(path)}")
    print(f"\n  Play: bash LABS/pattern-engine/demos-vibevoice/play-demos.sh")
    print()


if __name__ == "__main__":
    main()
