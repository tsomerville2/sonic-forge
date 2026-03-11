"""
trance1_1.py -- Following switch.angel's live session, snapshot by snapshot.

The song EVOLVES over time, just like her live coding.
Each section = a moment where she changes the code live.

0:00 — pluck arp alone (same as trance.py opening)
0:12 — switches to sawtooth + acid envelope

Usage:
    python LABS/pattern-engine/trance1_1.py

Generates trance1_1.wav — play with afplay.
"""

import os
import sys
import subprocess
import wave
import struct
import array

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from songs import render_song
from tidal import mini, stack, fast, cat, atom


def generate_speech(text, wav_path):
    """Use macOS say to generate speech WAV at 44100Hz mono."""
    aiff_path = wav_path.replace(".wav", ".aiff")
    subprocess.run(["say", "-o", aiff_path, text], check=True)
    subprocess.run([
        "afconvert", "-f", "WAVE", "-d", "LEI16@44100",
        aiff_path, wav_path
    ], check=True)
    os.remove(aiff_path)
    return wav_path


def mix_voiceover(music_path, voiceovers, output_path):
    """Mix speech clips into music at specific timestamps.

    voiceovers: list of (time_seconds, text_string)
    """
    tmp_dir = os.path.dirname(output_path)

    # Read the music
    with wave.open(music_path, "r") as wf:
        n_frames = wf.getnframes()
        rate = wf.getframerate()
        music_data = array.array("h", wf.readframes(n_frames))

    # Generate and mix each voiceover
    for i, (t_sec, text) in enumerate(voiceovers):
        speech_wav = os.path.join(tmp_dir, f"_vo_{i}.wav")
        generate_speech(text, speech_wav)

        with wave.open(speech_wav, "r") as sf:
            speech_data = array.array("h", sf.readframes(sf.getnframes()))

        # Mix speech into music buffer at the right offset
        start_sample = int(t_sec * rate)
        for j, sample in enumerate(speech_data):
            idx = start_sample + j
            if idx < len(music_data):
                # Mix: add speech at ~80% volume on top of music
                mixed = music_data[idx] + int(sample * 0.8)
                music_data[idx] = max(-32768, min(32767, mixed))

        os.remove(speech_wav)

    # Write the mixed result
    with wave.open(output_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(music_data.tobytes())


def trance1_1():
    """switch.angel live session — evolving over time"""

    # The core notes: <0 4 0 9 7> in g:minor trans(-12)
    # = G2 D3 G2 Bb3 G3

    # === PLUCK version (how the song starts) ===
    pluck_arp = fast(16, cat(
        atom("pluck:g2"),
        atom("pluck:d3"),
        atom("pluck:g2"),
        atom("pluck:bb3"),
        atom("pluck:g3"),
    ))

    # === SAW/ACID version (what she switches to at 0:12) ===
    acid_arp = fast(16, cat(
        atom("acid:g2"),
        atom("acid:d3"),
        atom("acid:g2"),
        atom("acid:bb3"),
        atom("acid:g3"),
    ))

    # At 136 BPM, 1 cycle = 4 beats = ~1.76 seconds
    # 12 seconds ≈ 7 cycles, 18 seconds ≈ 10 cycles

    sections = []

    # 0:00 — pluck arp alone, just like trance.py opens
    sections.append((pluck_arp, 7))

    # 0:12 — switches to sawtooth + acidenv
    sections.append((acid_arp, 3))

    # 0:18 — kick enters (tbd:2!4 = four-on-the-floor)
    sections.append((stack(acid_arp, mini("bd*4")), 3))

    # 0:22 — sidechain ducking added (.duckdepth(.8))
    sections.append((stack(acid_arp, mini("bd*4")), 4))

    # ~0:28 — bass enters: n("<0>*16").scale("g:minor").trans(-24)
    # Root note G pulsing 16x/cycle, same acid saw, 2 octaves below arp
    bass_pulse = fast(16, atom("acid:g1"))

    sections.append((stack(acid_arp, mini("bd*4"), bass_pulse), 10))

    # ~0:46 — she slides acidenv up (0.546 → 0.763 = brighter filter)
    #         AND switches bass from sawtooth to supersaw with .detune(rand)
    # Our "saw" synth = 4 detuned saws = supersaw equivalent
    bright_arp = fast(16, cat(
        atom("saw:g2"),
        atom("saw:d3"),
        atom("saw:g2"),
        atom("saw:bb3"),
        atom("saw:g3"),
    ))
    supersaw_bass = fast(16, atom("saw:g1"))

    sections.append((stack(bright_arp, mini("bd*4"), supersaw_bass), 10))

    # ~1:04 — adds s("top:1/2").fit().o(5) = stretched cymbal wash texture
    # Subtle atmospheric layer on top of everything
    sections.append((stack(bright_arp, mini("bd*4"), supersaw_bass, mini("oh*2")), 10))

    # ~1:22 — cranks BOTH sliders up: arp acidenv 0.851, bass acidenv 0.751
    # Maximum power — stack acid + saw arps together for full thickness
    # She jams on this for a while
    sections.append((stack(
        acid_arp, bright_arp,
        mini("bd*4"), supersaw_bass, mini("oh*2"),
    ), 20))

    # (more sections will be added as we get more screenshots)

    return sections


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(out_dir, "trance1_1.wav")

    print("=" * 50)
    print("  switch.angel live session")
    print("  0:00 pluck → 0:12 acid → 0:18 kick → 0:28 bass → 0:46 supersaw → 1:04 wash → 1:22 FULL POWER")
    print("=" * 50)

    sections = trance1_1()
    render_song(sections, filename, bpm=136)

    # Voiceovers — narrate each change a couple seconds before it hits
    # Section times: 0:00 pluck, 0:12 acid, 0:18 kick, 0:22 duck,
    #                0:28 bass, 0:46 supersaw, 1:04 wash, 1:22 full power
    voiceovers = [
        (0.5,  "in the beginning, there were five notes"),
        (10.0, "now let's switch to sawtooth, with an acid envelope"),
        (16.0, "here comes the kick drum, four on the floor"),
        (20.5, "adding some sidechain ducking"),
        (26.0, "and now, the bass enters, pulsing on the root"),
        (43.0, "switching to supersaw, cranking the detune"),
        (61.0, "adding a cymbal wash on top, just a little texture"),
        (78.0, "now we crank both sliders up, full power, let it ride"),
    ]

    print("  Adding voiceovers...")
    mix_voiceover(filename, voiceovers, filename)

    print(f"\n  Play: afplay {filename}")
