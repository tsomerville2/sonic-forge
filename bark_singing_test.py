import os
os.environ["SUNO_USE_SMALL_MODELS"] = "True"
os.environ["SUNO_ENABLE_MPS"] = "True"
os.environ["SUNO_OFFLOAD_CPU"] = "True"

import time
import numpy as np
from bark import SAMPLE_RATE, generate_audio, preload_models

print("Loading models...")
t0 = time.time()
preload_models()
print(f"Models loaded in {time.time()-t0:.1f}s")

outdir = "/Users/t/clients/starship/starforge/LABS/MATERIALS-BAY/sonic-forge/bakeoff-songs"

tests = [
    # 1. Full singing notation - short phrase
    ("bark-sing-short.wav", "♪ La la la, steel arms in the sky ♪"),

    # 2. Singing with more musical cues
    ("bark-sing-melody.wav", "♪ Watching cranes move... watching cranes move... in the morning light ♪"),

    # 3. Try with [singing] tag
    ("bark-sing-tagged.wav", "[singing] ♪ Grace in every ton of steel, the cranes are dancing ♪"),

    # 4. Humming/melodic - simpler
    ("bark-sing-hum.wav", "♪ Doo doo doo, doo doo doo, doo doo doo doo doo ♪"),

    # 5. More repetition helps melody
    ("bark-sing-repeat.wav", "♪ The sky, the sky, the beautiful sky, the cranes reach up so high ♪"),
]

import scipy.io.wavfile

for filename, text in tests:
    print(f"\n--- {filename} ---")
    print(f"Text: {text}")
    t0 = time.time()
    audio = generate_audio(text)
    elapsed = time.time() - t0
    outpath = os.path.join(outdir, filename)
    scipy.io.wavfile.write(outpath, SAMPLE_RATE, audio)
    duration = len(audio) / SAMPLE_RATE
    print(f"Generated in {elapsed:.1f}s -> {duration:.1f}s audio")

# 6. Try with a specific speaker preset known for more musical output
print("\n--- bark-sing-speaker3.wav (speaker_3 preset) ---")
t0 = time.time()
audio = generate_audio("♪ Steel arm reaching for the morning sky, beauty in the iron and steel ♪", history_prompt="v2/en_speaker_3")
elapsed = time.time() - t0
outpath = os.path.join(outdir, "bark-sing-speaker3.wav")
scipy.io.wavfile.write(outpath, SAMPLE_RATE, audio)
duration = len(audio) / SAMPLE_RATE
print(f"Generated in {elapsed:.1f}s -> {duration:.1f}s audio")

# 7. Speaker 6 (often more expressive)
print("\n--- bark-sing-speaker6.wav (speaker_6 preset) ---")
t0 = time.time()
audio = generate_audio("♪ Oh the cranes, the beautiful cranes, dancing in the morning light ♪", history_prompt="v2/en_speaker_6")
elapsed = time.time() - t0
outpath = os.path.join(outdir, "bark-sing-speaker6.wav")
scipy.io.wavfile.write(outpath, SAMPLE_RATE, audio)
duration = len(audio) / SAMPLE_RATE
print(f"Generated in {elapsed:.1f}s -> {duration:.1f}s audio")

print("\nAll done!")
