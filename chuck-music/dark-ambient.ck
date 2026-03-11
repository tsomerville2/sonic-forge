// Starforge Dark Ambient — sinister drones, metallic resonance, industrial hum
// 6-minute arc: silence → creep → swell → breathe → dread → fade
// Run: chuck LABS/chuck-music/dark-ambient.ck

Gain master => NRev reverb => dac;
0.35 => reverb.mix;
0.3 => master.gain;

// Shared state
float tension;
float songTime;
float SONG_LENGTH;
360.0 => SONG_LENGTH;  // 6 minutes default
if (me.args() > 0) Std.atof(me.arg(0)) * 60.0 => SONG_LENGTH;

// Tension curve — slow dread build (starts audible, not silent)
[  0.0, 0.25,
  30.0, 0.30,
  60.0, 0.40,
  90.0, 0.55,
 120.0, 0.20,     // pull back
 150.0, 0.55,
 180.0, 0.75,     // peak dread
 210.0, 0.35,     // breathe
 240.0, 0.85,     // darkest moment
 270.0, 0.60,
 300.0, 0.35,
 330.0, 0.20,
 360.0, 0.10
] @=> float curve[];

fun float tensionAt(float t) {
    t * 360.0 / SONG_LENGTH => t;  // scale arc to fit song length
    if (t <= 0.0) return curve[1];
    if (t >= 360.0) return curve[curve.size()-1];
    for (0 => int i; i < curve.size() - 2; 2 +=> i) {
        curve[i] => float t0; curve[i+1] => float v0;
        curve[i+2] => float t1; curve[i+3] => float v1;
        if (t >= t0 && t < t1) {
            return v0 + (v1 - v0) * ((t - t0) / (t1 - t0));
        }
    }
    return curve[curve.size()-1];
}

// ============================================================
// CONDUCTOR
// ============================================================
fun void conductor() {
    0.0 => songTime;
    while (true) {
        tensionAt(songTime) => tension;
        // More reverb at low tension, tighter at peak
        0.45 - tension * 0.2 => reverb.mix;
        0.25 + tension * 0.15 => master.gain;

        100::ms => now;
        0.1 +=> songTime;
        if (songTime >= SONG_LENGTH) 0.0 => songTime;
    }
}

// ============================================================
// SUB DRONE — two detuned sines, very low, always present
// ============================================================
fun void subDrone() {
    SinOsc s1 => LPF filt => Gain dg => master;
    SinOsc s2 => filt;
    35.0 => s1.freq;
    35.07 => s2.freq;  // very slow beating
    200.0 => filt.freq;
    2.0 => filt.Q;
    0.08 => dg.gain;

    [29, 24, 31, 27] @=> int roots[];
    0 => int rootIdx;

    while (true) {
        Std.mtof(roots[rootIdx]) / 4.0 => float target;
        s1.freq() => float start;
        if (start < 10.0) target => start;

        // Glacial glide
        for (0 => int i; i < 200; i++) {
            start + (target - start) * (i / 200.0) => float f;
            f => s1.freq;
            f * 1.002 => s2.freq;
            // Filter opens with tension
            120.0 + tension * 150.0 => filt.freq;
            0.06 + tension * 0.06 => dg.gain;
            50::ms => now;
        }

        if (Math.random2(0, 3) == 0) {
            (rootIdx + 1) % roots.size() => rootIdx;
        }
        Math.random2(3000, 8000)::ms => now;
    }
}

// ============================================================
// DARK PAD — 4 detuned saws, very filtered, ominous
// ============================================================
fun void darkPad() {
    SawOsc p1 => LPF filt => Gain pg => master;
    SawOsc p2 => filt;
    SawOsc p3 => filt;
    SawOsc p4 => filt;
    180.0 => filt.freq;
    6.0 => filt.Q;
    0.05 => pg.gain;

    [29, 27, 31, 24] @=> int notes[];
    0 => int idx;

    while (true) {
        // Enter at tension > 0.1
        if (tension < 0.1) { 500::ms => now; continue; }

        Std.mtof(notes[idx]) => float root;
        root * 0.498 => p1.freq;
        root * 0.502 => p2.freq;
        root * 0.997 => p3.freq;
        root * 1.003 => p4.freq;

        // Very slow filter sweep following tension
        for (0 => int i; i < 100; i++) {
            120.0 + tension * tension * 1000.0 => float fTarget;
            filt.freq() + (fTarget - filt.freq()) * 0.02 => filt.freq;
            0.04 + tension * 0.1 => pg.gain;
            60::ms => now;
        }

        if (Math.random2(0, 2) == 0) {
            (idx + 1) % notes.size() => idx;
        }
        Math.random2(1000, 3000)::ms => now;
    }
}

// ============================================================
// METALLIC RESONANCE — filtered noise pings, like distant metal
// ============================================================
fun void metallicPing(float freq, float vol) {
    Noise n => BPF bp => Gain g => master;
    freq => bp.freq;
    30.0 => bp.Q;  // very narrow = metallic ring
    vol => g.gain;

    for (0 => int i; i < 60; i++) {
        vol * Math.pow(0.94, i $ float) => g.gain;
        // Pitch drifts slightly
        freq * (1.0 + Math.sin(i * 0.1) * 0.01) => bp.freq;
        25::ms => now;
    }
    0.0 => g.gain;
    g =< master; n =< bp; bp =< g;
}

fun void metalResonance() {
    [800.0, 1200.0, 2400.0, 3600.0, 5000.0, 1800.0] @=> float freqs[];

    while (true) {
        // More pings at higher tension
        if (Math.random2f(0.0, 1.0) < tension * 0.7) {
            freqs[Math.random2(0, freqs.size()-1)] => float freq;
            Math.random2f(0.02, 0.06) * tension => float vol;
            spork ~ metallicPing(freq, vol);
        }

        Math.random2(800, 4000)::ms => now;
    }
}

// ============================================================
// INDUSTRIAL HUM — low filtered noise, pulses with tension
// ============================================================
fun void industrialHum() {
    Noise n => LPF filt => Gain hg => master;
    80.0 => filt.freq;
    4.0 => filt.Q;
    0.0 => hg.gain;

    while (true) {
        // Fades in above 0.15 tension
        if (tension < 0.15) {
            hg.gain() * 0.95 => float g;
            if (g < 0.001) 0.0 => g;
            g => hg.gain;
            200::ms => now;
            continue;
        }

        // Volume and filter track tension
        float targetGain;
        tension * 0.04 => targetGain;
        hg.gain() + (targetGain - hg.gain()) * 0.05 => hg.gain;
        40.0 + tension * 120.0 => float fTarget;
        filt.freq() + (fTarget - filt.freq()) * 0.03 => filt.freq;

        // Occasional pulse — volume bump
        if (Math.random2f(0.0, 1.0) < 0.02) {
            hg.gain() * 1.8 => hg.gain;
        }

        80::ms => now;
    }
}

// ============================================================
// GHOST VOICE — very high, very quiet sine sweeps
// ============================================================
fun void ghostSweep(float startFreq, float endFreq, float vol) {
    SinOsc s => Gain g => master;
    startFreq => s.freq;
    0.0 => g.gain;

    // Fade in
    for (0 => int i; i < 30; i++) {
        vol * (i / 30.0) => g.gain;
        startFreq + (endFreq - startFreq) * (i / 120.0) => s.freq;
        30::ms => now;
    }
    // Sustain + sweep
    for (30 => int i; i < 90; i++) {
        startFreq + (endFreq - startFreq) * (i / 120.0) => s.freq;
        vol * (0.8 + 0.2 * Math.sin(i * 0.15)) => g.gain;
        30::ms => now;
    }
    // Fade out
    for (0 => int i; i < 30; i++) {
        g.gain() * 0.9 => g.gain;
        30::ms => now;
    }
    0.0 => g.gain;
    g =< master; s =< g;
}

fun void ghostVoices() {
    3000::ms => now;
    while (true) {
        if (tension > 0.2 && Math.random2f(0.0, 1.0) < tension * 0.4) {
            Math.random2f(2000.0, 6000.0) => float startF;
            startF + Math.random2f(-800.0, 800.0) => float endF;
            Math.random2f(0.008, 0.02) => float vol;
            spork ~ ghostSweep(startF, endF, vol);
        }
        Math.random2(3000, 10000)::ms => now;
    }
}

// ============================================================
// HEARTBEAT — sparse, deep, irregular pulse at high tension
// ============================================================
fun void heartbeat() {
    while (true) {
        if (tension < 0.4) { 1000::ms => now; continue; }

        // Double-tap like a heartbeat
        for (0 => int tap; tap < 2; tap++) {
            SinOsc s => Gain g => master;
            40.0 => s.freq;
            tension * 0.06 => g.gain;

            for (0 => int i; i < 15; i++) {
                40.0 - (i * 1.5) => s.freq;
                g.gain() * 0.88 => g.gain;
                8::ms => now;
            }
            g =< master; s =< g;

            if (tap == 0) 120::ms => now;  // gap between double-tap
        }

        // Irregular spacing — faster at higher tension
        Math.random2(1500, (4000.0 - tension * 2000.0) $ int)::ms => now;
    }
}

// ============================================================
// LAUNCH
// ============================================================
<<< "  Starforge Dark Ambient", "" >>>;
<<< "  sinister drones, metallic resonance, industrial hum", "" >>>;
<<< "  6-min arc: silence > creep > dread > breathe > dark > fade", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ conductor();
spork ~ subDrone();
spork ~ darkPad();
spork ~ metalResonance();
spork ~ industrialHum();
spork ~ ghostVoices();
spork ~ heartbeat();

while (true) 1::second => now;
