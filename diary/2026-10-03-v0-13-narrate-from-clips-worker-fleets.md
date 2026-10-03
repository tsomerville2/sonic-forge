# sonic-forge 0.13.0: one narration, many machines — `narrate --from-clips`, `clip`, `--segments`

**Pain:** a long script in a cloned voice takes minutes on one machine (Chatterbox is autoregressive; CPU ~0.7–3.4 s of
compute per second of speech). video-maker has a worker fleet, but `narrate` could only speak a whole script in one
process, so the fleet couldn't split the work without the result drifting from a single-machine narrate (different
pauses, different seeds, double levelling, a different manifest).

## B) Summary
- **`script_segments(text, phonics=None, pause_mode="legacy", seed=None) -> list[dict]`** — the exact plan narrate
  speaks: phonics on the whole text, `split_script` with `random.Random(seed)`, adjacent pauses collapsed by max,
  leading/trailing pauses trimmed. `{"kind":"text","text","index":k}` (k counts text only) / `{"kind":"pause","seconds"}`.
  `narrate` now calls it, so the two can't drift.
- **`speak_clip(text, out_path, engine=None, voice=None, seed=None, index=0, phonics=None, sample_rate=24000)`** — one
  paragraph exactly as narrate speaks text segment `index`: same resolution, `_tts_paragraph` for say/kokoro/edge,
  `clone.synthesize([text], …, jobs=1, seed=seed+index)` for chatterbox, NOT levelled, re-encoded mono s16le.
- **`narrate_from_clips(input_path, clips_dir, output_path, engine=None, seed=None, pause_mode="legacy", phonics=None,
  fps=30, sample_rate=24000, write_manifest=True, verbose=True) -> Path`** — ffmpeg only. `clips_dir/0000.wav…` one per
  text segment; same seeded pauses, same re-encode/silence/concat, one -4.5 dB peak levelling when engine=chatterbox,
  identical `<out>.timing.json`. Missing/extra clips → ValueError with expected vs found counts + first missing file.
- Both narrate and narrate_from_clips end in one shared `_assemble()`.
- **CLI:** `narrate SCRIPT --segments` (OUT optional only then), `narrate SCRIPT OUT --from-clips DIR`, `clip TEXTFILE OUT`.
- **Warm clone model:** `clone.synthesize(jobs=1)` reuses the in-process model when the (reference, backend, threads)
  match, so a worker calling speak_clip in a loop loads Chatterbox once. Kokoro was already a module singleton.

## C) Decisions faced
- **One shared assembler, not a copy.** narrate's loop became `_assemble(segments, speech_for, …)`; narrate passes a
  callback that speaks, from-clips one that returns `clips/k:04d.wav`. Rejected: duplicating the loop (drift risk).
- **Refactor proven byte-identical against HEAD** before anything else: say + fake-chatterbox, legacy + explicit, seed,
  phonics, `[pause: long]` — same sha256 for WAV and manifest before/after.
- **speak_clip applies `phonics` to its text.** Text taken from `--segments`/`script_segments(..., phonics=…)` already
  has it, so workers pass phonics=None for that text (documented in help, README, card). Rejected: making speak_clip
  skip phonics (raw-paragraph callers would lose them).
- **Clip naming `k:04d.wav`, k = text index only** (not the manifest index, which counts pauses too).
- **Engine for assembly is just `engine == "chatterbox"`** (decides levelling); no voice resolution, so from-clips never
  needs the reference wav or any model.
- **Re-encoding a clip twice is lossless:** speak_clip resamples once to 24 kHz s16; from-clips' second re-encode at the
  same rate/format is an identity, so samples match narrate's single re-encode. Proven by the tests (44.1 kHz tones).
- **Deferred:** a torch-backend real-model check on this Mac (the pipx venv has clone-mlx, not chatterbox-tts torch).

## C-2) Gritty tech snippets
```bash
sonic-forge narrate script.txt --segments --seed 7 --pause-mode explicit           # plan JSON
sonic-forge clip - clips/0003.wav --engine chatterbox --voice me.wav --seed 7 --index 3 < para3.txt
sonic-forge narrate script.txt narration.wav --from-clips clips --engine chatterbox --seed 7 --pause-mode explicit

# tests (throwaway venv; tests/visual are interactive scripts needing PIL — not part of the suite)
python -m pytest -q --ignore=tests/visual                                          # 71 passed, 4 skipped
# real voices (Kokoro + cloned voice on this Mac's backend), byte-identical clips vs narrate:
SONIC_FORGE_SLOW=1 ~/.local/pipx/venvs/sonic-forge/bin/python -m unittest tests.test_narrate_from_clips.RealVoices

# release (standard PyPA via pipx, no uv)
pipx run build && pipx run twine check dist/sonic_forge-0.13.0*
pipx run twine upload dist/sonic_forge-0.13.0*                                      # owner runs this
```

## D) Files changed
- `src/sonic_forge/narrate.py` — [api][fleet] script_segments, clip_name, _assemble, speak_clip, narrate_from_clips; narrate refactored onto them.
- `src/sonic_forge/clone.py` — [perf] in-process model stays warm across synthesize(jobs=1) calls (`_loaded` key).
- `src/sonic_forge/cli.py` — [cli] narrate `--from-clips`/`--segments` (OUT optional for --segments), new `clip` command, help examples.
- `tests/test_narrate_from_clips.py` — [tests] byte-identity narrate vs from-clips (legacy/explicit, phonics, long pauses, chatterbox levelling), speak_clip seed+index/no-levelling, count mismatch, CliRunner `--segments`/`clip`, no heavy imports, warm model; SLOW real-voice checks.
- `README.md`, `src/sonic_forge/skills/sonic-forge/SKILL.md` — [docs] "Narration from clips (worker fleets)", What's new in 0.13.
- `pyproject.toml` — [release] 0.13.0.

## E) Appendix
- Verified live 2026-10-03 on the M2 Max: Kokoro am_fenrir seed 608 and Chatterbox Turbo on mlx (seed 7) — narrate vs
  per-paragraph speak_clip + narrate_from_clips: WAV and manifest byte-identical, including each clip spoken in its own
  fresh process (cold model load per clip).
- Wheel e2e in a fresh venv (no numpy/torch): `--segments`, sine-tone `--from-clips`, missing-clip error (exit 1), and
  `clip --engine say` x3 + `--from-clips` == `narrate --engine say`, byte-identical.
- All workers in a fleet must share the clone backend: mlx and torch audio differ for the same seed.

Tags: sonic-forge, 0.13.0, narrate, from-clips, worker-fleet, speak_clip, script_segments, chatterbox, byte-identical, release.
Meaning: a narration can now be spoken across a fleet and assembled on one machine with output identical to a one-machine narrate.
