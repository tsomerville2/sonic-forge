"""sonic-forge's agent skill card (SKILL.md): print it, export it, install it.

    sonic-forge --skill                  print the stock SKILL.md
    sonic-forge --skill install          (re)install it for every coding agent here, and show where
    sonic-forge --skill list [--json]    Skillflag-compatible listing (github.com/osolmaz/skillflag)
    sonic-forge --skill export           Skillflag-compatible tar stream (one top-level sonic-forge/ dir)

Every run also installs or refreshes the card silently, the same way: missing → written,
ours and unchanged → updated on upgrade, edited by someone → left alone.
SONIC_FORGE_NO_SKILLS=1 turns the silent install off.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tarfile
from importlib import resources
from pathlib import Path

SKILL_NAME = "sonic-forge"
SKILL_SUMMARY = ("Voiceovers, narration WAV + frame-accurate timing manifest, TTS voices in 20+ languages, "
                 "voice FX and code-generated music with the sonic-forge CLI")
SKILL_MARKER = "<!-- managed by sonic-forge: updated automatically on upgrade; edit freely and it will be left alone -->"
ACTIONS = ("show", "list", "export", "install")


def skill_md() -> str:
    return resources.files("sonic_forge").joinpath("skills", SKILL_NAME, "SKILL.md").read_text(encoding="utf-8")


def _version() -> str:
    from sonic_forge import __version__
    return __version__


def _env_path(name: str):
    v = os.environ.get(name)
    return Path(v).expanduser() if v else None


def skill_targets() -> list[Path]:
    """Skill folders of the coding agents that are actually installed here."""
    home = Path.home()
    claude_home = _env_path("CLAUDE_CONFIG_DIR") or home / ".claude"
    codex_home = _env_path("CODEX_HOME") or home / ".codex"
    targets = []
    if claude_home.is_dir():
        targets.append(claude_home / "skills")          # Claude Code (opencode and goose read it too)
    if codex_home.is_dir():
        targets.append(codex_home / "skills")           # Codex
    agents_users = [home / ".agents", home / ".pi", home / ".omo", home / ".local" / "share" / "opencode",
                    home / ".config" / "opencode", home / ".config" / "goose", home / ".gemini"]
    if any(p.is_dir() for p in agents_users):
        targets.append(home / ".agents" / "skills")     # Agent Skills standard: pi, omo, opencode, goose
    return targets


def _state_path() -> Path:
    return Path.home() / ".sonic-forge" / "skills.json"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def install_skills(force: bool = False, report: bool = False) -> list[tuple[Path, str]]:
    """Write or refresh the card in every agent's skill folder; never clobber someone's edits."""
    card = skill_md()
    want = _digest(card)
    state_path = _state_path()
    try:
        state = json.loads(state_path.read_text())
    except Exception:
        state = {}
    changed, done = False, []
    for root in skill_targets():
        path = root / SKILL_NAME / "SKILL.md"
        key = str(path)
        try:
            current = path.read_text(encoding="utf-8") if path.exists() else None
        except OSError:
            continue
        if current is not None and _digest(current) == want:
            if state.get(key) != want:
                state[key], changed = want, True
            done.append((path, "up to date"))
            continue
        ours = current is None or (SKILL_MARKER in current and state.get(key) in (None, _digest(current)))
        if not ours and not force:
            done.append((path, "left alone (edited by someone)"))
            continue
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(card, encoding="utf-8")
        except OSError as exc:
            done.append((path, f"not writable: {exc}"))
            continue
        state[key], changed = want, True
        done.append((path, "installed" if current is None else "updated"))
    if changed:
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state, indent=1))
        except OSError:
            pass
    if report:
        if not done:
            print("sonic-forge: no coding agent found to install the skill into "
                  "(looked for ~/.claude, ~/.codex, ~/.agents and friends)")
        for path, what in done:
            print(f"  {what:32s} {path}")
    return done


def auto_install_skills() -> None:
    """Silent and cheap (a few stats and small reads); never fails the command."""
    if os.environ.get("SONIC_FORGE_NO_SKILLS"):
        return
    try:
        install_skills()
    except Exception:
        pass


def skill_tar_bytes() -> bytes:
    """The skill as a deterministic ustar stream with exactly one top-level <id>/ dir (Skillflag spec §9)."""
    buf = io.BytesIO()
    data = skill_md().encode("utf-8")
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, payload in ((f"{SKILL_NAME}/", None), (f"{SKILL_NAME}/SKILL.md", data)):
            info = tarfile.TarInfo(name.rstrip("/"))
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "root", "root"
            if payload is None:
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                tar.addfile(info)
            else:
                info.size, info.mode = len(payload), 0o644
                tar.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


def cmd_skill(argv: list[str]) -> int:
    """`sonic-forge --skill [show|list|export|install] [id] [--json]`. Returns an exit code."""
    as_json = "--json" in argv
    words = [a for a in argv if not a.startswith("-")]
    action = (words[0] if words else "show").lower()
    skill_id = words[1] if len(words) > 1 else SKILL_NAME
    if action in ("-h", "help"):
        action = "help"
    if action not in ACTIONS + ("help",):
        sys.stderr.write(f"sonic-forge: --skill takes show (default), list, export or install, not {action!r}\n")
        return 2
    if action == "help" or "--help" in argv or "-h" in argv:
        print(__doc__.split("\n\n")[1].rstrip())
        return 0
    if action != "list" and skill_id != SKILL_NAME:
        sys.stderr.write(f"sonic-forge: no skill {skill_id!r}; sonic-forge ships one: {SKILL_NAME}\n")
        return 1
    if action == "show":
        sys.stdout.write(skill_md())
    elif action == "list":
        if as_json:
            print(json.dumps({"skillflag_version": "0.1", "skills": [{
                "id": SKILL_NAME, "summary": SKILL_SUMMARY, "version": _version(), "files": 1,
                "digest": "sha256:" + hashlib.sha256(skill_tar_bytes()).hexdigest()}]}))
        else:
            print(f"{SKILL_NAME}\t{SKILL_SUMMARY}")
    elif action == "export":
        sys.stdout.buffer.write(skill_tar_bytes())
        sys.stdout.flush()
    else:
        install_skills(force=True, report=True)
    return 0
