// Starforge Coding Flow — warm ambient with gentle melody
// Pad fades in first, melody arrives slowly, soft pulse underneath
// Run: chuck LABS/chuck-music/coding-flow.ck

Gain master => NRev reverb => dac;
0.15 => reverb.mix;
0.35 => master.gain;

[48, 51, 53, 55, 58, 60, 63, 65, 67, 70, 72, 75] @=> int penta[];

// ============================================================
// PAD — warm detuned triangles, slow chord glides
// ============================================================
fun void pad() {
    TriOsc p1 => LPF filt => Gain pg => master;
    TriOsc p2 => filt;
    TriOsc p3 => filt;
    600.0 => filt.freq;
    3.0 => filt.Q;
    0.0 => pg.gain;

    // Fade in over 6 seconds
    for (0 => int i; i < 60; i++) {
        0.1 * (i / 60.0) => pg.gain;
        100::ms => now;
    }

    0 => int rootIdx;

    while (true) {
        penta[rootIdx] => int n1;
        penta[(rootIdx + 2) % penta.size()] => int n2;
        penta[(rootIdx + 4) % penta.size()] => int n3;

        Std.mtof(n1) => float f1;
        Std.mtof(n2) * 1.003 => float f2;
        Std.mtof(n3) * 0.997 => float f3;

        // Snap to new chord (no pitch glide)
        f1 => p1.freq;
        f2 => p2.freq;
        f3 => p3.freq;

        Math.random2f(400.0, 900.0) => float filtTarget;
        filt.freq() => float filtStart;

        // Slow filter sweep (brightness, not pitch)
        for (0 => int i; i < 120; i++) {
            i / 120.0 => float t;
            filtStart + (filtTarget - filtStart) * t => filt.freq;
            0.1 * (0.75 + 0.25 * Math.sin(i * 0.06)) => pg.gain;
            50::ms => now;
        }

        (rootIdx + Math.random2(1, 3)) % 7 => rootIdx;
        Math.random2(3000, 7000)::ms => now;
    }
}

// ============================================================
// MELODY — gentle sine phrases with long tails, unhurried
// ============================================================
fun void melody() {
    // Wait for pad to establish
    8000::ms => now;

    SinOsc mel => Gain mg => master;
    0.0 => mg.gain;

    // Short melodic motifs — index into penta
    // Each motif: sequence of note indices, -1 = rest
    [  4, 5, 7, -1, 5, 4, -1, -1,
       7, 5, 4, 3, -1, -1,
       3, 5, 4, -1, 7, 5, -1, -1,
       5, 7, 8, 7, 5, -1, -1, -1
    ] @=> int motifs[];

    // Motif boundaries: start, length
    [0, 8, 8, 6, 14, 8, 22, 8] @=> int bounds[];
    0 => int motifIdx;

    while (true) {
        (motifIdx * 2) => int bIdx;
        bounds[bIdx] => int mStart;
        bounds[bIdx + 1] => int mLen;

        for (0 => int i; i < mLen; i++) {
            motifs[mStart + i] => int noteIdx;

            if (noteIdx >= 0) {
                Std.mtof(penta[noteIdx % penta.size()]) => mel.freq;

                // Gentle fade in
                for (0 => int a; a < 15; a++) {
                    (a / 15.0) * Math.random2f(0.05, 0.08) => mg.gain;
                    8::ms => now;
                }
                // Hold
                Math.random2(300, 600)::ms => now;
                // Gentle fade out
                mg.gain() => float vol;
                for (0 => int r; r < 25; r++) {
                    vol * (1.0 - r / 25.0) => mg.gain;
                    10::ms => now;
                }
                0.0 => mg.gain;

                // Brief gap between notes in motif
                Math.random2(100, 300)::ms => now;
            } else {
                // Rest
                Math.random2(400, 800)::ms => now;
            }
        }

        // Long pause between motifs
        Math.random2(2000, 5000)::ms => now;

        // Next motif, with occasional repeat
        if (Math.random2(0, 3) == 0) {
            motifIdx => motifIdx;  // repeat same
        } else {
            (motifIdx + 1) % (bounds.size() / 2) => motifIdx;
        }
    }
}

// ============================================================
// PULSE — soft square wave, euclidean, enters after melody
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

fun void pulse() {
    // Enter well after pad and melody
    15000::ms => now;

    SqrOsc sq => LPF filt => Gain pg => master;
    0.0 => pg.gain;
    1500.0 => filt.freq;
    2.0 => filt.Q;

    [36, 38, 41, 43, 46] @=> int bassNotes[];
    0 => int noteIdx;
    3 => int k;
    8 => int n;
    0 => int cycle;

    while (true) {
        bjorklund(k, n) @=> int rhythm[];

        for (0 => int i; i < rhythm.size(); i++) {
            if (rhythm[i]) {
                Std.mtof(bassNotes[noteIdx]) => sq.freq;
                0.045 => pg.gain;
                for (0 => int d; d < 10; d++) {
                    pg.gain() * 0.84 => pg.gain;
                    15::ms => now;
                }
            } else {
                0.0 => pg.gain;
                150::ms => now;
            }
        }

        cycle++;
        if (cycle % 4 == 0) {
            Math.random2(2, 5) => k;
            Math.random2(7, 12) => n;
            (noteIdx + Math.random2(1, 3)) % bassNotes.size() => noteIdx;
        }
    }
}

// ============================================================
// SHIMMER — high sine sparkles, very sparse
// ============================================================
fun void sparkle(float freq, float vol) {
    SinOsc s => Gain g => master;
    freq => s.freq;
    vol => g.gain;
    for (0 => int i; i < 40; i++) {
        vol * Math.pow(0.92, i $ float) => g.gain;
        25::ms => now;
    }
    0.0 => g.gain;
    g =< master; s =< g;
}

fun void shimmer() {
    12000::ms => now;

    while (true) {
        if (Math.random2f(0.0, 1.0) < 0.25) {
            Math.random2(8, penta.size()-1) => int idx;
            Std.mtof(penta[idx] + 12) => float freq;
            Math.random2f(0.015, 0.03) => float vol;
            spork ~ sparkle(freq, vol);
        }
        Math.random2(2000, 6000)::ms => now;
    }
}

// ============================================================
// SUB — barely there, grounds everything
// ============================================================
fun void sub() {
    10000::ms => now;

    SinOsc s => Gain sg => master;
    0.0 => sg.gain;

    while (true) {
        Std.mtof(penta[Math.random2(0, 3)] - 12) => s.freq;

        // Slow swell
        for (0 => int i; i < 50; i++) {
            0.05 * Math.sin(Math.PI * i / 50.0) => sg.gain;
            60::ms => now;
        }
        for (0 => int i; i < 30; i++) {
            sg.gain() * 0.94 => sg.gain;
            50::ms => now;
        }
        0.0 => sg.gain;

        Math.random2(5000, 12000)::ms => now;
    }
}

// ============================================================
// LAUNCH
// ============================================================
<<< "  Starforge Coding Flow", "" >>>;
<<< "  warm ambient with gentle melodies — layers fade in slowly", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ pad();
spork ~ melody();
spork ~ pulse();
spork ~ shimmer();
spork ~ sub();

while (true) 1::second => now;
