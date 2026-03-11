// Starforge Cathedral Drift — deep reverb pads that slowly transform
// Inspired by your love of the "cathedral" bytebeat formula
// Run: chuck LABS/chuck-music/cathedral-drift.ck

Gain master => NRev reverb => dac;
0.15 => reverb.mix;  // heavy reverb for cathedral feel
0.3 => master.gain;

// === DRONE: low fundamental that shifts ===
fun void drone() {
    SawOsc saw1 => LPF filt => Gain droneGain => master;
    SawOsc saw2 => filt;
    0.06 => droneGain.gain;
    300.0 => filt.freq;
    4.0 => filt.Q;

    [36, 38, 41, 43, 34, 31] @=> int roots[]; // deep roots
    0 => int idx;

    while (true) {
        Std.mtof(roots[idx]) => float targetFreq;
        saw1.freq() => float startFreq;
        if (startFreq < 10.0) targetFreq => startFreq;

        // Glacial glide to new note
        for (0 => int i; i < 200; i++) {
            startFreq + (targetFreq - startFreq) * (i / 200.0) => saw1.freq;
            (startFreq + (targetFreq - startFreq) * (i / 200.0)) * 1.005 => saw2.freq;
            25::ms => now;
        }

        // Hold
        Math.random2(3000, 8000)::ms => now;

        (idx + Math.random2(1, 3)) % roots.size() => idx;
    }
}

// === BELLS: sine harmonics that ring and fade ===
fun void bell(float freq, float vol, dur length) {
    SinOsc s1 => Gain g => master;
    SinOsc s2 => g;
    SinOsc s3 => g;
    freq => s1.freq;
    freq * 2.756 => s2.freq;  // inharmonic partial (bell-like)
    freq * 5.404 => s3.freq;  // higher inharmonic
    vol => g.gain;

    // Exponential decay
    length / 50 => dur step;
    for (0 => int i; i < 50; i++) {
        vol * Math.pow(0.92, i $ float) => g.gain;
        step => now;
    }
    0.0 => g.gain;
}

fun void bells() {
    [60, 63, 67, 70, 72, 75, 79, 84] @=> int notes[];

    while (true) {
        // Sparse — sometimes play, sometimes rest
        if (Math.random2f(0.0, 1.0) < 0.35) {
            Math.random2(0, notes.size()-1) => int idx;
            spork ~ bell(Std.mtof(notes[idx]),
                        Math.random2f(0.02, 0.05),
                        Math.random2(2000, 5000)::ms);
        }
        Math.random2(800, 3000)::ms => now;
    }
}

// === MORE BELLS: second bell layer with different tuning ===
fun void bellsLow() {
    // Lower register bells with longer decay
    [48, 51, 53, 55, 58, 60] @=> int notes[];

    while (true) {
        if (Math.random2f(0.0, 1.0) < 0.25) {
            Math.random2(0, notes.size()-1) => int idx;
            spork ~ bell(Std.mtof(notes[idx]),
                        Math.random2f(0.015, 0.035),
                        Math.random2(3000, 7000)::ms);
        }
        Math.random2(1500, 5000)::ms => now;
    }
}

// === SUB PULSE: very deep, slow ===
fun void subPulse() {
    SinOsc sub => Gain subGain => master;
    0.0 => subGain.gain;

    [29, 31, 34, 36] @=> int notes[]; // very low
    0 => int idx;

    while (true) {
        Std.mtof(notes[idx]) => sub.freq;

        // Slow fade in/out
        for (0 => int i; i < 60; i++) {
            0.1 * Math.sin(Math.PI * i / 60.0) => subGain.gain;
            50::ms => now;
        }
        0.0 => subGain.gain;

        Math.random2(2000, 6000)::ms => now;
        (idx + 1) % notes.size() => idx;
    }
}

// === LAUNCH ===
<<< "  Starforge Cathedral Drift", "" >>>;
<<< "  Deep reverb ambient — slow transformation", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ drone();
spork ~ bells();
spork ~ bellsLow();
spork ~ subPulse();

while (true) 1::second => now;
