import os
os.environ["SUNO_USE_SMALL_MODELS"] = "True"
os.environ["SUNO_ENABLE_MPS"] = "True"
os.environ["SUNO_OFFLOAD_CPU"] = "True"

import time
from bark import SAMPLE_RATE, generate_audio, preload_models

print("Loading models...")
t0 = time.time()
preload_models()
print(f"Models loaded in {time.time()-t0:.1f}s")

# Test singing - clip 1
text = "♪ Steel arm reaching cross the morning sky ♪"
print(f"Generating singing clip 1...")
t0 = time.time()
audio = generate_audio(text)
gen_time = time.time() - t0
print(f"Clip 1 generated in {gen_time:.1f}s, shape={audio.shape}, dtype={audio.dtype}")

import scipy.io.wavfile
import numpy as np

out1 = "/Users/t/clients/starship/starforge/LABS/MATERIALS-BAY/sonic-forge/bakeoff-songs/singing-bark-cranes.wav"
# Normalize to int16 for WAV
audio_int16 = (audio * 32767).astype(np.int16)
scipy.io.wavfile.write(out1, SAMPLE_RATE, audio_int16)
import os as _os
print(f"Saved to {out1} ({_os.path.getsize(out1)//1024} KB)")

# Test singing - clip 2
text2 = "♪ Grace in every ton of turning steel, I never thought machinery could sing ♪"
print(f"Generating singing clip 2...")
t0 = time.time()
audio2 = generate_audio(text2)
gen_time2 = time.time() - t0
print(f"Clip 2 generated in {gen_time2:.1f}s, shape={audio2.shape}, dtype={audio2.dtype}")

out2 = "/Users/t/clients/starship/starforge/LABS/MATERIALS-BAY/sonic-forge/bakeoff-songs/singing-bark-cranes2.wav"
audio2_int16 = (audio2 * 32767).astype(np.int16)
scipy.io.wavfile.write(out2, SAMPLE_RATE, audio2_int16)
print(f"Saved to {out2} ({_os.path.getsize(out2)//1024} KB)")

print("SAMPLE_RATE:", SAMPLE_RATE)
print("All done!")
