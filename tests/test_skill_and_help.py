"""The skill card, --skill, --version and --help: what an agent or a newcomer reads first.

Runs the real CLI in subprocesses with a throwaway HOME, so nothing touches the real agent folders.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shlex
import site
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sonic_forge.skill import SKILL_MARKER, SKILL_NAME, skill_md  # noqa: E402


class CliCase(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "HOME": str(self.home), "COLUMNS": "200", "PYTHONPATH": os.pathsep.join([str(SRC), site.getusersitepackages()])}
        for k in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "SONIC_FORGE_NO_SKILLS"):
            self.env.pop(k, None)

    def sf(self, *args, env=None, binary=False):
        return subprocess.run([sys.executable, "-m", "sonic_forge", *args], capture_output=True,
                              env=env or self.env, cwd=str(self.home), timeout=120, text=not binary)


class SkillTests(CliCase):
    def test_bare_skill_prints_the_stock_card(self):
        r = self.sf("--skill")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith(f"---\nname: {SKILL_NAME}\ndescription: "), r.stdout[:120])
        self.assertEqual(r.stdout, skill_md())
        self.assertIn(SKILL_MARKER, r.stdout)

    def test_skills_alias(self):
        self.assertEqual(self.sf("--skills").stdout, skill_md())

    def test_list_and_json_digest_matches_export(self):
        r = self.sf("--skill", "list")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith(f"{SKILL_NAME}\t"))
        listing = json.loads(self.sf("--skill", "list", "--json").stdout)
        self.assertEqual(listing["skillflag_version"], "0.1")
        exported = self.sf("--skill", "export", binary=True).stdout
        self.assertEqual(listing["skills"][0]["digest"], "sha256:" + hashlib.sha256(exported).hexdigest())

    def test_export_is_one_dir_one_file_and_deterministic(self):
        a = self.sf("--skill", "export", binary=True).stdout
        b = self.sf("--skill", "export", binary=True).stdout
        self.assertEqual(a, b)
        with tarfile.open(fileobj=io.BytesIO(a)) as tar:
            self.assertEqual(sorted(tar.getnames()), [SKILL_NAME, f"{SKILL_NAME}/SKILL.md"])
            self.assertTrue(all(m.mtime == 0 and m.uid == 0 for m in tar.getmembers()))
            self.assertEqual(tar.extractfile(f"{SKILL_NAME}/SKILL.md").read().decode(), skill_md())

    def test_bad_action_and_unknown_id(self):
        self.assertEqual(self.sf("--skill", "frobnicate").returncode, 2)
        self.assertEqual(self.sf("--skill", "show", "nope").returncode, 1)

    def test_install_reports_every_agent_present(self):
        for d in (".claude", ".codex", ".agents"):
            (self.home / d).mkdir()
        r = self.sf("--skill", "install")
        self.assertEqual(r.returncode, 0, r.stderr)
        for d in (".claude", ".codex", ".agents"):
            card = self.home / d / "skills" / SKILL_NAME / "SKILL.md"
            self.assertEqual(card.read_text(), skill_md())
            self.assertIn(str(card), r.stdout)

    def test_install_with_no_agents_says_so(self):
        r = self.sf("--skill", "install")
        self.assertEqual(r.returncode, 0)
        self.assertIn("no coding agent found", r.stdout)

    def test_any_run_installs_silently_and_never_clobbers_edits(self):
        (self.home / ".claude").mkdir()
        card = self.home / ".claude" / "skills" / SKILL_NAME / "SKILL.md"
        r = self.sf("templates")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(card.read_text(), skill_md())
        self.assertNotIn("SKILL", r.stdout)                        # silent
        card.write_text(skill_md() + "\nmy own note\n")             # someone edits it
        self.sf("templates")
        self.assertIn("my own note", card.read_text())              # left alone
        self.sf("--skill", "install")                               # an explicit install does replace it
        self.assertEqual(card.read_text(), skill_md())

    def test_opt_out(self):
        (self.home / ".claude").mkdir()
        self.sf("templates", env={**self.env, "SONIC_FORGE_NO_SKILLS": "1"})
        self.assertFalse((self.home / ".claude" / "skills").exists())


class HelpTests(CliCase):
    def test_version(self):
        from sonic_forge import __version__
        for flag in ("--version", "-V"):
            r = self.sf(flag)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), f"sonic-forge {__version__}")

    def test_top_help_points_agents_at_skill(self):
        out = self.sf("--help").stdout
        self.assertIn("sonic-forge --skill prints the skill card.", out)
        self.assertIn("--skill", out)
        self.assertIn("--version", out)
        self.assertIn("sonic-forge narrate script.txt out.wav", out)

    def test_narrate_help_shows_pause_markers_literally(self):
        # Rich treats [pause: short] as a markup tag and deletes it unless escaped.
        out = self.sf("narrate", "--help").stdout
        for marker in ("[pause: tiny]", "[pause: short]", "[pause: long]", "[pause: xlong]", "[pause: 1.2]"):
            self.assertIn(marker, out)
        self.assertIn("--pause-mode", out)
        self.assertIn("explicit (recommended)", out)

    def test_bad_pause_mode_is_a_clean_error(self):
        script = self.home / "s.txt"
        script.write_text("Hello.\n")
        r = self.sf("narrate", str(script), str(self.home / "o.wav"), "--pause-mode", "fast")
        self.assertEqual(r.returncode, 1)
        self.assertIn("pause_mode must be", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)


class DocsDontDrift(CliCase):
    """Every `sonic-forge COMMAND --option` in the skill card and README names a real command and option."""

    def commands(self, text):
        for line in text.splitlines():
            m = re.search(r"(?:^|\|\s*|`)\s*sonic-forge\s+([^`#|]*)", line)
            if m:
                yield m.group(1).strip()

    def check(self, text, where):
        import typer.main
        from sonic_forge.cli import app
        group = typer.main.get_command(app)
        top_opts = {o for p in group.params for o in p.opts} | {"--help"}
        seen = 0
        for cmd in self.commands(text):
            try:
                words = shlex.split(cmd)
            except ValueError:
                continue
            if not words or words[0].startswith("--skill") or words[0] in top_opts or words[0] == "COMMAND":
                continue
            seen += 1
            sub = group.commands.get(words[0])
            self.assertIsNotNone(sub, f"{where}: unknown command in `sonic-forge {cmd}`")
            opts = {o for p in sub.params for o in getattr(p, "opts", [])} | {"--help"}
            for w in words[1:]:
                if w.startswith("-") and w != "-":
                    self.assertIn(w.split("=")[0], opts, f"{where}: `sonic-forge {cmd}` uses unknown option {w}")
        self.assertGreater(seen, 8, f"{where}: found too few examples to check")

    def test_skill_card(self):
        self.check(skill_md(), "SKILL.md")

    def test_readme(self):
        self.check((REPO_ROOT / "README.md").read_text(), "README.md")


class DefaultEngine(unittest.TestCase):
    def test_no_say_binary_means_kokoro(self):
        from unittest import mock
        from sonic_forge import tts
        with mock.patch.object(tts.shutil, "which", return_value=None):
            self.assertEqual(tts.resolve_voice(), ("kokoro", "af_heart"))
        with mock.patch.object(tts.shutil, "which", return_value="/usr/bin/say"):
            self.assertEqual(tts.resolve_voice(), ("say", "Samantha"))
        self.assertEqual(tts.resolve_voice(engine="say"), ("say", "Samantha"))   # an explicit choice still wins


if __name__ == "__main__":
    unittest.main()
