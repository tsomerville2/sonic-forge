# sonic-forge 0.10.0: `--skill` hands agents the card, `[pause: short]` really is short, and PyPI finally has a README

**Pain:**
- Agents had no way to learn sonic-forge exists, or how to drive `narrate`, without being told.
- `[pause: short]` came out medium. The default blank-line pause swallowed any shorter marker.
- `narrate --help` silently deleted every `[pause: …]` example, because Rich read them as markup tags.
- On Linux, auto-pick fell back to macOS `say`.
- `--version` didn't exist and `__version__` said 0.5.0.
- PyPI showed no README.
- `rich` wasn't a declared dependency, so without it every help example was rewrapped into one paragraph.

## B) Summary
- **`sonic-forge --skill`** prints the stock SKILL.md, and `--skills` is an alias. The other actions:
  - `--skill install` installs it into `~/.claude/skills`, `~/.codex/skills` and `~/.agents/skills` wherever those agents exist, and reports where.
  - `--skill list [--json]` and `--skill export` follow the Skillflag draft spec (deterministic USTAR, sha256 digest).
- **Every run silently installs or refreshes the card.** Missing → written; ours and unchanged → updated; edited → left alone. `SONIC_FORGE_NO_SKILLS=1` opts out. State lives in `~/.sonic-forge/skills.json`.
- **`--pause-mode explicit`** comes from the 0.9.1 commit (3477854), now released. Proven with real Kokoro at seed 608, am_fenrir:

  | Mode | `[pause: short]` | `[pause: 0.3]` |
  |---|---|---|
  | explicit | 0.40 s | 0.315 s |
  | legacy | 0.95 s | 1.10 s |

  `legacy` stays the default, so old outputs remain byte-identical. `--help`, the card and the README all recommend explicit.
- **Help fixes:**
  - `--version`/`-V` added; `__version__` now comes from package metadata.
  - The top-level help is a real manual, with the narrate recipe and a line pointing agents at `--skill`.
  - narrate help documents the pause pools and the manifest, and escapes `\[pause` so the examples show.
  - `rich` is now a declared dependency.
  - A bad `--pause-mode` gives a clean error with exit 1.
- **Default engine:** off macOS (no `say` binary), the default engine is Kokoro with af_heart.
- **README.md:** install, narration, voices, FX, music, agents and the Python API. Wired as the PyPI readme, with keywords, classifiers and URLs.

## C) Decisions faced
- **Kept `legacy` as the default pause mode.** Flipping it would silently change every existing seeded narration on upgrade. explicit is the documented recommendation everywhere; video-maker passes it explicitly. *Deferred:* flip the default in a 1.0 with a changelog line.
- **Full-service install despite Skillflag's "producers MUST NOT install" rule.** That is the owner's position: newcomers need it working, and power users can delete a folder. This is the same choice navcom 0.2.2 made (`~/dev/navcom/diary/2026-09-30-navcom-022-skill-flag.md`). We stay compatible on list and export, so `npx skillflag install` still works.
- **`--skill` is handled in `run()` before typer.** Click can't express an option with an optional value. The callback declares `--skill` only so it appears in `--help`. The entry point changed from `sonic_forge.cli:app` to `sonic_forge.cli:run`, and `python -m sonic_forge` works too.
- **Rejected `rich_markup_mode=None`.** It drops typer to click's plain formatter, which rewraps every example. Escaping `\[` and requiring `rich` is right.
- **The card lives as a real file** (`src/sonic_forge/skills/sonic-forge/SKILL.md`), loaded with importlib.resources. It can be read and edited in the repo and ships in the wheel.

## C-2) Gritty tech snippets
```bash
sonic-forge --skill | head -3                        # frontmatter: name: sonic-forge
sonic-forge --skill list --json                      # digest == sha256(sonic-forge --skill export)
sonic-forge --skill export | tar -tvf -              # sonic-forge/ + sonic-forge/SKILL.md, mtime 0
python3.13 -m pytest tests -q                        # 28 passed (narrate e2e with say + skill/help/drift)

# release: standard PyPA tools via pipx (no uv)
rm -rf dist && pipx run build                          # sdist + wheel into dist/
pipx run twine check dist/*
TWINE_USERNAME=__token__ TWINE_PASSWORD=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.pypi-keys.json')))['pypi'])") \
  pipx run twine upload --non-interactive dist/*
pipx upgrade sonic-forge                               # this Mac runs the real PyPI install, like everyone else
```

## D) Files changed
- `src/sonic_forge/skill.py`: **skill card machinery**: targets, hash-guarded install, silent auto-install, Skillflag list/export, `cmd_skill`.
- `src/sonic_forge/skills/sonic-forge/SKILL.md`: **the agent card**: narrate recipe, pause table, timing.json, phonics, engines, voices, FX, music.
- `src/sonic_forge/cli.py`: **entry point `run()`**, `--version`, `--skill` in help, manual-style top help, narrate help (escaped markers, pools, manifest), `ValueError` → clean exit.
- `src/sonic_forge/__main__.py`: **`python -m sonic_forge`**.
- `src/sonic_forge/__init__.py`: **version from metadata**.
- `src/sonic_forge/tts.py`: **Linux default engine** is Kokoro when `say` is absent.
- `pyproject.toml`: **0.10.0**, readme, keywords, classifiers, URLs, `rich` dependency, script → `cli:run`.
- `README.md`: **PyPI page / project manual**.
- `tests/test_skill_and_help.py`: **tests**: skill show/list/export/install/silent/no-clobber/opt-out, version, help content, escaped markers, bad pause mode, docs-drift (every example in the README and card uses a real command and option), default engine.
- `diary/README.md`: **diary index** (new).

## E) Appendix
- PyPI before this release: 0.9.0. 0.9.1 was never published; 0.10.0 includes it and 702dcd0 (CLI/engine API drift fix, 2026-06-10).
- GitHub: `tsomerville2/sonic-forge` (public), pushed with the active gh account tsomerville2.
- Local install, as of 0.10.1: `pipx install "sonic-forge[kokoro]"` from PyPI, at `~/.local/bin/sonic-forge` (Python 3.13). Removed in the cleanup: the editable Homebrew install, the broken 0.5.2 pipx venv, and the repo's Aug-4 `uv.lock` and `.venv` (uv 0.8.3, never tracked).
- 0.10.1: voice counts corrected (54 Kokoro voices, 28 English; the old help said 27), and the top help fits 80 columns.
- video-maker now installs `sonic-forge[kokoro]==0.10.1` from PyPI in its Dockerfile. The vendored 0.9.1 wheel is gone; it was a stopgap from before 0.9.1 was published.

**Tags:** sonic-forge, release, pypi, skillflag, SKILL.md, agent-skills, --skill, pause-mode, typer-rich-markup, help-text, kokoro-default-linux. The CLI now explains itself to people and agents, and its pause markers mean what they say.
