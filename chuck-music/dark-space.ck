// Starforge Dark Space — 80s laser show synthesizers with song arc
// Tension curve drives everything: filter, layers, density, reverb
// 6-minute journey: sparse drone → build → climax → breathe → peak → fade
// Run: chuck LABS/chuck-music/dark-space.ck

Gain master => dac;
0.35 => master.gain;

// Reverb with variable wet/dry controlled by tension
NRev reverb => dac;
0.0 => reverb.gain;
0.95 => reverb.mix;

// Dark minor scale
[36, 39, 41, 43, 46, 48, 51, 53, 55, 58, 60, 63, 65, 67, 70, 72] @=> int scale[];

// ============================================================
// TENSION ENGINE — the arc of the song
// ============================================================
float tension;      // 0.0 to 1.0, drives everything
float songTime;     // seconds since start
float SONG_LENGTH;
360.0 => SONG_LENGTH;  // 6 minutes default
if (me.args() > 0) Std.atof(me.arg(0)) * 60.0 => SONG_LENGTH;

// Piecewise tension curve — the emotional arc
// Time(sec) → Tension
// 0    → 0.05  (drone only, dark)
// 30   → 0.10  (sub enters)
// 60   → 0.25  (bass, first hints)
// 90   → 0.40  (pad opens, lead hints)
// 120  → 0.20  (BREAKDOWN: strip back, breathe)
// 150  → 0.55  (rebuild, fuller)
// 180  → 0.80  (FIRST CLIMAX — all layers, filter open)
// 210  → 0.45  (breathe again — pads only)
// 240  → 0.90  (SECOND CLIMAX — peak, everything wide)
// 270  → 0.70  (sustain high energy)
// 300  → 0.35  (outro begins, layers peel)
// 330  → 0.10  (drone + reverb tail)
// 360  → 0.02  (silence)

// Keyframes: [time_seconds, tension]
[  0.0, 0.05,
  30.0, 0.10,
  60.0, 0.25,
  90.0, 0.40,
 120.0, 0.20,
 150.0, 0.55,
 180.0, 0.80,
 210.0, 0.45,
 240.0, 0.90,
 270.0, 0.70,
 300.0, 0.35,
 330.0, 0.10,
 360.0, 0.02
] @=> float curve[];

fun float tensionAt(float t) {
    // Scale time so the full arc fits SONG_LENGTH (curves authored for 360s)
    t * 360.0 / SONG_LENGTH => t;
    if (t <= 0.0) return curve[1];
    if (t >= 360.0) return curve[curve.size()-1];

    for (0 => int i; i < curve.size() - 2; 2 +=> i) {
        curve[i] => float t0;
        curve[i+1] => float v0;
        curve[i+2] => float t1;
        curve[i+3] => float v1;
        if (t >= t0 && t < t1) {
            (t - t0) / (t1 - t0) => float frac;
            return v0 + (v1 - v0) * frac;
        }
    }
    return curve[curve.size()-1];
}

// Derived parameters from tension
fun float lpfFreq() { return 150.0 + tension * tension * 6000.0; }
fun float revWet()  { return 0.95 - tension * 0.55; }
fun float padVol()  { return 0.03 + tension * 0.08; }

// Conductor: updates tension every 100ms
fun void conductor() {
    0.0 => songTime;
    while (true) {
        tensionAt(songTime) => tension;
        // Reverb follows tension (more reverb when sparse, less when dense)
        revWet() => reverb.mix;
        // Master volume slight boost at climax
        0.3 + tension * 0.15 => master.gain;

        0.1 => float dt;
        (dt * 1000.0) $ int => int stepMs;
        stepMs::ms => now;
        dt +=> songTime;

        // Loop the song
        if (songTime >= SONG_LENGTH) {
            0.0 => songTime;
        }
    }
}

// ============================================================
// SUPERSAW PAD — 6 detuned saws, filter driven by tension
// ============================================================
fun void superSawPad() {
    SawOsc s1 => LPF filt => Gain pg => master;
    SawOsc s2 => filt;
    SawOsc s3 => filt;
    SawOsc s4 => filt;
    SawOsc s5 => filt;
    SawOsc s6 => filt;
    pg => reverb;
    0.05 => pg.gain;
    200.0 => filt.freq;
    4.0 => filt.Q;

    [1.0, 0.993, 1.007, 0.997, 1.003, 1.01] @=> float det[];

    [[36, 39, 43, 48],
     [34, 39, 41, 46],
     [31, 36, 39, 43],
     [29, 34, 36, 41],
     [36, 41, 43, 48],
     [34, 38, 41, 46]
    ] @=> int chords[][];
    0 => int chIdx;

    while (true) {
        chords[chIdx] @=> int ch[];
        Std.mtof(ch[0]) => float root;
        Std.mtof(ch[1]) => float third;
        Std.mtof(ch[2]) => float fifth;
        Std.mtof(ch[3]) => float oct;

        s1.freq() => float sf1; s2.freq() => float sf2;
        s3.freq() => float sf3; s4.freq() => float sf4;
        s5.freq() => float sf5; s6.freq() => float sf6;
        if (sf1 < 10.0) {
            root * det[0] => sf1; root * det[1] => sf2;
            fifth * det[2] => sf3; fifth * det[3] => sf4;
            third * det[4] => sf5; oct * det[5] => sf6;
        }

        // Glide to new chord — speed depends on tension
        Math.max(150, 500 - (tension * 300.0) $ int) => int steps;

        for (0 => int i; i < steps; i++) {
            i $ float / steps => float t;

            sf1 + (root * det[0] - sf1) * t => s1.freq;
            sf2 + (root * det[1] - sf2) * t => s2.freq;
            sf3 + (fifth * det[2] - sf3) * t => s3.freq;
            sf4 + (fifth * det[3] - sf4) * t => s4.freq;
            sf5 + (third * det[4] - sf5) * t => s5.freq;
            sf6 + (oct * det[5] - sf6) * t => s6.freq;

            // Filter follows tension curve
            lpfFreq() => filt.freq;
            padVol() => pg.gain;

            // Q increases slightly at mid-tension (resonance peak during build)
            3.0 + 4.0 * Math.sin(tension * Math.PI) => filt.Q;

            50::ms => now;
        }

        // Hold — shorter at high tension (more changes), longer at low
        (2000 + ((1.0 - tension) * 6000.0) $ int)::ms => now;

        (chIdx + Math.random2(1, 3)) % chords.size() => chIdx;
    }
}

// ============================================================
// EPIC LEAD — only plays when tension > 0.35
// ============================================================
fun void epicLead() {
    SawOsc l1 => LPF filt => Gain lg => master;
    SawOsc l2 => filt;
    SinOsc lsin => filt;
    lg => reverb;
    0.0 => lg.gain;
    2000.0 => filt.freq;
    3.0 => filt.Q;
    0.7 => l2.gain;
    0.5 => lsin.gain;

    while (true) {
        if (tension < 0.35) {
            // Not time yet — wait
            500::ms => now;
            continue;
        }

        // Play a phrase
        Math.random2(3, 5 + (tension * 4.0) $ int) => int phraseLen;
        Math.random2(5, scale.size()-1) => int notePos;

        for (0 => int n; n < phraseLen; n++) {
            if (tension < 0.3) break;  // cut phrase if tension drops

            (notePos + Math.random2(-2, 3)) => notePos;
            if (notePos < 4) 4 => notePos;
            if (notePos >= scale.size()) scale.size() - 1 => notePos;

            Std.mtof(scale[notePos]) => float target;
            l1.freq() => float from;
            if (from < 10.0) target => from;

            // Portamento — faster at higher tension
            Math.max(8, (20 - tension * 12.0) $ int) => int glideSteps;
            for (0 => int g; g < glideSteps; g++) {
                from + (target - from) * (g $ float / glideSteps) => float f;
                f => l1.freq;
                f * 1.005 => l2.freq;
                f => lsin.freq;
                (g $ float / glideSteps) * (0.03 + tension * 0.05) => lg.gain;
                12::ms => now;
            }

            // Sustain with vibrato — wider at high tension
            tension * 0.005 => float vibDepth;
            Math.random2(400, 1200)::ms / 20 => dur vibStep;
            for (0 => int v; v < 20; v++) {
                target * (1.0 + vibDepth * Math.sin(v * 0.8)) => l1.freq;
                l1.freq() * 1.005 => l2.freq;
                target * (1.0 + vibDepth * Math.sin(v * 0.8)) => lsin.freq;
                vibStep => now;
            }

            // Decay — longer tail at low tension, snappier at high
            lg.gain() => float peak;
            Math.max(15, (40 - tension * 20.0) $ int) => int decSteps;
            for (0 => int d; d < decSteps; d++) {
                peak * Math.pow(0.93, d $ float) => lg.gain;
                filt.freq() * 0.996 => float ff;
                if (ff < 500.0) 500.0 => ff;
                ff => filt.freq;
                30::ms => now;
            }

            1500.0 + tension * 2000.0 => filt.freq;
        }

        0.0 => lg.gain;
        // Gap between phrases — shorter at high tension
        (3000 + ((1.0 - tension) * 10000.0) $ int)::ms => now;
    }
}

// ============================================================
// BASS — enters at tension > 0.2, deeper and more rhythmic at high
// ============================================================
fun void bassSequence() {
    SawOsc b1 => LPF bf => Gain bg => master;
    SawOsc b2 => bf;
    bg => reverb;
    0.0 => bg.gain;
    400.0 => bf.freq;
    5.0 => bf.Q;

    [36, 34, 31, 29, 36, 39, 34, 31] @=> int line[];
    0 => int step;

    while (true) {
        if (tension < 0.2) {
            500::ms => now;
            continue;
        }

        Std.mtof(line[step]) => float f;
        f => b1.freq;
        f * 1.006 => b2.freq;

        // Volume follows tension
        tension * 0.12 => float targetVol;

        // Attack
        for (0 => int a; a < 10; a++) {
            (a / 10.0) * targetVol => bg.gain;
            300.0 + tension * 800.0 => bf.freq;
            15::ms => now;
        }

        // Filter + volume decay
        for (0 => int s; s < 25; s++) {
            bf.freq() * 0.96 => float ff;
            if (ff < 150.0) 150.0 => ff;
            ff => bf.freq;
            bg.gain() * 0.96 => bg.gain;
            35::ms => now;
        }

        0.0 => bg.gain;
        (step + 1) % line.size() => step;

        // Rhythm: faster notes at higher tension
        (800 + ((1.0 - tension) * 1500.0) $ int)::ms => now;

        // Mutate occasionally
        if (Math.random2(0, 15) == 0) {
            Math.random2(0, line.size()-1) => int idx;
            [29, 31, 34, 36, 39, 41] @=> int opts[];
            opts[Math.random2(0, opts.size()-1)] => line[idx];
        }
    }
}

// ============================================================
// BOWL RESONANCE — more frequent at breakdowns (low tension)
// ============================================================
fun void bowlHit(float freq, float vol, float decaySec) {
    SinOsc f1 => Gain g => reverb;
    SinOsc f2 => g;
    SinOsc f3 => g;
    freq => f1.freq;
    freq * 2.71 => f2.freq;
    freq * 1.002 => f3.freq;
    vol => g.gain;
    0.25 => f2.gain;
    0.45 => f3.gain;

    (decaySec * 1000.0) $ int / 80 => int stepMs;
    if (stepMs < 30) 30 => stepMs;
    for (0 => int i; i < 80; i++) {
        vol * Math.pow(0.965, i $ float) => g.gain;
        stepMs::ms => now;
    }
    0.0 => g.gain;
    g =< reverb; f1 =< g; f2 =< g; f3 =< g;
}

fun void bowls() {
    while (true) {
        // More bowls during breakdowns, sparse during climax
        (1.0 - tension) * 0.5 + 0.1 => float probability;
        if (Math.random2f(0.0, 1.0) < probability) {
            Math.random2(6, scale.size()-1) => int idx;
            Std.mtof(scale[idx]) => float freq;
            spork ~ bowlHit(freq, Math.random2f(0.02, 0.04), Math.random2f(12.0, 22.0));
        }
        Math.random2(3000, 8000)::ms => now;
    }
}

// ============================================================
// CHIPPY ARPS — enter at tension > 0.5, faster at peak
// ============================================================
fun void chippyNote(float freq, float vol, float decay) {
    SqrOsc sq => LPF f => Gain g => master;
    g => reverb;
    freq => sq.freq;
    freq * 3.0 + tension * 2000.0 => f.freq;
    2.0 => f.Q;
    vol => g.gain;

    (decay * 1000.0) $ int / 40 => int stepMs;
    if (stepMs < 15) 15 => stepMs;
    for (0 => int i; i < 40; i++) {
        vol * Math.pow(0.95, i $ float) => g.gain;
        f.freq() * 0.995 => float ff;
        if (ff < 200.0) 200.0 => ff;
        ff => f.freq;
        stepMs::ms => now;
    }
    0.0 => g.gain;
    g =< master; g =< reverb; sq =< f; f =< g;
}

fun void chippyArps() {
    Math.random2(3, 7) => int baseIdx;

    while (true) {
        if (tension < 0.5) {
            1000::ms => now;
            continue;
        }

        // Run length scales with tension
        Math.random2(3, 3 + (tension * 5.0) $ int) => int runLen;
        for (0 => int n; n < runLen; n++) {
            if (tension < 0.4) break;
            (baseIdx + Math.random2(-1, 2)) => int idx;
            if (idx < 0) 0 => idx;
            if (idx >= scale.size()) scale.size()-1 => idx;
            idx => baseIdx;

            spork ~ chippyNote(
                Std.mtof(scale[idx]),
                Math.random2f(0.02, 0.04) * tension,
                Math.random2f(1.5, 4.0)
            );

            // Speed: faster at high tension
            (50 + ((1.0 - tension) * 150.0) $ int)::ms => now;
        }

        (2000 + ((1.0 - tension) * 5000.0) $ int)::ms => now;

        baseIdx + Math.random2(-3, 3) => baseIdx;
        if (baseIdx < 0) 0 => baseIdx;
        if (baseIdx >= scale.size() - 3) scale.size() - 4 => baseIdx;
    }
}

// ============================================================
// DEEP SUB — always present but volume follows tension
// ============================================================
fun void deepSub() {
    SinOsc sub => Gain sg => master;
    0.0 => sg.gain;

    [24, 22, 29, 27] @=> int roots[];

    while (true) {
        roots[Math.random2(0, roots.size()-1)] => int note;
        sub.freq() => float startF;
        Std.mtof(note) => float targetF;
        if (startF < 10.0) targetF => startF;

        for (0 => int i; i < 80; i++) {
            startF + (targetF - startF) * (i / 80.0) => sub.freq;
            // Sub louder during builds and breakdowns, quieter at extremes
            (0.03 + tension * 0.06) * Math.sin(Math.PI * i / 80.0) => sg.gain;
            60::ms => now;
        }

        for (0 => int i; i < 30; i++) {
            sg.gain() * 0.96 => sg.gain;
            50::ms => now;
        }
        0.0 => sg.gain;

        Math.random2(4000, 10000)::ms => now;
    }
}

// ============================================================
// LAUNCH
// ============================================================
<<< "  Starforge Dark Space", "" >>>;
<<< "  80s laser show — 6 minute arc: drone → build → climax → breathe → peak → fade", "" >>>;
<<< "  tension-driven: every parameter follows the emotional curve", "" >>>;
<<< "  loops forever. Ctrl-C to stop.", "" >>>;
<<< "" >>>;

spork ~ conductor();
spork ~ superSawPad();
spork ~ epicLead();
spork ~ bassSequence();
spork ~ bowls();
spork ~ chippyArps();
spork ~ deepSub();

while (true) 1::second => now;
