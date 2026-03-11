# Strudel Node.js Proof-of-Concept — Report

**Date:** 2026-03-10
**Goal:** Does the Strudel pattern engine work in Node.js, and what is the simplest path to audio output?

---

## Does @strudel/core + @strudel/mini work in Node? YES

With one caveat: a package.json patch is required.

`@strudel/core` statically imports `{ SalatRepl }` from `@kabelsalat/web`.
The `@kabelsalat/web` package ships both `dist/index.mjs` (ESM) and `dist/index.js`
(CJS), but its `package.json` has no `exports` field. Node.js therefore falls back to
`main: "dist/index.js"` (CJS). A static ESM named import from a CJS module fails with:

```
SyntaxError: The requested module '@kabelsalat/web' does not provide an export named 'SalatRepl'
```

**Fix:** Add an `exports` field to `@kabelsalat/web/package.json`:
```json
"exports": {
  ".": {
    "import": "./dist/index.mjs",
    "require": "./dist/index.js",
    "default": "./dist/index.mjs"
  }
}
```

This is a one-liner fix; once applied, everything works. In a real project this should
be an `npm patch` or `postinstall` script.

---

## Total Install Size

| Package | Size |
|---|---|
| `@strudel/core` + `@strudel/mini` | 932 KB |
| `@kabelsalat/*` (transitive dep) | 472 KB |
| `node-web-audio-api` | 41 MB |
| **Total node_modules** | **52 MB** |

Without `node-web-audio-api`, the pattern-only install is ~1.4 MB — genuinely lightweight.
`node-web-audio-api` is heavy (Rust-compiled native addon via napi-rs).

---

## Did node-web-audio-api work? YES

`node-web-audio-api@1.0.8` installed cleanly and `OfflineAudioContext` worked correctly:
- Created an 8-second, 44100 Hz offline rendering context
- Scheduled 56 synthesized drum events using the Web Audio API
- Called `ctx.startRendering()` — rendered 352,800 samples
- Result: a valid WAV file with 100% peak amplitude and 56.8% non-zero samples

The API is a complete drop-in for browser Web Audio API. `OscillatorNode`,
`BiquadFilterNode`, `GainNode`, `AudioBufferSourceNode`, `createBuffer()` all work.

---

## What Was the Simplest Path to Audio Output?

**Pattern engine → OfflineAudioContext → WAV file**

1. `mini("pattern")` → `pat.queryArc(0, N)` gives you an array of events
2. Each event has `event.value` (a string like `"bd"`, `"hh"`) and `event.whole.begin/end`
   (fractional cycle positions as Fraction objects — use `.valueOf()` to get floats)
3. Convert cycle position to seconds: `startTime = event.whole.begin.valueOf() * SECONDS_PER_CYCLE`
4. Schedule Web Audio API nodes on `OfflineAudioContext`
5. `await ctx.startRendering()` → `AudioBuffer`
6. Write PCM samples from `audioBuffer.getChannelData(c)` as int16 LE into a WAV file

The pure-JS WAV writer is ~50 lines with no dependencies.

**Pure-JS alternative (no node-web-audio-api):** Also viable. You'd compute PCM samples
directly by iterating timed events and filling a Float32Array with sine waves/noise. Tested
and works, but you lose the declarative Web Audio scheduling API. The node-web-audio-api
path is cleaner.

---

## Sample Output from Pattern Queries

Pattern: `bd sd [hh hh] cp`
```
bd at [0.0000, 0.2500]
sd at [0.2500, 0.5000]
hh at [0.5000, 0.6250]
hh at [0.6250, 0.7500]
cp at [0.7500, 1.0000]
```

Euclidean `bd(3,8)`:
```
bd at [0.0000, 0.1250]
bd at [0.3750, 0.5000]
bd at [0.7500, 0.8750]
```

Stacked `[bd(3,8), hh*8]`:
```
bd at [0.0000, 0.1250]
bd at [0.3750, 0.5000]
bd at [0.7500, 0.8750]
hh at [0.0000, 0.1250]
hh at [0.1250, 0.2500]
hh at [0.2500, 0.3750]
hh at [0.3750, 0.5000]
hh at [0.5000, 0.6250]
hh at [0.6250, 0.7500]
hh at [0.7500, 0.8750]
hh at [0.8750, 1.0000]
```

Note pattern `c3 [e3 g3] a3 b3`:
```
c3 at [0.0000, 0.2500]
e3 at [0.2500, 0.3750]
g3 at [0.3750, 0.5000]
a3 at [0.5000, 0.7500]
b3 at [0.7500, 1.0000]
```

---

## Key Gotchas

1. **`e.value` is a String object** (not `{ s: "bd" }`). Access with `String(e.value)`, not `e.value.s`.
2. **`e.whole.begin` is a Fraction** (BigInt-based). Use `.valueOf()` for float arithmetic.
   Cannot `JSON.stringify()` events directly — BigInt serialization error.
3. **`cannot use window: not in browser?`** — harmless warning from kabelsalat at load time.
4. **`@kabelsalat/web` package.json needs patching** — this is a bug in that package upstream.
   A real project should use an `npm postinstall` patch script.

---

## Verdict: VIABLE

The path is:
```
mini("bd(3,8) hh*8") → queryArc → OfflineAudioContext → WAV
```

All three layers work in Node.js. Pattern engine is ~1MB clean. Audio output is real.
Files: `test-patterns.mjs` (pattern tests), `play.mjs` (synthesis → WAV), `output.wav` (result).
