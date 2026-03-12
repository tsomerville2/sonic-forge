// Starforge Euro Rave — acid bass, four-on-the-floor, sidechain pump
// 6-minute arc: intro → build → drop → breathe → peak → outro
// Run: chuck LABS/chuck-music/euro-rave.ck

Gain master => dac;
0.35 => master.gain;

// Shared state
float tension;
float songTime;
float duckAmount;
1.0 => duckAmount;
float SONG_LENGTH;
360.0 => SONG_LENGTH;  // 6 minutes default
if (me.args() > 0) Std.atof(me.arg(0)) * 60.0 => SONG_LENGTH;
float BPM;
135.0 => BPM;

fun int beatMs() { return (60000.0 / BPM) $ int; }
fun int stepMs() { return beatMs() / 4; }

// Tension curve — rave energy arc
[  0.0, 0.20,
  30.0, 0.30,
  60.0, 0.50,
  90.0, 0.70,
 120.0, 0.30,     // breakdown
 150.0, 0.60,
 180.0, 0.90,     // FIRST DROP
 210.0, 0.40,     // breathe
 240.0, 0.95,     // PEAK — maximum energy
 270.0, 0.80,
 300.0, 0.45,
 330.0, 0.20,
 360.0, 0.08
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

// Euclidean rhythm
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

// ============================================================
// CONDUCTOR
// ============================================================
fun void conductor() {
    0.0 => songTime;
    while (true) {
        tensionAt(songTime) => tension;
        // BPM: 132 at rest → 142 at peak
        132.0 + tension * 10.0 => BPM;
        0.3 + tension * 0.12 => master.gain;
        100::ms => now;
        0.1 +=> songTime;
        if (songTime >= SONG_LENGTH) 0.0 => songTime;
    }
}

// ============================================================
// KICK — four-on-the-floor, power scales with tension
// ============================================================
fun void kick() {
    while (true) {
        if (tension < 0.1) { 500::ms => now; continue; }

        // Sparse at low tension, every beat at high
        if (Math.random2f(0.0, 1.0) > tension * 1.5) {
            beatMs()::ms => now;
            continue;
        }

        0.12 => duckAmount;

        SinOsc body => Gain kg => master;
        Noise click => LPF cf => kg;
        (0.25 + tension * 0.2) => kg.gain;
        4000.0 => cf.freq;

        160.0 + tension * 30.0 => body.freq;
        0.3 + tension * 0.15 => click.gain;
        2::ms => now;
        0.0 => click.gain;

        for (0 => int i; i < 25; i++) {
            body.freq() * 0.93 => float bf;
            if (bf < 42.0) 42.0 => bf;
            bf => body.freq;
            kg.gain() * 0.93 => kg.gain;
            duckAmount + (1.0 - duckAmount) * 0.04 => duckAmount;
            2::ms => now;
        }
        for (0 => int i; i < 40; i++) {
            kg.gain() * 0.91 => kg.gain;
            duckAmount + (1.0 - duckAmount) * 0.04 => duckAmount;
            2::ms => now;
        }

        kg =< master; body =< kg; click =< cf; cf =< kg;

        (beatMs() - 130)::ms => now;
        for (0 => int i; i < 4; i++) {
            duckAmount + (1.0 - duckAmount) * 0.2 => duckAmount;
            10::ms => now;
        }
    }
}

// ============================================================
// ACID BASS — TB-303: saw + resonant filter, tension controls squelch
// ============================================================
fun void acidBass() {
    SawOsc saw => LPF filt => Gain ag => master;
    0.0 => ag.gain;
    2000.0 => filt.freq;
    8.0 => filt.Q;

    [29, 29, 32, 29, 34, 32, 36, 34,
     29, 31, 29, 34, 36, 34, 31, 29] @=> int pattern[];
    [1, 0, 1, 0, 0, 1, 1, 0,
     1, 0, 0, 1, 1, 0, 0, 1] @=> int accents[];
    [0, 0, 1, 0, 1, 0, 0, 1,
     0, 1, 0, 0, 1, 0, 1, 0] @=> int slides[];

    0 => int step;
    0 => int count;

    while (true) {
        if (tension < 0.15) { 500::ms => now; continue; }

        duckAmount * tension * 0.22 => ag.gain;

        Std.mtof(pattern[step]) => float target;

        stepMs() => int stp;

        if (slides[step]) {
            saw.freq() => float startF;
            if (startF < 20.0) target => startF;
            for (0 => int g; g < 8; g++) {
                startF + (target - startF) * (g / 8.0) => saw.freq;
                (stp / 8)::ms => now;
            }
        } else {
            target => saw.freq;

            // Filter envelope — spike then decay
            if (accents[step]) {
                400.0 + tension * tension * 5000.0 => filt.freq;
            } else {
                400.0 + tension * 1200.0 => filt.freq;
            }
            // Resonance follows tension
            6.0 + tension * 10.0 => filt.Q;

            for (0 => int d; d < 10; d++) {
                filt.freq() * 0.91 => float ff;
                if (ff < 300.0) 300.0 => ff;
                ff => filt.freq;
                (stp / 10)::ms => now;
            }
        }

        (step + 1) % pattern.size() => step;
        count++;

        // Evolve pattern
        if (count % 64 == 0) {
            Math.random2(0, pattern.size()-1) => int idx;
            [24, 27, 29, 31, 32, 34, 36] @=> int opts[];
            opts[Math.random2(0, opts.size()-1)] => pattern[idx];
        }
    }
}

// ============================================================
// HATS — density follows tension
// ============================================================
fun void hats() {
    0 => int step;
    [0, 0, 1, 0, 0, 1, 1, 0,
     0, 0, 1, 0, 0, 1, 2, 0] @=> int hatPat[];

    while (true) {
        if (tension < 0.12) { 300::ms => now; continue; }

        stepMs() => int stp;

        // Extra ghost notes at high tension
        int play;
        hatPat[step] => play;
        if (play == 0 && tension > 0.6 && Math.random2f(0.0, 1.0) < tension * 0.4) {
            1 => play;
        }

        if (play == 1) {
            Noise n => BPF bp => Gain hg => master;
            8000.0 + tension * 4000.0 => bp.freq;
            3.0 => bp.Q;
            duckAmount * tension * Math.random2f(0.04, 0.08) => hg.gain;
            4::ms => now;
            0.0 => hg.gain;
            hg =< master; n =< bp; bp =< hg;
            (stp - 4)::ms => now;
        } else if (play == 2) {
            // Open hat
            Noise n => BPF bp => Gain hg => master;
            7000.0 => bp.freq;
            2.0 => bp.Q;
            duckAmount * tension * 0.1 => hg.gain;
            for (0 => int d; d < 12; d++) {
                hg.gain() * 0.88 => hg.gain;
                (stp / 12)::ms => now;
            }
            hg =< master; n =< bp; bp =< hg;
        } else {
            stp::ms => now;
        }

        (step + 1) % hatPat.size() => step;
    }
}

// ============================================================
// CLAP — 2 and 4, harder at higher tension
// ============================================================
fun void clap() {
    while (true) {
        if (tension < 0.2) { beatMs()::ms => now; continue; }

        // Beat 1: rest
        beatMs()::ms => now;

        // Beat 2: clap
        Noise n => BPF bp => Gain cg => master;
        1800.0 => bp.freq;
        2.0 => bp.Q;
        duckAmount * tension * 0.15 => cg.gain;

        for (0 => int r; r < 3; r++) {
            duckAmount * tension * 0.15 => cg.gain;
            3::ms => now;
            0.0 => cg.gain;
            2::ms => now;
        }
        duckAmount * tension * 0.12 => cg.gain;
        for (0 => int d; d < 12; d++) {
            cg.gain() * 0.82 => cg.gain;
            3::ms => now;
        }
        cg =< master; n =< bp; bp =< cg;

        (beatMs() - 51)::ms => now;

        // Beat 3: rest
        beatMs()::ms => now;

        // Beat 4: clap
        Noise n2 => BPF bp2 => Gain cg2 => master;
        1800.0 => bp2.freq;
        2.0 => bp2.Q;
        duckAmount * tension * 0.15 => cg2.gain;

        for (0 => int r; r < 3; r++) {
            duckAmount * tension * 0.15 => cg2.gain;
            3::ms => now;
            0.0 => cg2.gain;
            2::ms => now;
        }
        duckAmount * tension * 0.12 => cg2.gain;
        for (0 => int d; d < 12; d++) {
            cg2.gain() * 0.82 => cg2.gain;
            3::ms => now;
        }
        cg2 =< master; n2 =< bp2; bp2 =< cg2;

        (beatMs() - 51)::ms => now;
    }
}

// ============================================================
// SYNTH STAB — chord hits, gated by tension, filter follows arc
// ============================================================
fun void synthStab() {
    3 => int k;
    8 => int n;
    0 => int bar;

    [[53, 56, 60, 63],
     [51, 55, 58, 63],
     [48, 51, 55, 58],
     [46, 51, 53, 58]] @=> int chords[][];
    0 => int chordIdx;

    while (true) {
        if (tension < 0.35) { beatMs()::ms => now; continue; }

        bjorklund(k, n) @=> int rhythm[];
        chords[chordIdx] @=> int ch[];

        for (0 => int i; i < rhythm.size(); i++) {
            (beatMs() / 2) => int stp;

            if (rhythm[i]) {
                SqrOsc s1 => LPF sf => Gain sg => master;
                SqrOsc s2 => sf;
                SqrOsc s3 => sf;
                SqrOsc s4 => sf;
                2000.0 + tension * 3000.0 => sf.freq;
                1.5 + tension * 2.0 => sf.Q;
                duckAmount * tension * 0.07 => sg.gain;

                Std.mtof(ch[0]) => s1.freq;
                Std.mtof(ch[1]) => s2.freq;
                Std.mtof(ch[2]) => s3.freq;
                Std.mtof(ch[3]) => s4.freq;

                for (0 => int d; d < 10; d++) {
                    sg.gain() * 0.8 => sg.gain;
                    sf.freq() * 0.9 => float ff;
                    if (ff < 400.0) 400.0 => ff;
                    ff => sf.freq;
                    (stp / 10)::ms => now;
                }
                sg =< master; s1 =< sf; s2 =< sf; s3 =< sf; s4 =< sf; sf =< sg;
            } else {
                stp::ms => now;
            }
        }

        bar++;
        if (bar % 4 == 0) (chordIdx + 1) % chords.size() => chordIdx;
        if (bar % 8 == 0) {
            (2 + tension * 4.0) $ int => int tk;
            Math.random2(Math.max(2, tk-1), tk+1) => k;
            Math.random2(6, 12) => n;
        }
    }
}

// ============================================================
// RISER — noise sweep when tension is building toward a peak
// ============================================================
fun void riser() {
    0.0 => float prevTension;

    while (true) {
        (beatMs() * Math.random2(24, 40))::ms => now;

        tension => float curT;
        if (curT > 0.4 && curT < 0.85 && curT > prevTension + 0.03) {
            Noise n => BPF bp => Gain rg => master;
            200.0 => bp.freq;
            6.0 => bp.Q;
            0.0 => rg.gain;

            (40 + (tension * 40.0) $ int) => int steps;
            for (0 => int i; i < steps; i++) {
                200.0 + (12000.0 * i / steps) => bp.freq;
                duckAmount * (i $ float / steps) * tension * 0.08 => rg.gain;
                (beatMs() / 4)::ms => now;
            }
            rg =< master; n =< bp; bp =< rg;
        }
        curT => prevTension;
    }
}

// ============================================================
// PAD — filtered saw pad, fills space at mid-low tension
// ============================================================
fun void pad() {
    SawOsc p1 => LPF filt => Gain pg => master;
    SawOsc p2 => filt;
    300.0 => filt.freq;
    4.0 => filt.Q;
    0.0 => pg.gain;

    [53, 51, 48, 46] @=> int roots[];
    0 => int idx;

    while (true) {
        Std.mtof(roots[idx]) => float root;
        root * 0.998 => p1.freq;
        root * 1.002 => p2.freq;

        for (0 => int i; i < 80; i++) {
            // Louder at mid tension, quieter at extremes
            float padVol;
            if (tension < 0.5) tension * 0.08 => padVol;
            else (1.0 - tension) * 0.08 => padVol;
            duckAmount * padVol => pg.gain;

            200.0 + tension * 600.0 => float fTarget;
            filt.freq() + (fTarget - filt.freq()) * 0.02 => filt.freq;

            60::ms => now;
        }

        if (Math.random2(0, 2) == 0) {
            (idx + 1) % roots.size() => idx;
        }
        Math.random2(2000, 5000)::ms => now;
    }
}

// ============================================================
// LAUNCH
// ============================================================
<<< "  STARFORGE EURO RAVE", "" >>>;
<<< "  acid bass | four-on-the-floor | sidechain pump", "" >>>;
<<< "  6-min arc: intro > build > drop > breathe > peak > outro", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ conductor();
spork ~ kick();
spork ~ acidBass();
spork ~ hats();
spork ~ clap();
spork ~ synthStab();
spork ~ riser();
spork ~ pad();

while (true) 1::second => now;
