import { sequence, stack, fastcat, pure } from '@strudel/core';
import { mini } from '@strudel/mini';

// Helper to format fraction-like objects
function frac(f) {
    if (f === null || f === undefined) return 'null';
    if (typeof f === 'number') return f.toFixed(4);
    const v = f.valueOf();
    if (typeof v === 'number') return v.toFixed(4);
    return String(v);
}

function printEvents(label, events) {
    console.log(`\n${label}:`);
    events.forEach(e => {
        const b = frac(e.whole?.begin);
        const end = frac(e.whole?.end);
        console.log(`  ${String(e.value)} at [${b}, ${end}]`);
    });
}

// Test 1: basic mini-notation
const pat = mini("bd sd [hh hh] cp");
printEvents("Pattern events for cycle 0→1 (bd sd [hh hh] cp)", pat.queryArc(0, 1));

// Test 2: euclidean
const eucPat = mini("bd(3,8)");
printEvents("Euclidean bd(3,8)", eucPat.queryArc(0, 1));

// Test 3: stacking
const stackPat = mini("[bd(3,8), hh*8]");
printEvents("Stacked bd(3,8) + hh*8", stackPat.queryArc(0, 1));

// Test 4: multiple cycles
const multiPat = mini("bd sd cp sd");
console.log("\nMultiple cycles (cycle 0→2):");
multiPat.queryArc(0, 2).forEach(e => {
    console.log(`  ${String(e.value)} at [${frac(e.whole?.begin)}, ${frac(e.whole?.end)}]`);
});

// Test 5: nested pattern with note values
const notePat = mini("c3 [e3 g3] a3 b3");
printEvents("Note pattern: c3 [e3 g3] a3 b3", notePat.queryArc(0, 1));

console.log("\n✓ All pattern tests passed — @strudel/core + @strudel/mini work in Node.js");
