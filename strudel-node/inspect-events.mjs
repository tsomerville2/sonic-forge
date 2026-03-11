import { mini } from '@strudel/mini';

// Inspect raw event structure
const pat = mini("bd sd [hh hh] cp");
const events = pat.queryArc(0, 1);
const e = events[0];
console.log("First event keys:", Object.keys(e));
console.log("First event value:", e.value);
console.log("First event value type:", typeof e.value);
console.log("First event whole:", e.whole?.toString?.() ?? e.whole);
console.log("First event part:", e.part?.toString?.() ?? e.part);

// Try inspecting prototype
console.log("\nValue prototype keys:", e.value ? Object.keys(e.value) : 'null');
console.log("Value constructor:", e.value?.constructor?.name);

// Check if value has string representation
console.log("Value string:", String(e.value));

// Look at all events
console.log("\nAll events:");
events.forEach((ev, i) => {
    const val = ev.value;
    console.log(`  Event ${i}: value=${val} (${typeof val}), whole=[${ev.whole?.begin?.valueOf()}, ${ev.whole?.end?.valueOf()}]`);
    if (val && typeof val === 'object') {
        console.log('    value keys:', Object.keys(val));
    }
});
