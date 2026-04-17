# Kokoro-82M Pause & Emotion Control via Punctuation Stacking

> Discovered 2026-04-13. Undocumented emergent behavior in Kokoro-82M ONNX.
> Tested with `am_onyx` voice. Likely applies to all Kokoro voices.

## Summary

Kokoro-82M has no official pause or emotion control API. However, stacking punctuation characters inline creates controllable pauses with emergent vocal behaviors (humming, contemplation sounds). This enables expressive narration without switching TTS engines.

## Period Stacking (.)

Periods are the cleanest pause mechanism. They produce natural breath-like gaps and, at higher counts, a distinctive "mmmm" thinking vocalization.

| Count | Gap Duration | Behavior |
|-------|-------------|----------|
| 1-2 | 0.3s | Minimal — normal sentence boundary |
| 4 | 0.5s | First useful breath pause |
| 8 | 0.7s | Good breath pause |
| 16 | 1.6s | "mmmm" thinking sound appears |
| 32 | 2.3s | **Peak** — longest reliable period pause |
| 64 | 0.3s | **Collapsed** — model ignores them |
| 128 | 1.1s (scattered) | Partial recovery, unreliable |
| 256 | 0.9s | Collapsed harder |

**Sweet spot: 4-32 periods.**

## Exclamation Mark Stacking (!)

Exclamation marks scale further than periods before collapsing. They produce similar humming/contemplation sounds at high counts.

| Count | Longest Gap | Total Quiet Zone | Behavior |
|-------|-----------|-----------------|----------|
| 1-2 | — | — | No pause effect |
| 4 | 0.3s | 0.3s | First noticeable |
| 8 | 0.7s | 0.7s | |
| 16 | 0.7s | 0.7s | |
| 32 | 1.8s | 1.8s | "mmmm" humming begins |
| 64 | 1.2s | 1.2s | Slight dip |
| 128 | **2.4s** | **4.5s** | **Peak** — massive contemplation zone |
| 256 | 1.2s | 3.6s | Degrading gracefully |

**Sweet spot: 32-128 exclamation marks.**

## Combined Strategy

Use periods for short pauses (they kick in at lower counts) and exclamation marks for long pauses (they scale further):

| Desired Effect | Technique | Example |
|---------------|-----------|---------|
| Breath pause (~0.5s) | 4-8 periods | `simple idea.... You are` |
| Thinking pause (~1.5s) | 16 periods | `in their own life................ And every` |
| Section break (~2.3s) | 32 periods | `control................................ Historically` |
| Long contemplation (~2.4s) | 128 exclamation marks | `without us!!!!!!!!...x128... That means` |

## What Does NOT Work

| Technique | Result |
|-----------|--------|
| Em-dashes (— — —) | Growly/guttural artifacts |
| Semicolons (;;;;) | Computerized/digital artifacts |
| Mixed punctuation (.,;—) | Growly sounds |
| Spaced periods (. . . .) | Shorter than packed, no benefit |
| Repeated consonants (mmmmm, hhhh) | Spelled out letter-by-letter |

## Filler Words That Work

These produce natural vocal sounds when placed between pauses:

- `hee hee` — light laugh
- `heh` — soft chuckle
- `tsk` — disapproval/thinking
- `yikes` — surprise
- `sheesh` — exasperation
- `phew` — relief
- `oh` / `ahhh` — realization (neutral delivery)
- `well well well` — contemplation
- `ooh la la` — playful

## The "mmmm" Thinking Sound

At 16+ periods or 32+ exclamation marks, Kokoro produces a low-frequency humming vocalization — like a person thinking or contemplating. This is NOT silence; it's emergent vocal behavior from the model interpreting dense punctuation as a cue to produce non-speech audio. It sounds natural and human-like.

## Script Conversion Guidelines

When converting a plain narration script for Kokoro:

1. **Between sentences in same paragraph**: 4-8 periods (breath)
2. **Between key concepts**: 16 periods (thinking pause)
3. **Between major sections**: 32 periods (section break)
4. **Before important statements**: 16 periods + filler word like "well" or "oh"
5. **After emotional moments**: 8 periods (let it land)
6. **Kokoro speaks too fast by default** — sprinkle periods throughout to slow pace
7. **Never use em-dashes for pauses** — they produce no pause effect in Kokoro

## Example: Before and After

**Original script:**
```
Person-centered support starts with a simple idea. You are the expert in your own life.
And every individual you support is the expert in theirs.
```

**Kokoro-optimized:**
```
Person-centered support starts with a simple idea........ You are the expert,
in your own life................ And every individual you support....
is the expert in theirs................................
```
