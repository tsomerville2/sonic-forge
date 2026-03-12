// Starforge Gameboy Evolve — 8-bit chiptune with real melodies
// Square wave leads, triangle bass, noise drums, evolving phrases
// Run: chuck LABS/chuck-music/gameboy-evolve.ck

Gain master => NRev reverb => dac;
0.08 => reverb.mix;
0.35 => master.gain;

// Shared tempo
float BPM;
120.0 => BPM;
fun int beatMs() { return (60000.0 / BPM) $ int; }
fun int stepMs() { return beatMs() / 4; }

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

// Scales
[60, 63, 65, 67, 70, 72, 75, 77] @=> int minPenta[];  // C minor penta
[60, 62, 63, 67, 68, 72, 74, 75] @=> int blues[];
[60, 64, 65, 67, 71, 72, 76, 77] @=> int major[];

// ============================================================
// MELODY — the star of the show. Real phrases, not random notes
// ============================================================
fun void melody() {
    SqrOsc sq => LPF filt => Gain mg => master;
    3000.0 => filt.freq;
    1.5 => filt.Q;
    0.0 => mg.gain;

    // Melodic phrases — each is a sequence of (note_index, duration_in_16ths)
    // Note index into current scale. -1 = rest.
    // These are hand-crafted to sound musical
    [  // Phrase 0: ascending question
       0, 2,  2, 2,  3, 4,  4, 2,  5, 4,  -1, 2,
       // Phrase 1: descending answer
       5, 2,  4, 2,  3, 4,  2, 2,  0, 4,  -1, 2,
       // Phrase 2: call and response
       0, 1,  2, 1,  4, 2,  -1, 4,  3, 1,  2, 1,  0, 2,  -1, 4,
       // Phrase 3: jump up, walk down
       0, 2,  5, 4,  4, 2,  3, 2,  2, 2,  1, 2,  0, 4,  -1, 2
    ] @=> int phrases[];

    // Phrase boundaries (index into phrases array, pairs per phrase)
    [0, 12, 12, 12, 24, 16, 40, 16] @=> int phraseBounds[];

    0 => int phraseIdx;
    0 => int scaleChoice;
    0 => int octaveShift;

    while (true) {
        // Pick scale
        int scale[];
        if (scaleChoice == 0) minPenta @=> scale;
        else if (scaleChoice == 1) blues @=> scale;
        else major @=> scale;

        // Pick phrase
        (phraseIdx * 2) => int bIdx;
        phraseBounds[bIdx] => int pStart;
        phraseBounds[bIdx + 1] => int pLen;

        // Play the phrase
        for (0 => int i; i < pLen; 2 +=> i) {
            phrases[pStart + i] => int noteIdx;
            phrases[pStart + i + 1] => int dur;

            stepMs() => int stp;

            if (noteIdx >= 0) {
                Std.mtof(scale[noteIdx % scale.size()] + octaveShift) => sq.freq;
                0.1 => mg.gain;

                // Note envelope — attack then decay
                for (0 => int d; d < dur; d++) {
                    if (d > 0) mg.gain() * 0.85 => mg.gain;
                    stp::ms => now;
                }
            } else {
                // Rest
                0.0 => mg.gain;
                (stp * dur)::ms => now;
            }
        }

        // Brief gap between phrases
        0.0 => mg.gain;
        Math.random2(200, 800)::ms => now;

        // Evolve: next phrase, occasional scale/octave change
        (phraseIdx + 1) % (phraseBounds.size() / 2) => phraseIdx;

        if (Math.random2(0, 5) == 0) {
            Math.random2(0, 2) => scaleChoice;
        }
        if (Math.random2(0, 7) == 0) {
            [0, 0, 12, -12] @=> int shifts[];
            shifts[Math.random2(0, shifts.size()-1)] => octaveShift;
        }
    }
}

// ============================================================
// COUNTERMELODY — higher register, sparser, echoes the melody
// ============================================================
fun void counterMelody() {
    SqrOsc sq => LPF filt => Gain cg => master;
    2500.0 => filt.freq;
    2.0 => filt.Q;
    0.0 => cg.gain;
    0.4 => sq.gain;  // quieter than melody

    // Offset start so it doesn't clash
    2000::ms => now;

    while (true) {
        // Play short ornamental runs
        Math.random2(2, 5) => int runLen;
        Math.random2(3, 6) => int startNote;

        for (0 => int n; n < runLen; n++) {
            int noteIdx;
            (startNote + n) % minPenta.size() => noteIdx;
            Std.mtof(minPenta[noteIdx] + 12) => sq.freq;  // octave up
            0.06 => cg.gain;

            stepMs() => int stp;

            // Very short staccato
            for (0 => int d; d < 3; d++) {
                cg.gain() * 0.7 => cg.gain;
                (stp / 3)::ms => now;
            }
        }

        0.0 => cg.gain;

        // Long gap — counter melody is sparse
        Math.random2(2000, 6000)::ms => now;
    }
}

// ============================================================
// BASS — triangle wave, follows root movement
// ============================================================
fun void bass() {
    TriOsc tri => LPF filt => Gain bg => master;
    0.12 => bg.gain;
    800.0 => filt.freq;
    2.0 => filt.Q;

    [36, 39, 41, 43, 36, 41, 39, 36] @=> int pattern[];
    0 => int step;
    0 => int bar;

    while (true) {
        Std.mtof(pattern[step]) => float target;
        tri.freq() => float cur;
        if (cur < 20.0) target => cur;

        // Slight slide to note
        for (0 => int i; i < 4; i++) {
            cur + (target - cur) * ((i+1) / 4.0) => tri.freq;
            0.12 => bg.gain;
            beatMs() / 4 => int qMs;
            qMs::ms => now;
        }

        // Note off gap
        0.0 => bg.gain;
        (beatMs() / 8)::ms => now;

        // Second hit — octave up staccato
        Std.mtof(pattern[step] + 12) => tri.freq;
        0.08 => bg.gain;
        (beatMs() / 8)::ms => now;
        0.0 => bg.gain;
        (beatMs() / 4)::ms => now;

        (step + 1) % pattern.size() => step;
        bar++;

        if (bar % 16 == 0) {
            // Mutate one bass note
            Math.random2(0, pattern.size()-1) => int idx;
            [36, 39, 41, 43, 34, 46] @=> int opts[];
            opts[Math.random2(0, opts.size()-1)] => pattern[idx];
        }
    }
}

// ============================================================
// DRUMS — kick, snare, hats with euclidean patterns
// ============================================================
fun void drums() {
    0 => int bar;

    while (true) {
        bjorklund(Math.random2(2, 4), 8) @=> int kickPat[];
        bjorklund(Math.random2(3, 6), 8) @=> int hatPat[];

        for (0 => int i; i < 8; i++) {
            stepMs() * 2 => int stp;  // eighth notes

            if (kickPat[i]) {
                // Kick: sine sweep + noise click
                SinOsc kb => Gain kg => master;
                Noise kn => LPF kf => kg;
                0.18 => kg.gain;
                200.0 => kf.freq;
                120.0 => kb.freq;
                0.2 => kn.gain;
                2::ms => now;
                0.0 => kn.gain;
                for (0 => int d; d < 10; d++) {
                    kb.freq() * 0.9 => float bf;
                    if (bf < 40.0) 40.0 => bf;
                    bf => kb.freq;
                    kg.gain() * 0.85 => kg.gain;
                    3::ms => now;
                }
                kg =< master; kb =< kg; kn =< kf; kf =< kg;
                (stp - 32)::ms => now;
            } else if (hatPat[i]) {
                // Hat
                Noise hn => BPF hb => Gain hg => master;
                9000.0 => hb.freq;
                4.0 => hb.Q;
                Math.random2f(0.04, 0.07) => hg.gain;
                3::ms => now;
                0.0 => hg.gain;
                hg =< master; hn =< hb; hb =< hg;
                (stp - 3)::ms => now;
            } else {
                stp::ms => now;
            }

            // Snare on beat 3 (i==4)
            if (i == 4) {
                Noise sn => BPF sb => Gain sg => master;
                2000.0 => sb.freq;
                2.0 => sb.Q;
                0.1 => sg.gain;
                5::ms => now;
                for (0 => int d; d < 8; d++) {
                    sg.gain() * 0.75 => sg.gain;
                    3::ms => now;
                }
                sg =< master; sn =< sb; sb =< sg;
            }
        }

        bar++;
        // Tempo drift
        if (bar % 8 == 0) {
            BPM + Math.random2f(-3.0, 5.0) => BPM;
            if (BPM < 100.0) 100.0 => BPM;
            if (BPM > 160.0) 160.0 => BPM;
        }
    }
}

// ============================================================
// ARPEGGIO — fast chippy runs, sporadic
// ============================================================
fun void arpLayer() {
    SqrOsc sq => LPF filt => Gain ag => master;
    4000.0 => filt.freq;
    1.5 => filt.Q;
    0.3 => sq.gain;

    while (true) {
        // Wait for a good moment
        Math.random2(3000, 8000)::ms => now;

        // Fast arp run
        Math.random2(4, 8) => int runLen;
        Math.random2(0, 4) => int startIdx;
        Math.random2(0, 1) => int dir;  // 0=up, 1=down

        for (0 => int n; n < runLen; n++) {
            int idx;
            if (dir == 0) (startIdx + n) % minPenta.size() => idx;
            else (startIdx - n + minPenta.size()) % minPenta.size() => idx;

            Std.mtof(minPenta[idx] + 12) => sq.freq;
            0.05 => ag.gain;

            stepMs() / 2 => int fast;
            if (fast < 30) 30 => fast;

            for (0 => int d; d < 4; d++) {
                ag.gain() * 0.7 => ag.gain;
                (fast / 4)::ms => now;
            }
        }
        0.0 => ag.gain;
    }
}

// ============================================================
// LAUNCH
// ============================================================
<<< "  Starforge Gameboy Evolve", "" >>>;
<<< "  8-bit chiptune with real melodies — never repeats", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ melody();
spork ~ counterMelody();
spork ~ bass();
spork ~ drums();
spork ~ arpLayer();

while (true) 1::second => now;
