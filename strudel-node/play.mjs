/**
 * play.mjs — Strudel pattern engine → audio output
 *
 * Uses @strudel/core + @strudel/mini for patterns,
 * then node-web-audio-api OfflineAudioContext for synthesis,
 * then writes a WAV file.
 */

import { mini } from '@strudel/mini';
import { AudioBuffer, OfflineAudioContext } from 'node-web-audio-api';
import { writeFileSync } from 'fs';

// ─── Config ───────────────────────────────────────────────────────────────────
const BPM = 120;
const CYCLES = 4;
const SAMPLE_RATE = 44100;
const SECONDS_PER_CYCLE = 60 / BPM * 4; // 4 beats per cycle
const TOTAL_SECONDS = CYCLES * SECONDS_PER_CYCLE;
const NUM_CHANNELS = 1;

// ─── Pattern ──────────────────────────────────────────────────────────────────
// A fun pattern: euclidean kick, snare on 2/4, 8 hihat, cp accent
const pat = mini("[bd(3,8), hh*8, ~ sd ~ sd, ~ ~ ~ cp]");
const events = pat.queryArc(0, CYCLES);

console.log(`Pattern has ${events.length} events over ${CYCLES} cycles`);
console.log(`Total audio: ${TOTAL_SECONDS}s @ ${SAMPLE_RATE}Hz`);

// ─── Synthesis helpers ─────────────────────────────────────────────────────────

/**
 * Synthesize a kick drum into the audio context buffer.
 * Pitch-swept sine wave with exponential decay.
 */
async function synthKick(ctx, startTime, duration = 0.3) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);

    // Kick: start at 150Hz, sweep to 40Hz
    osc.frequency.setValueAtTime(150, startTime);
    osc.frequency.exponentialRampToValueAtTime(40, startTime + 0.08);

    // Gain envelope: fast attack, exponential decay
    gain.gain.setValueAtTime(0.8, startTime);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

    osc.start(startTime);
    osc.stop(startTime + duration);
}

/**
 * Snare: noise burst + tone
 */
async function synthSnare(ctx, startTime, duration = 0.15) {
    // Noise component
    const bufferSize = Math.ceil(SAMPLE_RATE * duration);
    const noiseBuffer = ctx.createBuffer(1, bufferSize, SAMPLE_RATE);
    const data = noiseBuffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
    }
    const noiseSource = ctx.createBufferSource();
    noiseSource.buffer = noiseBuffer;

    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = 'bandpass';
    noiseFilter.frequency.value = 1200;
    noiseFilter.Q.value = 0.8;

    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.5, startTime);
    noiseGain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

    noiseSource.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(ctx.destination);

    // Tone component
    const osc = ctx.createOscillator();
    const oscGain = ctx.createGain();
    osc.frequency.value = 200;
    oscGain.gain.setValueAtTime(0.4, startTime);
    oscGain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.08);

    osc.connect(oscGain);
    oscGain.connect(ctx.destination);

    noiseSource.start(startTime);
    noiseSource.stop(startTime + duration);
    osc.start(startTime);
    osc.stop(startTime + 0.08);
}

/**
 * Hi-hat: filtered noise, short and bright
 */
async function synthHiHat(ctx, startTime, duration = 0.06) {
    const bufferSize = Math.ceil(SAMPLE_RATE * duration);
    const noiseBuffer = ctx.createBuffer(1, bufferSize, SAMPLE_RATE);
    const data = noiseBuffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
    }

    const noiseSource = ctx.createBufferSource();
    noiseSource.buffer = noiseBuffer;

    const filter = ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.value = 8000;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.25, startTime);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

    noiseSource.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    noiseSource.start(startTime);
    noiseSource.stop(startTime + duration);
}

/**
 * Clap: burst of noise, slightly longer, with slight reverb character
 */
async function synthClap(ctx, startTime, duration = 0.12) {
    const bufferSize = Math.ceil(SAMPLE_RATE * duration);
    const noiseBuffer = ctx.createBuffer(1, bufferSize, SAMPLE_RATE);
    const data = noiseBuffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
    }

    const noiseSource = ctx.createBufferSource();
    noiseSource.buffer = noiseBuffer;

    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 2000;
    filter.Q.value = 1.5;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.6, startTime);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

    noiseSource.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    noiseSource.start(startTime);
    noiseSource.stop(startTime + duration);
}

// ─── Schedule events ──────────────────────────────────────────────────────────

const ctx = new OfflineAudioContext(NUM_CHANNELS, Math.ceil(SAMPLE_RATE * TOTAL_SECONDS), SAMPLE_RATE);

let scheduledCount = 0;
for (const event of events) {
    const cycleStart = event.whole.begin.valueOf();
    const startTime = cycleStart * SECONDS_PER_CYCLE;

    if (startTime >= TOTAL_SECONDS) continue;

    const instrument = String(event.value);
    scheduledCount++;

    switch (instrument) {
        case 'bd':
            await synthKick(ctx, startTime);
            break;
        case 'sd':
            await synthSnare(ctx, startTime);
            break;
        case 'hh':
            await synthHiHat(ctx, startTime);
            break;
        case 'cp':
            await synthClap(ctx, startTime);
            break;
        default:
            console.warn(`  Unknown instrument: ${instrument}`);
    }
}

console.log(`Scheduled ${scheduledCount} events`);

// ─── Render ───────────────────────────────────────────────────────────────────

console.log('Rendering audio...');
const renderedBuffer = await ctx.startRendering();
console.log(`Rendered ${renderedBuffer.length} samples (${(renderedBuffer.length / SAMPLE_RATE).toFixed(2)}s)`);

// ─── Write WAV ────────────────────────────────────────────────────────────────

function writeWav(filename, audioBuffer) {
    const numChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    const numSamples = audioBuffer.length;
    const bitsPerSample = 16;
    const blockAlign = numChannels * (bitsPerSample / 8);
    const byteRate = sampleRate * blockAlign;
    const dataSize = numSamples * blockAlign;
    const headerSize = 44;
    const buf = Buffer.alloc(headerSize + dataSize);

    // RIFF header
    buf.write('RIFF', 0);
    buf.writeUInt32LE(36 + dataSize, 4);
    buf.write('WAVE', 8);
    buf.write('fmt ', 12);
    buf.writeUInt32LE(16, 16); // fmt chunk size
    buf.writeUInt16LE(1, 20);  // PCM
    buf.writeUInt16LE(numChannels, 22);
    buf.writeUInt32LE(sampleRate, 24);
    buf.writeUInt32LE(byteRate, 28);
    buf.writeUInt16LE(blockAlign, 32);
    buf.writeUInt16LE(bitsPerSample, 34);
    buf.write('data', 36);
    buf.writeUInt32LE(dataSize, 40);

    // Write PCM samples (interleaved if stereo)
    let offset = 44;
    const channelData = [];
    for (let c = 0; c < numChannels; c++) {
        channelData.push(audioBuffer.getChannelData(c));
    }

    for (let i = 0; i < numSamples; i++) {
        for (let c = 0; c < numChannels; c++) {
            const sample = Math.max(-1, Math.min(1, channelData[c][i]));
            const int16 = sample < 0
                ? Math.ceil(sample * 32768)
                : Math.floor(sample * 32767);
            buf.writeInt16LE(int16, offset);
            offset += 2;
        }
    }

    writeFileSync(filename, buf);
    console.log(`WAV written: ${filename} (${(buf.length / 1024).toFixed(1)} KB)`);
}

writeWav('./output.wav', renderedBuffer);
console.log('\n✓ Done! Play output.wav to hear the result.');
console.log('  (e.g.: afplay output.wav  on macOS)');
