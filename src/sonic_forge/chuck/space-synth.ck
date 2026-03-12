// Starforge Space Synth — organic evolving synthesizer journey
// Long decays, drifting notes, chippy arpeggios, singing bowl resonance
// Meant to play for hours. Never repeats.
// Run: chuck LABS/chuck-music/space-synth.ck

Gain master => NRev reverb => dac;
0.2 => reverb.mix;
0.35 => master.gain;

// Pentatonic scales — always sounds good, easy to drift between
[48, 51, 53, 55, 58, 60, 63, 65, 67, 70, 72, 75, 77, 79, 82] @=> int penta[];

// ============================================================
// SINGING BOWL LAYER — long resonant tones, irregular spacing
// ============================================================
fun void bowlTone(float freq, float vol, float decaySec) {
    SinOsc f1 => Gain g => master;
    SinOsc f2 => g;  // inharmonic partial
    SinOsc f3 => g;  // beating pair
    SinOsc f4 => g;  // high partial

    freq => f1.freq;
    freq * 2.71 => f2.freq;
    freq * 1.002 => f3.freq;
    freq * 4.53 => f4.freq;

    vol => g.gain;
    0.5 => f1.gain;
    0.25 => f2.gain;
    0.45 => f3.gain;
    0.1 => f4.gain;

    // Very long exponential decay
    (decaySec * 1000.0) $ int => int totalMs;
    totalMs / 80 => int stepMs;
    if (stepMs < 30) 30 => stepMs;

    for (0 => int i; i < 80; i++) {
        vol * Math.pow(0.965, i $ float) => g.gain;
        // Higher partials fade faster
        0.1 * Math.pow(0.94, i $ float) => f4.gain;
        0.25 * Math.pow(0.96, i $ float) => f2.gain;
        stepMs::ms => now;
    }
    0.0 => g.gain;
    g =< master; f1 =< g; f2 =< g; f3 =< g; f4 =< g;
}

fun void bowls() {
    while (true) {
        // Pick from pentatonic — favor middle-high register
        Math.random2(4, penta.size()-1) => int idx;
        Std.mtof(penta[idx]) => float freq;

        Math.random2f(0.03, 0.07) => float vol;
        Math.random2f(8.0, 20.0) => float decay;  // 8-20 second tails

        spork ~ bowlTone(freq, vol, decay);

        // Organic spacing: sometimes close together, sometimes far apart
        if (Math.random2f(0.0, 1.0) < 0.3) {
            // Cluster: quick follow-up
            Math.random2(800, 2000)::ms => now;
        } else if (Math.random2f(0.0, 1.0) < 0.3) {
            // Long silence
            Math.random2(6000, 12000)::ms => now;
        } else {
            // Normal
            Math.random2(3000, 7000)::ms => now;
        }
    }
}

// ============================================================
// CHIPPY ARPEGGIOS — gameboy square waves, long tails
// ============================================================
fun void chippyNote(float freq, float vol, float decaySec) {
    SqrOsc sq => LPF filt => Gain g => master;
    freq => sq.freq;
    freq * 4.0 => filt.freq;
    2.0 => filt.Q;
    vol => g.gain;

    (decaySec * 1000.0) $ int => int totalMs;
    totalMs / 60 => int stepMs;
    if (stepMs < 20) 20 => stepMs;

    for (0 => int i; i < 60; i++) {
        vol * Math.pow(0.955, i $ float) => g.gain;
        // Filter closes slowly
        filt.freq() * 0.99 => float ff;
        if (ff < 300.0) 300.0 => ff;
        ff => filt.freq;
        stepMs::ms => now;
    }
    0.0 => g.gain;
    g =< master; sq =< filt; filt =< g;
}

fun void chippyArp() {
    // Start index into pentatonic
    Math.random2(0, 5) => int baseIdx;
    0 => int direction;  // 0=up, 1=down, 2=random

    while (true) {
        // Play a short arpeggio run (3-6 notes)
        Math.random2(3, 6) => int runLen;
        Math.random2(0, 2) => direction;

        for (0 => int n; n < runLen; n++) {
            int idx;
            if (direction == 0) {
                (baseIdx + n) % penta.size() => idx;
            } else if (direction == 1) {
                (baseIdx - n + penta.size()) % penta.size() => idx;
            } else {
                Math.random2(baseIdx, Math.min(baseIdx + 5, penta.size()-1)) => idx;
            }

            Std.mtof(penta[idx]) => float freq;
            Math.random2f(0.03, 0.06) => float vol;
            Math.random2f(2.0, 5.0) => float decay;

            spork ~ chippyNote(freq, vol, decay);

            // Arp speed varies
            Math.random2(80, 200)::ms => now;
        }

        // Drift the base note
        baseIdx + Math.random2(-2, 3) => baseIdx;
        if (baseIdx < 0) 0 => baseIdx;
        if (baseIdx >= penta.size() - 3) penta.size() - 4 => baseIdx;

        // Gap between runs — sometimes long, sometimes short
        if (Math.random2f(0.0, 1.0) < 0.25) {
            // Quick follow-up
            Math.random2(500, 1500)::ms => now;
        } else {
            Math.random2(3000, 9000)::ms => now;
        }
    }
}

// ============================================================
// PAD — detuned triangle waves, slow evolving chords
// ============================================================
fun void pad() {
    TriOsc t1 => LPF filt => Gain padGain => master;
    TriOsc t2 => filt;
    TriOsc t3 => filt;
    0.06 => padGain.gain;
    600.0 => filt.freq;
    3.0 => filt.Q;

    while (true) {
        // Pick a chord from pentatonic (root + 3rd + 5th in scale)
        Math.random2(0, 6) => int root;
        penta[root] => int n1;
        penta[(root + 2) % penta.size()] => int n2;
        penta[(root + 4) % penta.size()] => int n3;

        Std.mtof(n1) => float f1;
        Std.mtof(n2) * 1.003 => float f2;  // slight detune
        Std.mtof(n3) * 0.998 => float f3;  // slight detune other way

        // Snap to new chord
        f1 => t1.freq;
        f2 => t2.freq;
        f3 => t3.freq;

        // Slow filter sweep + volume breathing (no pitch glide)
        Math.random2f(300.0, 900.0) => float filtTarget;
        filt.freq() => float filtStart;

        for (0 => int i; i < 150; i++) {
            i / 150.0 => float t;
            filtStart + (filtTarget - filtStart) * t => filt.freq;
            0.06 * (0.7 + 0.3 * Math.sin(i * 0.08)) => padGain.gain;
            50::ms => now;
        }

        // Hold
        Math.random2(4000, 10000)::ms => now;
    }
}

// ============================================================
// SUB — very deep, barely there, grounds everything
// ============================================================
fun void sub() {
    SinOsc s => Gain sg => master;
    0.0 => sg.gain;

    while (true) {
        // Pick a deep root
        Std.mtof(penta[Math.random2(0, 3)] - 12) => float freq;  // octave below low penta
        freq => s.freq;

        // Slow swell
        for (0 => int i; i < 60; i++) {
            0.06 * Math.sin(Math.PI * i / 60.0) => sg.gain;
            60::ms => now;
        }

        // Gentle fade
        for (0 => int i; i < 40; i++) {
            sg.gain() * 0.95 => sg.gain;
            50::ms => now;
        }
        0.0 => sg.gain;

        Math.random2(4000, 12000)::ms => now;
    }
}

// ============================================================
// SHIMMER — occasional high sine sparkles
// ============================================================
fun void sparkle(float freq, float vol) {
    SinOsc s => Gain g => master;
    freq => s.freq;
    vol => g.gain;

    for (0 => int i; i < 40; i++) {
        vol * Math.pow(0.92, i $ float) => g.gain;
        30::ms => now;
    }
    0.0 => g.gain;
    g =< master; s =< g;
}

fun void shimmer() {
    while (true) {
        // Rare sparkles — high register
        if (Math.random2f(0.0, 1.0) < 0.3) {
            Math.random2(9, penta.size()-1) => int idx;
            Std.mtof(penta[idx] + 12) => float freq;  // octave up
            Math.random2f(0.015, 0.035) => float vol;
            spork ~ sparkle(freq, vol);
        }
        Math.random2(2000, 6000)::ms => now;
    }
}

// ============================================================
// LAUNCH
// ============================================================
<<< "  Starforge Space Synth", "" >>>;
<<< "  organic evolving journey — synthesizers + bowls + arpeggios", "" >>>;
<<< "  never repeats. play for hours.", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ pad();
spork ~ bowls();
spork ~ chippyArp();
spork ~ sub();
spork ~ shimmer();

while (true) 1::second => now;
