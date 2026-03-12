// Starforge Coding Ambient — evolving generative music for terminal coding
// Run: chuck LABS/chuck-music/coding-ambient.ck
// Ctrl-C to stop

// === MASTER OUTPUT ===
Gain master => NRev reverb => dac;
0.08 => reverb.mix;
0.35 => master.gain;

// === PAD: slow evolving chords ===
fun void pad() {
    // Pentatonic minor scale degrees (dark, spacey)
    [48, 51, 53, 55, 58, 60, 63, 65, 67, 70] @=> int notes[];

    // Two detuned oscillators for thickness
    TriOsc p1 => LPF filt1 => Gain padGain => master;
    TriOsc p2 => LPF filt2 => padGain;
    0.12 => padGain.gain;
    800.0 => filt1.freq;
    750.0 => filt2.freq;
    3.0 => filt1.Q;
    3.0 => filt2.Q;

    while (true) {
        // Pick two notes for a chord
        Math.random2(0, notes.size()-1) => int idx1;
        (idx1 + Math.random2(2, 4)) % notes.size() => int idx2;

        Std.mtof(notes[idx1]) => p1.freq;
        Std.mtof(notes[idx2]) * 1.003 => p2.freq; // slight detune

        // Slow filter sweep
        Math.random2f(400.0, 1200.0) => float targetFreq;
        filt1.freq() => float startFreq;
        for (0 => int i; i < 100; i++) {
            startFreq + (targetFreq - startFreq) * (i / 100.0) => filt1.freq;
            startFreq + (targetFreq - startFreq) * (i / 100.0) * 0.95 => filt2.freq;
            40::ms => now;
        }
        Math.random2(2000, 5000)::ms => now;
    }
}

// === PULSE: rhythmic element, euclidean-inspired ===
fun int[] bjorklund(int k, int n) {
    // Euclidean rhythm generator
    int result[n];
    if (k >= n) {
        for (0 => int i; i < n; i++) 1 => result[i];
        return result;
    }
    if (k == 0) {
        for (0 => int i; i < n; i++) 0 => result[i];
        return result;
    }

    int pattern[n];
    float bucket;
    0.0 => bucket;
    k $ float / n => float slope;
    for (0 => int i; i < n; i++) {
        bucket + slope => bucket;
        if (bucket >= 1.0) {
            1 => pattern[i];
            bucket - 1.0 => bucket;
        } else {
            0 => pattern[i];
        }
    }
    return pattern;
}

fun void pulse() {
    SqrOsc sq => LPF filt => Gain pulseGain => master;
    0.06 => pulseGain.gain;
    2000.0 => filt.freq;
    2.0 => filt.Q;

    // Evolving euclidean parameters
    3 => int k;
    8 => int n;

    [36, 38, 41, 43, 46] @=> int bassNotes[]; // low pentatonic
    0 => int noteIdx;

    0 => int cycleCount;

    while (true) {
        bjorklund(k, n) @=> int rhythm[];

        for (0 => int i; i < rhythm.size(); i++) {
            if (rhythm[i]) {
                Std.mtof(bassNotes[noteIdx]) => sq.freq;
                0.06 => pulseGain.gain;

                // Quick decay
                for (0 => int d; d < 10; d++) {
                    pulseGain.gain() * 0.85 => pulseGain.gain;
                    15::ms => now;
                }
            } else {
                0.0 => pulseGain.gain;
                150::ms => now;
            }
        }

        cycleCount++;
        // Evolve every 4 cycles
        if (cycleCount % 4 == 0) {
            Math.random2(2, 5) => k;
            Math.random2(7, 13) => n;
            (noteIdx + Math.random2(1, 3)) % bassNotes.size() => noteIdx;
        }
    }
}

// === HIHAT: gentle tick pattern ===
fun void hihat() {
    Noise noise => BPF bp => Gain hhGain => master;
    8000.0 => bp.freq;
    4.0 => bp.Q;
    0.0 => hhGain.gain;

    while (true) {
        // Random density: sometimes busy, sometimes sparse
        Math.random2(2, 6) => int density;

        for (0 => int i; i < 16; i++) {
            if (Math.random2(0, 8) < density) {
                Math.random2f(0.02, 0.06) => hhGain.gain;
                5::ms => now;
                0.0 => hhGain.gain;
                Math.random2(80, 200)::ms => now;
            } else {
                Math.random2(100, 250)::ms => now;
            }
        }
    }
}

// === MELODY: sparse, floating notes ===
fun void melody() {
    SinOsc mel => LPF filt => Gain melGain => master;
    0.0 => melGain.gain;
    3000.0 => filt.freq;

    [60, 63, 65, 67, 70, 72, 75, 77] @=> int notes[]; // high pentatonic

    while (true) {
        // 40% chance of playing a note
        if (Math.random2f(0.0, 1.0) < 0.4) {
            Math.random2(0, notes.size()-1) => int idx;
            Std.mtof(notes[idx]) => mel.freq;

            // Gentle attack
            for (0 => int a; a < 20; a++) {
                (a / 20.0) * Math.random2f(0.04, 0.08) => melGain.gain;
                8::ms => now;
            }
            // Hold
            Math.random2(200, 600)::ms => now;
            // Gentle release
            melGain.gain() => float vol;
            for (0 => int r; r < 30; r++) {
                vol * (1.0 - r / 30.0) => melGain.gain;
                10::ms => now;
            }
            0.0 => melGain.gain;
        }

        Math.random2(500, 2000)::ms => now;
    }
}

// === LAUNCH ALL SHREDS ===
<<< "  Starforge Coding Ambient", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ pad();
spork ~ pulse();
spork ~ hihat();
spork ~ melody();

// Keep main shred alive
while (true) 1::second => now;
