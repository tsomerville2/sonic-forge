"""
robotize.py — Apply robot/droid effects to any WAV file

Effects:
  ringmod   - Ring modulation (classic Dalek/robot)
  bitcrush  - 8-bit retro crunch
  vocoder   - Synthetic harmonic reconstruction
  droid     - Combined: ringmod + bitcrush + resonance (full droid)

Usage:
    python robotize.py input.wav                    # all effects
    python robotize.py input.wav --effects ringmod bitcrush
    python robotize.py input.wav --freq 60          # ring mod frequency
"""

import numpy as np
import soundfile as sf
import os


def ringmod(samples, sr, freq=55.0, mix=0.7):
    """Ring modulation — multiply signal by a sine wave.
    Classic Dalek/Cyberman effect. freq=30-80 for deep robot, 100-200 for metallic."""
    t = np.arange(len(samples)) / sr
    carrier = np.sin(2 * np.pi * freq * t)
    modulated = samples * carrier
    return samples * (1 - mix) + modulated * mix


def bitcrush(samples, sr, bits=6, downsample=4):
    """Bit-depth reduction + sample rate reduction.
    bits=8 for mild, bits=4 for extreme. downsample=4 means keep every 4th sample."""
    # Reduce bit depth
    levels = 2 ** bits
    crushed = np.round(samples * levels) / levels
    # Downsample (sample-and-hold)
    if downsample > 1:
        indices = np.arange(len(crushed))
        crushed = crushed[(indices // downsample) * downsample]
    return crushed


def vocoder_effect(samples, sr, num_bands=20, carrier_freq=120.0):
    """Simple vocoder — analyze speech in frequency bands, resynthesize with harmonics.
    Creates that classic 'talking synthesizer' sound."""
    from numpy.fft import rfft, irfft

    # Work in overlapping frames
    frame_size = 2048
    hop = frame_size // 4
    n_frames = (len(samples) - frame_size) // hop + 1

    output = np.zeros(len(samples))
    window = np.hanning(frame_size)

    # Generate harmonic carrier
    t = np.arange(frame_size) / sr
    carrier = np.zeros(frame_size)
    for h in range(1, 30):
        carrier += np.sin(2 * np.pi * carrier_freq * h * t) / h

    for i in range(n_frames):
        start = i * hop
        frame = samples[start:start + frame_size] * window

        # Get spectral envelope (smooth magnitude)
        spectrum = rfft(frame)
        magnitude = np.abs(spectrum)

        # Smooth the envelope
        kernel_size = len(magnitude) // num_bands
        if kernel_size > 1:
            kernel = np.ones(kernel_size) / kernel_size
            envelope = np.convolve(magnitude, kernel, mode='same')
        else:
            envelope = magnitude

        # Apply envelope to carrier
        carrier_frame = carrier * window
        carrier_spectrum = rfft(carrier_frame)
        carrier_mag = np.abs(carrier_spectrum)
        carrier_mag[carrier_mag < 1e-10] = 1e-10

        # Scale carrier by speech envelope
        result_spectrum = carrier_spectrum * (envelope / carrier_mag)
        result = irfft(result_spectrum, n=frame_size)

        output[start:start + frame_size] += result * window

    # Normalize
    peak = np.max(np.abs(output))
    if peak > 0:
        output = output / peak * np.max(np.abs(samples))
    return output


def droid(samples, sr):
    """Full droid effect — layered processing for maximum robot character.
    Ring mod + resonant filter + bitcrush + subtle chorus."""
    # Layer 1: ring mod at low frequency for bass rumble
    out = ringmod(samples, sr, freq=45.0, mix=0.5)

    # Layer 2: add a second ring mod at higher freq for metallic sheen
    t = np.arange(len(out)) / sr
    carrier2 = np.sin(2 * np.pi * 150 * t) * 0.3
    out = out + out * carrier2 * 0.4

    # Layer 3: mild bitcrush for digital texture
    out = bitcrush(out, sr, bits=8, downsample=2)

    # Layer 4: resonant boost around 800-1200Hz (makes it sound more "speakery")
    # Simple bandpass via FFT
    from numpy.fft import rfft, irfft
    spectrum = rfft(out)
    freqs = np.fft.rfftfreq(len(out), 1.0 / sr)
    # Boost 600-1500Hz
    boost = np.ones(len(freqs))
    mask = (freqs >= 600) & (freqs <= 1500)
    boost[mask] = 2.5
    spectrum *= boost
    out = irfft(spectrum, n=len(out))

    # Normalize
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak * 0.9
    return out


def helmet(samples, sr):
    """Mandalorian helmet effect — voice trapped in a small resonant cavity.
    Bandpass to kill lows/highs, resonant peaks at helmet frequencies,
    tight early reflections for that 'inside a bucket' feel."""
    from numpy.fft import rfft, irfft

    out = samples.copy()

    # Layer 1: Bandpass — helmet blocks sub-bass and sparkle
    spectrum = rfft(out)
    freqs = np.fft.rfftfreq(len(out), 1.0 / sr)
    filt = np.ones(len(freqs))
    # Roll off below 250Hz (helmet blocks bass)
    low_mask = freqs < 250
    filt[low_mask] = (freqs[low_mask] / 250) ** 2
    # Roll off above 4000Hz (muffled highs)
    high_mask = freqs > 4000
    filt[high_mask] = (4000 / np.maximum(freqs[high_mask], 1)) ** 3
    # Kill everything above 6kHz
    filt[freqs > 6000] = 0.0
    # Resonant peaks — helmet cavity resonances
    for peak_freq, q, gain in [(800, 200, 2.8), (1600, 250, 2.2), (2800, 300, 1.8)]:
        resonance = np.exp(-0.5 * ((freqs - peak_freq) / q) ** 2)
        filt += resonance * gain
    spectrum *= filt
    out = irfft(spectrum, n=len(out))

    # Layer 2: Tight early reflections (small cavity reverb)
    delay_ms = [3.2, 5.7, 8.1, 11.4]  # very short delays = small space
    decay = [0.35, 0.25, 0.18, 0.12]
    reverb = out.copy()
    for d_ms, dec in zip(delay_ms, decay):
        delay_samples = int(sr * d_ms / 1000)
        delayed = np.zeros(len(out))
        delayed[delay_samples:] = out[:-delay_samples] * dec
        reverb += delayed
    out = reverb

    # Layer 3: Subtle ring mod — metallic tinge from the helmet
    t = np.arange(len(out)) / sr
    out = out + out * np.sin(2 * np.pi * 180 * t) * 0.12

    # Layer 4: Mild saturation — speaker compression inside helmet
    out = np.tanh(out * 1.8) * 0.7

    # Normalize
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak * 0.9
    return out


def intercom(samples, sr):
    """Bank teller / drive-through intercom — cheap tiny speaker behind glass.
    Very narrow bandwidth, harsh mids, clipping distortion, lo-fi crackle."""
    from numpy.fft import rfft, irfft

    out = samples.copy()

    # Layer 1: Aggressive bandpass — tiny speaker only does 400-2800Hz
    spectrum = rfft(out)
    freqs = np.fft.rfftfreq(len(out), 1.0 / sr)
    filt = np.zeros(len(freqs))
    # Only pass 400-2800Hz
    pass_mask = (freqs >= 400) & (freqs <= 2800)
    filt[pass_mask] = 1.0
    # Soft edges
    edge_lo = (freqs >= 300) & (freqs < 400)
    filt[edge_lo] = (freqs[edge_lo] - 300) / 100
    edge_hi = (freqs > 2800) & (freqs <= 3200)
    filt[edge_hi] = (3200 - freqs[edge_hi]) / 400
    # Harsh mid peak at 1.2kHz (resonance of cheap speaker)
    resonance = np.exp(-0.5 * ((freqs - 1200) / 150) ** 2) * 3.0
    filt += resonance
    spectrum *= filt
    out = irfft(spectrum, n=len(out))

    # Layer 2: Hard clipping — speaker distortion
    out = out * 2.5
    out = np.clip(out, -0.6, 0.6)

    # Layer 3: Downsample — cheap ADC
    downsample = 3
    indices = np.arange(len(out))
    out = out[(indices // downsample) * downsample]

    # Layer 4: Add some hum (60Hz electrical noise, very subtle)
    t = np.arange(len(out)) / sr
    hum = np.sin(2 * np.pi * 60 * t) * 0.03
    out = out + hum

    # Normalize
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak * 0.85
    return out


EFFECTS = {
    "ringmod": ("Ring Mod (Dalek robot)", lambda s, sr: ringmod(s, sr, freq=55.0, mix=0.7)),
    "bitcrush": ("Bitcrush (8-bit retro)", lambda s, sr: bitcrush(s, sr, bits=6, downsample=4)),
    "vocoder": ("Vocoder (synth speech)", lambda s, sr: vocoder_effect(s, sr)),
    "droid": ("Droid (full robot)", lambda s, sr: droid(s, sr)),
    "helmet": ("Helmet (Mandalorian)", lambda s, sr: helmet(s, sr)),
    "intercom": ("Intercom (bank teller)", lambda s, sr: intercom(s, sr)),
}


def robotize_file(input_path, output_dir=None, effects=None):
    """Apply robot effects to a WAV file, saving each variant."""
    samples, sr = sf.read(input_path)

    # If stereo, convert to mono for processing
    if len(samples.shape) > 1:
        samples = samples.mean(axis=1)

    if output_dir is None:
        output_dir = os.path.dirname(input_path)

    base = os.path.splitext(os.path.basename(input_path))[0]
    effects = effects or list(EFFECTS.keys())

    results = []
    for fx_key in effects:
        if fx_key not in EFFECTS:
            print(f"  Unknown effect: {fx_key}")
            continue
        fx_name, fx_fn = EFFECTS[fx_key]
        out = fx_fn(samples.copy(), sr)
        # Clip to prevent distortion
        out = np.clip(out, -1.0, 1.0)
        out_path = os.path.join(output_dir, f"{base}__{fx_key}.wav")
        sf.write(out_path, out, sr)
        results.append((fx_key, fx_name, out_path))
        print(f"  {fx_name}: {out_path}")

    return results


def generate_robot_samples():
    """Generate robotized versions of select Kokoro voices for the comparison player."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    kokoro_dir = os.path.join(base_dir, "samples", "kokoro")
    robot_dir = os.path.join(base_dir, "samples", "kokoro-robot")
    os.makedirs(robot_dir, exist_ok=True)

    # Pick a few good base voices to robotize
    source_voices = [
        "full_af_heart",    # warm female → robot
        "full_am_adam",     # clear male → robot
        "full_am_onyx",     # deep male → robot
        "full_bf_emma",     # British female → robot
    ]

    print(f"\n  Robotizer — generating droid voices from Kokoro")
    print(f"  Output: {robot_dir}\n")

    for voice in source_voices:
        src = os.path.join(kokoro_dir, f"{voice}.wav")
        if not os.path.exists(src):
            print(f"  SKIP {voice} (not found)")
            continue

        print(f"\n  {voice}:")
        samples, sr = sf.read(src)
        if len(samples.shape) > 1:
            samples = samples.mean(axis=1)

        for fx_key, (fx_name, fx_fn) in EFFECTS.items():
            out = fx_fn(samples.copy(), sr)
            out = np.clip(out, -1.0, 1.0)
            out_path = os.path.join(robot_dir, f"full_{voice[5:]}__{fx_key}.wav")
            sf.write(out_path, out, sr)
            print(f"    {fx_name}")

    # Also generate the 6 individual lines with the droid effect (using af_heart as base)
    print(f"\n  Individual lines (droid effect on af_heart):")
    for i in range(6):
        src = os.path.join(kokoro_dir, f"line_{i}.wav")
        if not os.path.exists(src):
            continue
        samples, sr = sf.read(src)
        if len(samples.shape) > 1:
            samples = samples.mean(axis=1)
        out = droid(samples.copy(), sr)
        out = np.clip(out, -1.0, 1.0)
        out_path = os.path.join(robot_dir, f"line_{i}.wav")
        sf.write(out_path, out, sr)
        print(f"    line_{i}")

    count = len([f for f in os.listdir(robot_dir) if f.endswith(".wav")])
    print(f"\n  Done — {count} robot samples in {robot_dir}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] != "--generate":
        # Robotize a specific file
        input_path = sys.argv[1]
        effects = None
        if "--effects" in sys.argv:
            idx = sys.argv.index("--effects")
            effects = sys.argv[idx + 1:]
        robotize_file(input_path, effects=effects)
    else:
        # Generate robot samples for the comparison player
        generate_robot_samples()
