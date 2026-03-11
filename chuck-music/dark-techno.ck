// Starforge Dark Techno — tension-driven industrial groove
// 6-minute arc: sparse → build → drop → breathe → peak → fade
// Run: chuck LABS/chuck-music/dark-techno.ck

Gain master => dac;
0.35 => master.gain;

// Shared state
float BPM;
float duckAmount;
float tension;      // 0.0 to 1.0 — drives everything
float songTime;
float SONG_LENGTH;
360.0 => SONG_LENGTH;  // 6 minutes default
if (me.args() > 0) Std.atof(me.arg(0)) * 60.0 => SONG_LENGTH;
128.0 => BPM;
1.0 => duckAmount;

fun int beatMs() { return (60000.0 / BPM) $ int; }
fun int stepMs() { return beatMs() / 4; }

// Tension curve for dark techno
// 0:00 → 0.05 (kick alone)
// 0:30 → 0.15 (hats creep in)
// 1:00 → 0.30 (bass enters, perc)
// 1:30 → 0.50 (building, filter opening)
// 2:00 → 0.25 (BREAKDOWN — strip to drone + sparse kick)
// 2:30 → 0.55 (rebuild, more aggressive)
// 3:00 → 0.80 (FIRST DROP — full power)
// 3:30 → 0.40 (breathe — pads, sparse hats)
// 4:00 → 0.90 (PEAK — fastest BPM, densest, filter wide)
// 4:30 → 0.75 (sustain intensity)
// 5:00 → 0.35 (outro begins)
// 5:30 → 0.10 (drone only)
// 6:00 → 0.02 (silence)

[  0.0, 0.05,
  30.0, 0.15,
  60.0, 0.30,
  90.0, 0.50,
 120.0, 0.25,
 150.0, 0.55,
 180.0, 0.80,
 210.0, 0.40,
 240.0, 0.90,
 270.0, 0.75,
 300.0, 0.35,
 330.0, 0.10,
 360.0, 0.02
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
// CONDUCTOR — updates tension, derives BPM
// ============================================================
fun void conductor() {
    0.0 => songTime;
    while (true) {
        tensionAt(songTime) => tension;
        // BPM follows tension: 125 at rest → 145 at peak
        125.0 + tension * 20.0 => BPM;
        // Master volume
        0.3 + tension * 0.12 => master.gain;

        100::ms => now;
        0.1 +=> songTime;
        if (songTime >= SONG_LENGTH) 0.0 => songTime;
    }
}

// ============================================================
// KICK — tension-driven: sparse at low, four-on-floor at high
// ============================================================
fun void kick() {
    while (true) {
        // Below 0.08 tension: no kick at all
        if (tension < 0.08) {
            500::ms => now;
            continue;
        }

        // Probability of kick playing = tension
        // At low tension: sparse, at high: every beat
        if (Math.random2f(0.0, 1.0) > tension * 1.5) {
            beatMs()::ms => now;
            continue;
        }

        0.1 => duckAmount;

        SinOsc body => Gain kg => master;
        Noise click => LPF cf => kg;
        (0.25 + tension * 0.25) => kg.gain;
        4000.0 => cf.freq;

        180.0 => body.freq;
        0.3 + tension * 0.2 => click.gain;
        1::ms => now;
        0.0 => click.gain;

        for (0 => int i; i < 25; i++) {
            180.0 - (140.0 * i / 25.0) => body.freq;
            kg.gain() * 0.93 => kg.gain;
            duckAmount + (1.0 - duckAmount) * 0.04 => duckAmount;
            2::ms => now;
        }
        for (0 => int i; i < 50; i++) {
            kg.gain() * 0.92 => kg.gain;
            duckAmount + (1.0 - duckAmount) * 0.04 => duckAmount;
            2::ms => now;
        }

        kg =< master; body =< kg; click =< cf; cf =< kg;

        (beatMs() - 150)::ms => now;
        for (0 => int i; i < 5; i++) {
            duckAmount + (1.0 - duckAmount) * 0.2 => duckAmount;
            10::ms => now;
        }
    }
}

// ============================================================
// BASS — detuned saws, pattern mutates
// ============================================================
fun void bass() {
    SawOsc s1 => LPF filt => Gain bg => master;
    SawOsc s2 => filt;
    200.0 => filt.freq;
    5.0 => filt.Q;
    0.0 => bg.gain;

    [29, 29, 29, 29, 27, 27, 29, 29,
     29, 31, 29, 29, 27, 27, 24, 29] @=> int pattern[];
    0 => int step;
    0 => int count;

    while (true) {
        // Bass enters at tension > 0.2
        if (tension < 0.2) {
            500::ms => now;
            continue;
        }

        duckAmount * (tension * 0.18) => bg.gain;

        Std.mtof(pattern[step]) => float f;
        f => s1.freq;
        f * 1.008 => s2.freq;

        stepMs() => int sms;

        // Filter opens with tension
        200.0 + tension * 500.0 => filt.freq;
        4.0 + tension * 5.0 => filt.Q;

        for (0 => int d; d < 8; d++) {
            filt.freq() * 0.97 => float ff;
            if (ff < 150.0) 150.0 => ff;
            ff => filt.freq;
            (sms / 8)::ms => now;
        }

        (step + 1) % pattern.size() => step;
        count++;

        if (count % 64 == 0) {
            Math.random2(0, pattern.size()-1) => int idx;
            [24, 27, 29, 31, 34] @=> int opts[];
            opts[Math.random2(0, opts.size()-1)] => pattern[idx];
        }
    }
}

// ============================================================
// INDUSTRIAL PERC — metallic hits, euclidean, section-aware
// ============================================================
fun int[] bjorklund(int k, int n) {
    int result[n];
    float bucket;
    0.0 => bucket;
    k $ float / n => float slope;
    for (0 => int i; i < n; i++) {
        bucket + slope => bucket;
        if (bucket >= 1.0) { 1 => result[i]; bucket - 1.0 => bucket; }
        else 0 => result[i];
    }
    return result;
}

fun void metalPerc() {
    5 => int k;
    12 => int n;
    0 => int bar;

    while (true) {
        // Only play above 0.25 tension
        if (tension < 0.25) { 500::ms => now; continue; }

        bjorklund(k, n) @=> int rhythm[];

        for (0 => int i; i < rhythm.size(); i++) {
            beatMs() / 3 => int tripMs;

            if (rhythm[i]) {
                SinOsc s => Gain pg => master;
                Noise cl => BPF bp => pg;
                Math.random2f(800.0, 3000.0) => s.freq;
                Math.random2f(3000.0, 8000.0) => bp.freq;
                4.0 => bp.Q;
                duckAmount * tension * Math.random2f(0.05, 0.1) => pg.gain;

                8::ms => now;
                for (0 => int d; d < 10; d++) {
                    pg.gain() * 0.75 => pg.gain;
                    Math.max(1, (tripMs - 8) / 10) $ int => int dms;
                    dms::ms => now;
                }
                pg =< master; s =< pg; cl =< bp; bp =< pg;
            } else {
                tripMs::ms => now;
            }
        }

        bar++;
        if (bar % 6 == 0) {
            // Density follows tension
            (2 + tension * 6.0) $ int => int tk;
            (7 + tension * 9.0) $ int => int tn;
            Math.random2(Math.max(2, tk-1), tk+1) => k;
            Math.random2(Math.max(6, tn-2), tn+2) => n;
        }
    }
}

// ============================================================
// HATS — 16ths, section-aware density
// ============================================================
fun void hats() {
    Noise n => BPF bp => Gain hg => master;
    10000.0 => bp.freq;
    3.0 => bp.Q;
    0.0 => hg.gain;
    0 => int step;

    while (true) {
        // Hats enter at tension > 0.12
        if (tension < 0.12) { 200::ms => now; continue; }

        stepMs() => int sms;

        // Probability of hat playing scales with tension
        if (Math.random2f(0.0, 1.0) < tension * 1.2) {
            duckAmount * tension * Math.random2f(0.04, 0.08) => hg.gain;
            if (step % 4 == 2) hg.gain() * 1.3 => hg.gain;
            3::ms => now;
            0.0 => hg.gain;
            (sms - 3)::ms => now;
        } else {
            sms::ms => now;
        }

        (step + 1) % 16 => step;
    }
}

// ============================================================
// DRONE — 4 detuned saws for thick dark pad
// ============================================================
fun void drone() {
    SawOsc d1 => LPF filt => NRev rev => Gain dg => master;
    SawOsc d2 => filt;
    SawOsc d3 => filt;
    SawOsc d4 => filt;
    0.2 => rev.mix;
    300.0 => filt.freq;
    4.0 => filt.Q;
    0.05 => dg.gain;

    [29, 27, 31, 24] @=> int roots[];
    0 => int rootIdx;

    while (true) {
        Std.mtof(roots[rootIdx]) => float root;
        d1.freq() => float startRoot;
        if (startRoot < 10.0) root => startRoot;

        for (0 => int i; i < 250; i++) {
            startRoot + (root - startRoot) * (i / 250.0) => float f;
            f * 0.997 => d1.freq;
            f * 1.003 => d2.freq;
            f * 1.498 => d3.freq;
            f * 1.502 => d4.freq;

            // Filter follows tension
            150.0 + tension * 500.0 => float fTarget;
            filt.freq() + (fTarget - filt.freq()) * 0.015 => filt.freq;

            // Volume: louder at low tension (fills space), quieter at peak
            duckAmount * (0.03 + (1.0 - tension) * 0.05) => dg.gain;

            40::ms => now;
        }

        // Change root occasionally
        if (Math.random2(0, 3) == 0) {
            (rootIdx + 1) % roots.size() => rootIdx;
        }
        Math.random2(2000, 4000)::ms => now;
    }
}

// ============================================================
// DARK SYNTH STAB — plays at mid-high tension
// ============================================================
fun void synthStab() {
    5000::ms => now;

    while (true) {
        if (tension > 0.45) {
            // Stab: 3 detuned saws, fast attack, filter snap
            SawOsc st1 => LPF sf => Gain sg => master;
            SawOsc st2 => sf;
            SawOsc st3 => sf;
            2000.0 => sf.freq;
            6.0 => sf.Q;
            duckAmount * 0.08 => sg.gain;

            // Minor chord
            [29, 34, 36, 41] @=> int notes[];
            notes[Math.random2(0, 3)] => int n;
            Std.mtof(n) => float f;
            f * 0.995 => st1.freq;
            f * 1.005 => st2.freq;
            f * 2.0 => st3.freq;
            0.4 => st3.gain;

            // Filter decay — the snap
            for (0 => int d; d < 30; d++) {
                sf.freq() * 0.92 => float ff;
                if (ff < 200.0) 200.0 => ff;
                ff => sf.freq;
                sg.gain() * 0.93 => sg.gain;
                20::ms => now;
            }

            sg =< master; st1 =< sf; st2 =< sf; st3 =< sf; sf =< sg;
        }

        // Irregular timing — euclidean feel
        Math.random2(2, 6) => int beats;
        (beatMs() * beats)::ms => now;
    }
}

// ============================================================
// RISER/FX — noise sweeps when tension is building
// ============================================================
fun void riserFX() {
    0.0 => float prevTension;

    while (true) {
        // Wait a while between potential risers
        (beatMs() * Math.random2(32, 48))::ms => now;

        // Only trigger when tension is mid-range and RISING
        // (building toward a drop — not during peaks or lulls)
        tension => float curT;
        if (curT > 0.3 && curT < 0.75 && curT > prevTension + 0.02) {
            Noise n => BPF bp => Gain rg => master;
            200.0 => bp.freq;
            6.0 => bp.Q;
            0.0 => rg.gain;

            // Riser length scales with tension — longer at higher tension
            (32 + (tension * 48.0) $ int) => int steps;

            for (0 => int i; i < steps; i++) {
                200.0 + (12000.0 * i / steps) => bp.freq;
                duckAmount * (i $ float / steps) * tension * 0.08 => rg.gain;
                (beatMs() / 4)::ms => now;
            }
            // Hard cut for impact
            rg =< master; n =< bp; bp =< rg;
        }
        curT => prevTension;
    }
}

// ============================================================
// LAUNCH
// ============================================================
<<< "  STARFORGE DARK TECHNO", "" >>>;
<<< "  6-min arc: sparse > build > drop > breathe > peak > fade", "" >>>;
<<< "  evolving tempo | tension-driven layers", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ conductor();
spork ~ kick();
spork ~ bass();
spork ~ metalPerc();
spork ~ hats();
spork ~ drone();
spork ~ synthStab();
spork ~ riserFX();

while (true) 1::second => now;
