// Starforge Dark Industrial — harsh, mechanical, relentless
// 6-minute arc: machine boot → grind → assault → cooldown → overload → shutdown
// Run: chuck LABS/chuck-music/dark-industrial.ck

Gain master => dac;
0.3 => master.gain;

// Shared state
float tension;
float songTime;
float duckAmount;
1.0 => duckAmount;
float SONG_LENGTH;
360.0 => SONG_LENGTH;  // 6 minutes default
if (me.args() > 0) Std.atof(me.arg(0)) * 60.0 => SONG_LENGTH;
float BPM;
130.0 => BPM;

fun int beatMs() { return (60000.0 / BPM) $ int; }
fun int stepMs() { return beatMs() / 4; }

// Tension curve — mechanical escalation (audible from the start)
[  0.0, 0.25,
  30.0, 0.35,
  60.0, 0.50,
  90.0, 0.65,
 120.0, 0.25,     // systems cooling
 150.0, 0.55,
 180.0, 0.85,     // full assault
 210.0, 0.35,     // brief reprieve
 240.0, 0.95,     // OVERLOAD
 270.0, 0.70,
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
        // BPM: 128 at rest → 155 at peak
        128.0 + tension * 27.0 => BPM;
        0.28 + tension * 0.14 => master.gain;
        100::ms => now;
        0.1 +=> songTime;
        if (songTime >= SONG_LENGTH) 0.0 => songTime;
    }
}

// ============================================================
// DISTORTED KICK — hard, clicky, distortion increases with tension
// ============================================================
fun void kick() {
    while (true) {
        if (tension < 0.08) { 500::ms => now; continue; }

        // Four-on-floor at high tension, sparser at low
        if (Math.random2f(0.0, 1.0) > tension * 1.3) {
            beatMs()::ms => now;
            continue;
        }

        0.1 => duckAmount;

        SinOsc body => Gain kg => master;
        Noise click => LPF cf => kg;
        // Harder hit at higher tension
        (0.3 + tension * 0.3) => kg.gain;
        6000.0 => cf.freq;

        // Higher pitch start = more attack
        200.0 + tension * 60.0 => body.freq;
        0.4 + tension * 0.3 => click.gain;
        1::ms => now;
        0.0 => click.gain;

        // Fast pitch drop
        for (0 => int i; i < 20; i++) {
            body.freq() * 0.92 => float bf;
            if (bf < 35.0) 35.0 => bf;
            bf => body.freq;
            kg.gain() * 0.92 => kg.gain;
            duckAmount + (1.0 - duckAmount) * 0.05 => duckAmount;
            2::ms => now;
        }
        // Tail
        for (0 => int i; i < 40; i++) {
            kg.gain() * 0.9 => kg.gain;
            duckAmount + (1.0 - duckAmount) * 0.04 => duckAmount;
            2::ms => now;
        }

        kg =< master; body =< kg; click =< cf; cf =< kg;

        (beatMs() - 120)::ms => now;
        for (0 => int i; i < 4; i++) {
            duckAmount + (1.0 - duckAmount) * 0.25 => duckAmount;
            10::ms => now;
        }
    }
}

// ============================================================
// NOISE SNARE — harsh filtered noise bursts on 2 and 4
// ============================================================
fun void snare() {
    0 => int beat;
    while (true) {
        if (tension < 0.3) { beatMs()::ms => now; continue; }

        if (beat % 4 == 2) {
            Noise n => BPF bp => Gain sg => master;
            Math.random2f(1500.0, 3500.0) => bp.freq;
            3.0 => bp.Q;
            duckAmount * tension * 0.12 => sg.gain;

            5::ms => now;
            for (0 => int d; d < 20; d++) {
                sg.gain() * 0.85 => sg.gain;
                5::ms => now;
            }
            sg =< master; n =< bp; bp =< sg;
            (beatMs() - 105)::ms => now;
        } else {
            beatMs()::ms => now;
        }
        (beat + 1) % 8 => beat;
    }
}

// ============================================================
// MACHINE GUN HATS — 32nds at peak tension, 8ths at low
// ============================================================
fun void hats() {
    while (true) {
        if (tension < 0.15) { 300::ms => now; continue; }

        // Step division: 16ths normally, 32nds at high tension
        stepMs() => int stp;
        if (tension > 0.7) stp / 2 => stp;

        if (Math.random2f(0.0, 1.0) < tension * 1.4) {
            Noise n => HPF hp => Gain hg => master;
            8000.0 + tension * 4000.0 => hp.freq;
            duckAmount * tension * Math.random2f(0.03, 0.07) => hg.gain;

            2::ms => now;
            0.0 => hg.gain;
            (stp - 2)::ms => now;

            hg =< master; n =< hp; hp =< hg;
        } else {
            stp::ms => now;
        }
    }
}

// ============================================================
// ACID BASS — saw through resonant filter, slides between notes
// ============================================================
fun void acidBass() {
    SawOsc s1 => LPF filt => Gain bg => master;
    SawOsc s2 => filt;
    200.0 => filt.freq;
    8.0 => filt.Q;  // high resonance = acid
    0.0 => bg.gain;

    [29, 29, 27, 29, 31, 29, 24, 27,
     29, 29, 34, 29, 27, 31, 29, 24] @=> int pattern[];
    0 => int step;

    while (true) {
        if (tension < 0.25) { 500::ms => now; continue; }

        duckAmount * tension * 0.14 => bg.gain;

        Std.mtof(pattern[step]) => float target;
        s1.freq() => float cur;
        if (cur < 20.0) target => cur;

        stepMs() => int stp;

        // Slide to target note
        for (0 => int d; d < 8; d++) {
            cur + (target - cur) * ((d + 1) / 8.0) => float f;
            f => s1.freq;
            f * 1.006 => s2.freq;  // detune

            // Filter envelope — snap open then close
            if (d == 0) {
                300.0 + tension * tension * 4000.0 => filt.freq;
                8.0 + tension * 8.0 => filt.Q;
            } else {
                filt.freq() * 0.93 => float ff;
                if (ff < 120.0) 120.0 => ff;
                ff => filt.freq;
            }

            (stp / 8)::ms => now;
        }

        (step + 1) % pattern.size() => step;

        // Occasional pattern mutation
        if (Math.random2(0, 80) == 0) {
            Math.random2(0, pattern.size()-1) => int idx;
            [24, 27, 29, 31, 34] @=> int opts[];
            opts[Math.random2(0, opts.size()-1)] => pattern[idx];
        }
    }
}

// ============================================================
// MACHINE TEXTURE — rhythmic filtered noise, mechanical grinding
// ============================================================
fun void machineTexture() {
    while (true) {
        if (tension < 0.35) { 500::ms => now; continue; }

        // 3 rapid noise bursts
        Math.random2(2, 5) => int bursts;
        for (0 => int b; b < bursts; b++) {
            Noise n => BPF bp => Gain tg => master;
            Math.random2f(400.0, 2000.0) => bp.freq;
            8.0 => bp.Q;
            duckAmount * tension * Math.random2f(0.02, 0.05) => tg.gain;

            Math.random2(10, 30) => int durMs;
            durMs::ms => now;

            for (0 => int d; d < 8; d++) {
                tg.gain() * 0.7 => tg.gain;
                5::ms => now;
            }
            tg =< master; n =< bp; bp =< tg;

            Math.random2(20, 80)::ms => now;
        }

        Math.random2(500, (2000.0 - tension * 1200.0) $ int)::ms => now;
    }
}

// ============================================================
// ALARM — high pitched sweep at very high tension
// ============================================================
fun void alarm() {
    while (true) {
        if (tension < 0.7) { 1000::ms => now; continue; }

        SinOsc s => Gain ag => master;
        duckAmount * (tension - 0.7) * 0.08 => ag.gain;

        // Sweep up then down
        for (0 => int i; i < 40; i++) {
            800.0 + 2000.0 * Math.sin(Math.PI * i / 40.0) => s.freq;
            ag.gain() * 0.98 => ag.gain;
            (stepMs() / 2)::ms => now;
        }

        ag =< master; s =< ag;

        Math.random2(2000, 5000)::ms => now;
    }
}

// ============================================================
// LOW DRONE — constant industrial hum
// ============================================================
fun void industrialDrone() {
    SawOsc d1 => LPF filt => Gain dg => master;
    SawOsc d2 => filt;
    Noise n => filt;
    40.0 => d1.freq;
    40.15 => d2.freq;
    0.04 => n.gain;
    120.0 => filt.freq;
    3.0 => filt.Q;
    0.06 => dg.gain;

    while (true) {
        // Always present, volume follows tension
        0.05 + tension * 0.06 => dg.gain;
        80.0 + tension * 100.0 => float fTarget;
        filt.freq() + (fTarget - filt.freq()) * 0.01 => filt.freq;

        // Noise level increases with tension (more grit)
        0.02 + tension * 0.06 => n.gain;

        80::ms => now;
    }
}

// ============================================================
// LAUNCH
// ============================================================
<<< "  STARFORGE DARK INDUSTRIAL", "" >>>;
<<< "  harsh, mechanical, relentless", "" >>>;
<<< "  6-min arc: boot > grind > assault > cool > overload > shutdown", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ conductor();
spork ~ kick();
spork ~ snare();
spork ~ hats();
spork ~ acidBass();
spork ~ machineTexture();
spork ~ alarm();
spork ~ industrialDrone();

while (true) 1::second => now;
