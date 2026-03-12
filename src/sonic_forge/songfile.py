"""
songfile.py — YAML song format to WAV converter

Reads a .yaml song file describing sections, instruments, lyrics/voiceover,
and renders it to a WAV with timed text-to-speech narration.

Usage:
    python LABS/pattern-engine/songfile.py LABS/pattern-engine/trance1_1.yaml
    python LABS/pattern-engine/songfile.py my_song.yaml --play
    python LABS/pattern-engine/songfile.py my_song.yaml --voice Alex
    python LABS/pattern-engine/songfile.py my_song.yaml --lead 3.0

YAML format:
    title: my song
    bpm: 136
    voice: Samantha          # macOS say voice, or kokoro voice like af_heart
    engine: kokoro           # TTS engine: say (default), kokoro
    fx: helmet               # robot effect: helmet, intercom, droid, ringmod, bitcrush
    voice_lead: 2.0          # seconds before change to start speaking

    sections:
      - say: "lyrics or narration here"
        cycles: 8
        layers:
          - synth: pluck               # pitched synth: acid, saw, pluck, pad, bass
            notes: g2 d3 g2 bb3 g3     # space-separated notes
            fast: 16                   # speed multiplier (optional, default 1)
          - mini: "bd*4"               # tidal mini-notation for drums/patterns
          - mini: "~ hh ~ hh"
"""

import os
import sys
import subprocess
import wave
import array

import yaml

from sonic_forge.songs import render_song
from sonic_forge.tidal import mini, stack, fast, cat, atom
from sonic_forge.templates import TEMPLATES, apply_template, list_templates


def parse_layer(layer_def):
    """Convert a YAML layer definition to a tidal pattern."""
    if "mini" in layer_def:
        return mini(layer_def["mini"])

    if "synth" in layer_def:
        synth_name = layer_def["synth"]
        notes = layer_def.get("notes", "c3").split()
        speed = layer_def.get("fast", 1)

        if len(notes) == 1:
            pat = atom(f"{synth_name}:{notes[0]}")
        else:
            pat = cat(*[atom(f"{synth_name}:{n}") for n in notes])

        if speed > 1:
            pat = fast(speed, pat)
        return pat

    raise ValueError(f"Unknown layer type: {layer_def}")


def parse_song(yaml_path, target_duration=None, voice_lead_override=None):
    """Parse a YAML song file into sections and metadata.

    target_duration: if set, scale all cycle counts to fit this many seconds.
    voice_lead_override: override the voice_lead from the YAML.
    """
    with open(yaml_path) as f:
        doc = yaml.safe_load(f)

    title = doc.get("title", "untitled")
    bpm = doc.get("bpm", 130)
    voice = doc.get("voice", "Samantha")
    engine = doc.get("engine", None)
    fx = doc.get("fx", None)
    voice_lead = voice_lead_override if voice_lead_override is not None else doc.get("voice_lead", 2.0)

    cycle_dur = (60.0 / bpm) * 4  # 4 beats per cycle
    raw_sections = doc.get("sections", [])

    # Calculate scale factor if target duration is set
    scale = 1.0
    if target_duration:
        total_cycles = sum(sec.get("cycles", 4) for sec in raw_sections)
        raw_duration = total_cycles * cycle_dur
        scale = target_duration / raw_duration
        # Shrink voice_lead proportionally too
        voice_lead = max(0.3, voice_lead * scale)

    sections = []
    voiceovers = []
    time_cursor = 0.0

    for sec in raw_sections:
        raw_cycles = sec.get("cycles", 4)
        cycles = max(1, round(raw_cycles * scale))
        layers_def = sec.get("layers", [])
        say_text = sec.get("say", None)

        # Build the pattern from layers
        patterns = [parse_layer(l) for l in layers_def]
        if len(patterns) == 1:
            pattern = patterns[0]
        else:
            pattern = stack(*patterns)

        sections.append((pattern, cycles))

        # Schedule voiceover
        if say_text:
            vo_time = max(0.0, time_cursor - voice_lead)
            voiceovers.append((vo_time, say_text))

        time_cursor += cycles * cycle_dur

    return {
        "title": title,
        "bpm": bpm,
        "voice": voice,
        "engine": engine,
        "fx": fx,
        "voice_lead": voice_lead,
        "sections": sections,
        "voiceovers": voiceovers,
        "duration": time_cursor,
    }


def generate_speech(text, wav_path, voice="Samantha", rate=None,
                    engine=None, fx=None):
    """Generate speech WAV at 44100Hz mono via any supported TTS engine.

    engine: "say" (macOS, default), "kokoro" (Kokoro-82M ONNX).
           Auto-detected from voice name if omitted.
    fx: Robot effect to apply: helmet, intercom, droid, ringmod, bitcrush.
    rate: words per minute (macOS say only).
    """
    from sonic_forge.tts import generate_to_wav, _apply_fx, _detect_engine

    if not engine:
        engine = _detect_engine(voice)

    generate_to_wav(text, wav_path, engine=engine, voice=voice, rate=rate)

    # Apply robot FX if requested
    if fx:
        processed_path = _apply_fx(wav_path, fx)
        # _apply_fx deletes original and returns new path with _fx suffix
        # We need the result at wav_path for the mixer, so rename back
        os.rename(processed_path, wav_path)

    # Ensure 44100Hz mono 16-bit for mixing (kokoro may output different format)
    if engine != "say":
        _normalize_wav(wav_path)


def _normalize_wav(wav_path):
    """Ensure WAV is 44100Hz mono 16-bit PCM for mixing compatibility."""
    with wave.open(wav_path, "r") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        data = wf.readframes(wf.getnframes())

    if sr == 44100 and nch == 1 and sw == 2:
        return  # already correct format

    # Read raw samples
    samples = array.array("h", data)

    # Stereo to mono
    if nch == 2:
        mono = array.array("h")
        for i in range(0, len(samples), 2):
            mono.append((samples[i] + samples[i + 1]) // 2)
        samples = mono

    # Resample if needed (simple linear interpolation)
    if sr != 44100:
        ratio = 44100 / sr
        n = len(samples)
        new_n = int(n * ratio)
        resampled = array.array("h")
        for i in range(new_n):
            src = i / ratio
            idx = int(src)
            frac = src - idx
            if idx + 1 < n:
                val = int(samples[idx] * (1 - frac) + samples[idx + 1] * frac)
            else:
                val = samples[min(idx, n - 1)]
            resampled.append(max(-32768, min(32767, val)))
        samples = resampled

    with wave.open(wav_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(samples.tobytes())


def mix_voiceover(music_path, voiceovers, output_path, voice="Samantha",
                  speech_rate=None, engine=None, fx=None, voice_stem=None):
    """Mix speech clips into music at specific timestamps.

    engine: TTS engine ("say", "kokoro"). Auto-detected from voice if omitted.
    fx: Robot effect to apply to all voiceovers.
    voice_stem: If set, save voice-only WAV to this path (for lip sync analysis).
    """
    tmp_dir = os.path.dirname(output_path) or "."

    with wave.open(music_path, "r") as wf:
        n_frames = wf.getnframes()
        rate = wf.getframerate()
        music_data = array.array("h", wf.readframes(n_frames))

    # Voice-only stem: same length as music, zeroed out
    if voice_stem:
        voice_data = array.array("h", [0] * len(music_data))

    for i, (t_sec, text) in enumerate(voiceovers):
        speech_wav = os.path.join(tmp_dir, f"_vo_{i}.wav")
        generate_speech(text, speech_wav, voice=voice, rate=speech_rate,
                        engine=engine, fx=fx)

        with wave.open(speech_wav, "r") as sf:
            speech_data = array.array("h", sf.readframes(sf.getnframes()))

        start_sample = int(t_sec * rate)
        for j, sample in enumerate(speech_data):
            idx = start_sample + j
            if idx < len(music_data):
                mixed = music_data[idx] + int(sample * 0.8)
                music_data[idx] = max(-32768, min(32767, mixed))
                if voice_stem:
                    voice_data[idx] = sample

        os.remove(speech_wav)

    with wave.open(output_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(music_data.tobytes())

    if voice_stem:
        with wave.open(voice_stem, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(voice_data.tobytes())


def render_yaml_song(yaml_path, output_path=None, play=False,
                     voice_override=None, lead_override=None,
                     target_duration=None, speech_rate=None,
                     template_name=None, engine=None, fx=None,
                     voice_stem=None):
    """Full pipeline: YAML -> music WAV -> mix voiceovers -> final WAV.

    engine: TTS engine for voiceovers ("say", "kokoro"). Auto-detected from voice.
    fx: Robot effect for voiceovers (helmet, intercom, droid, etc.).
    voice_stem: If set, save voice-only WAV to this path (for lip sync).
    """

    if template_name:
        # Template mode: extract narration texts from YAML, apply template
        with open(yaml_path) as f:
            doc = yaml.safe_load(f)
        yaml_sections = [sec for sec in doc.get("sections", []) if sec.get("say")]
        texts = [sec["say"] for sec in yaml_sections]
        yaml_cycles = [sec.get("cycles") for sec in yaml_sections]
        tmpl_song = apply_template(template_name, texts)

        # Now parse the template output the same way as a regular song
        title = doc.get("title", tmpl_song["title"])
        bpm = tmpl_song["bpm"]
        voice = voice_override or doc.get("voice") or tmpl_song["voice"]
        voice_lead = lead_override if lead_override is not None else doc.get("voice_lead", tmpl_song["voice_lead"])
        cycle_dur = (60.0 / bpm) * 4

        # Scale if target_duration set
        raw_sections = tmpl_song["sections"]
        scale = 1.0
        if target_duration:
            total_cycles = sum(s.get("cycles", 4) for s in raw_sections)
            raw_dur = total_cycles * cycle_dur
            scale = target_duration / raw_dur
            voice_lead = max(0.3, voice_lead * scale)

        sections = []
        voiceovers = []
        time_cursor = 0.0
        for idx, sec in enumerate(raw_sections):
            # YAML cycles override template cycles when specified
            if idx < len(yaml_cycles) and yaml_cycles[idx] is not None:
                raw_cycles = yaml_cycles[idx]
            else:
                raw_cycles = sec.get("cycles", 4)
            cycles = max(1, round(raw_cycles * scale))
            patterns = [parse_layer(l) for l in sec.get("layers", [])]
            pattern = stack(*patterns) if len(patterns) > 1 else patterns[0]
            sections.append((pattern, cycles))
            if sec.get("say"):
                voiceovers.append((max(0.0, time_cursor - voice_lead), sec["say"]))
            time_cursor += cycles * cycle_dur

        song = {
            "title": title,
            "bpm": bpm,
            "voice": voice,
            "voice_lead": voice_lead,
            "music_volume": tmpl_song.get("music_volume", 1.0),
            "sections": sections,
            "voiceovers": voiceovers,
            "duration": time_cursor,
        }
    else:
        song = parse_song(yaml_path, target_duration=target_duration,
                          voice_lead_override=lead_override)

    if voice_override:
        song["voice"] = voice_override

    # Resolve engine/fx: CLI flags override YAML fields
    engine = engine or song.get("engine")
    fx = fx or song.get("fx")

    if not output_path:
        output_path = yaml_path.rsplit(".", 1)[0] + ".wav"

    title = song["title"]
    bpm = song["bpm"]
    dur = song["duration"]
    n_sections = len(song["sections"])
    n_voices = len(song["voiceovers"])

    print("=" * 50)
    print(f"  {title}")
    print(f"  {n_sections} sections, {n_voices} voiceovers, {bpm} BPM")
    print("=" * 50)

    # Render music
    render_song(song["sections"], output_path, bpm=bpm)

    # Scale music volume if template specifies it
    music_volume = song.get("music_volume", 1.0)
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

    # Mix voiceovers
    if song["voiceovers"]:
        engine_info = f", engine: {engine}" if engine else ""
        fx_info = f", fx: {fx}" if fx else ""
        rate_info = f", {speech_rate} WPM" if speech_rate else ""
        print(f"  Mixing {n_voices} voiceovers (voice: {song['voice']}{engine_info}{fx_info}{rate_info})...")
        mix_voiceover(output_path, song["voiceovers"], output_path,
                      voice=song["voice"], speech_rate=speech_rate,
                      engine=engine, fx=fx, voice_stem=voice_stem)

    mins = int(dur) // 60
    secs = int(dur) % 60
    print(f"\n  Output: {output_path}")
    print(f"  Duration: {mins}:{secs:02d}")

    if play:
        print(f"  Playing...")
        subprocess.run(["afplay", output_path])
    else:
        print(f"  Play: afplay {output_path}")

    return output_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YAML song file to WAV converter")
    parser.add_argument("yaml_file", nargs="?", help="Path to .yaml song file")
    parser.add_argument("--play", action="store_true", help="Play after rendering")
    parser.add_argument("--voice", default=None, help="macOS voice (e.g. Alex, Samantha, Daniel)")
    parser.add_argument("--lead", type=float, default=None,
                        help="Seconds before each change to start voiceover")
    parser.add_argument("--duration", type=float, default=None,
                        help="Target song length in seconds (scales all sections)")
    parser.add_argument("--rate", type=int, default=None,
                        help="Speech speed in words per minute")
    parser.add_argument("--template", default=None,
                        help="Apply a genre template (trance, lofi, cinematic, ambient, acid, hiphop, minimal, anthem)")
    parser.add_argument("--templates", action="store_true",
                        help="List available templates")
    parser.add_argument("--engine", default=None,
                        help="TTS engine: say (macOS), kokoro (Kokoro-82M ONNX)")
    parser.add_argument("--fx", default=None,
                        help="Robot effect for voiceovers: helmet, intercom, droid, ringmod, bitcrush")
    parser.add_argument("-o", "--output", default=None, help="Output WAV path")

    args = parser.parse_args()

    if args.templates:
        list_templates()
        sys.exit(0)

    if not args.yaml_file:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.yaml_file):
        print(f"  Error: {args.yaml_file} not found")
        sys.exit(1)

    render_yaml_song(
        args.yaml_file,
        output_path=args.output,
        play=args.play,
        voice_override=args.voice,
        lead_override=args.lead,
        target_duration=args.duration,
        speech_rate=args.rate,
        template_name=args.template,
        engine=args.engine,
        fx=args.fx,
    )
