// Starforge Singing Bowls — Tibetan brass bowls: tap and swirl
// Each bowl has a fundamental + inharmonic partials that beat against each other
// Run: chuck LABS/chuck-music/singing-bowls.ck

Gain master => NRev reverb => dac;
0.18 => reverb.mix;
0.4 => master.gain;

// Singing bowl: fundamental + partials with slow beating
// Real bowls have inharmonic overtones at ~2.71x, ~4.53x, ~6.65x of fundamental
fun void bowl(float freq, float vol, float decaySec) {
    // Fundamental
    SinOsc f1 => Gain g => master;
    // Inharmonic partials (the "singing" quality)
    SinOsc f2 => g;
    SinOsc f3 => g;
    SinOsc f4 => g;
    // Beating pair — slightly detuned from fundamental
    SinOsc f5 => g;

    freq => f1.freq;
    freq * 2.71 => f2.freq;
    freq * 4.53 => f3.freq;
    freq * 6.65 => f4.freq;
    freq * 1.002 => f5.freq;  // slow beat against fundamental

    // Partials are quieter
    vol => g.gain;
    0.5 => f1.gain;
    0.3 => f2.gain;
    0.15 => f3.gain;
    0.08 => f4.gain;
    0.45 => f5.gain;  // beating pair almost as loud

    // Very long exponential decay — bowls ring for a long time
    (decaySec * 1000.0) $ int => int totalMs;
    totalMs / 80 => int stepMs;
    if (stepMs < 30) 30 => stepMs;

    for (0 => int i; i < 80; i++) {
        vol * Math.pow(0.965, i $ float) => g.gain;
        // Higher partials decay faster
        Math.pow(0.90, i $ float) => float hiDecay;
        0.15 * hiDecay => f3.gain;
        0.08 * hiDecay => f4.gain;
        stepMs::ms => now;
    }

    0.0 => g.gain;
    g =< master;
    f1 =< g; f2 =< g; f3 =< g; f4 =< g; f5 =< g;
}

// Swirl: continuous tone that slowly modulates (like rubbing the rim)
fun void swirl(float freq, float vol, float durSec) {
    SinOsc f1 => Gain g => master;
    SinOsc f2 => g;
    SinOsc f3 => g;

    freq => f1.freq;
    freq * 2.71 => f2.freq;
    freq * 1.003 => f3.freq;  // beating

    0.0 => g.gain;
    0.3 => f2.gain;
    0.9 => f3.gain;

    (durSec * 1000.0) $ int => int totalMs;

    // Fade in
    for (0 => int i; i < 40; i++) {
        vol * (i / 40.0) => g.gain;
        // Wobble the frequency slightly (hand pressure variation)
        freq + Math.sin(i * 0.3) * 1.5 => f1.freq;
        (freq + Math.sin(i * 0.3) * 1.5) * 1.003 => f3.freq;
        25::ms => now;
    }

    // Sustain with slow wobble
    (totalMs - 2000) / 30 => int sustainStep;
    if (sustainStep < 30) 30 => sustainStep;
    for (0 => int i; i < 30; i++) {
        freq + Math.sin(i * 0.2) * 2.0 => f1.freq;
        (freq + Math.sin(i * 0.2) * 2.0) * 1.003 => f3.freq;
        // Volume gently pulses (like the bowl vibrating under the mallet)
        vol * (0.85 + 0.15 * Math.sin(i * 0.5)) => g.gain;
        sustainStep::ms => now;
    }

    // Fade out
    g.gain() => float startVol;
    for (0 => int i; i < 40; i++) {
        startVol * (1.0 - i / 40.0) => g.gain;
        25::ms => now;
    }

    0.0 => g.gain;
    g =< master;
    f1 =< g; f2 =< g; f3 =< g;
}

// Bowl frequencies — tuned to a pentatonic set (like a real bowl set)
// These are approximate frequencies of common singing bowls
[174.0,   // F3 — large deep bowl
 220.0,   // A3 — medium-large
 261.6,   // C4 — medium
 329.6,   // E4 — medium-small
 392.0,   // G4 — small
 523.3,   // C5 — very small, bright
 440.0    // A4 — medium high
] @=> float bowlFreqs[];

// === TAPPED BOWLS — random strikes with long decay ===
fun void tappedBowls() {
    while (true) {
        Math.random2(0, bowlFreqs.size()-1) => int idx;
        bowlFreqs[idx] => float freq;

        // Vary volume and decay — much longer tails
        Math.random2f(0.03, 0.07) => float vol;
        Math.random2f(12.0, 25.0) => float decay;

        spork ~ bowl(freq, vol, decay);

        // Organic spacing: clusters and long silences
        if (Math.random2f(0.0, 1.0) < 0.2) {
            // Cluster: two bowls close together
            Math.random2(600, 1500)::ms => now;
        } else if (Math.random2f(0.0, 1.0) < 0.3) {
            // Long contemplative gap
            Math.random2(8000, 16000)::ms => now;
        } else {
            // Normal spacing
            Math.random2(3000, 8000)::ms => now;
        }
    }
}

// === SWIRLED BOWLS — rim singing, less frequent ===
fun void swirledBowls() {
    // Wait a bit before first swirl
    3000::ms => now;

    while (true) {
        // Pick a bowl, usually the deeper ones for swirling
        Math.random2(0, 3) => int idx;
        bowlFreqs[idx] => float freq;

        Math.random2f(0.025, 0.05) => float vol;
        Math.random2f(5.0, 10.0) => float dur;

        spork ~ swirl(freq, vol, dur);

        // Long gaps between swirls
        Math.random2(8000, 18000)::ms => now;
    }
}

// === DEEP DRONE — very quiet fundamental hum ===
fun void deepDrone() {
    SinOsc d1 => Gain dg => master;
    SinOsc d2 => dg;
    0.02 => dg.gain;

    // Sub-bass bowl hum
    bowlFreqs[0] / 2.0 => d1.freq;  // octave below lowest bowl
    d1.freq() * 1.001 => d2.freq;    // very slow beating

    // Just sits there quietly, grounding everything
    while (true) {
        // Slowly drift between the two lowest bowl fundamentals
        (bowlFreqs[0] / 2.0) => float f1;
        (bowlFreqs[1] / 2.0) => float f2;
        Math.random2f(f1, f2) => float target;

        d1.freq() => float start;
        for (0 => int i; i < 100; i++) {
            start + (target - start) * (i / 100.0) => d1.freq;
            d1.freq() * 1.001 => d2.freq;
            80::ms => now;
        }
        Math.random2(3000, 8000)::ms => now;
    }
}

// === LAUNCH ===
<<< "  Starforge Singing Bowls", "" >>>;
<<< "  Tibetan brass bowls — tapped and swirled", "" >>>;
<<< "  Ctrl-C to stop", "" >>>;
<<< "" >>>;

spork ~ tappedBowls();
spork ~ swirledBowls();
spork ~ deepDrone();

while (true) 1::second => now;
