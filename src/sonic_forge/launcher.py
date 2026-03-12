"""sonic-forge interactive launcher — the TUI that greets you."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path


# ── Song catalog ────────────────────────────────────────────────────────

SONGS = [
    # (key, display_name, description, category, engine, file_or_template)
    # engine: "yaml" = render via sonic-forge, "chuck" = play via chuck, "template" = generate on-the-fly

    # YAML songs
    ("trance-session", "Switch.Angel Session", "Acid trance, 136 BPM — live coding recreation", "SONGS", "yaml", "trance1_1.yaml"),
    ("midnight-drive", "Midnight Drive", "Moody C minor, 110 BPM — night city vibes", "SONGS", "yaml", "midnight.yaml"),
    ("starforge-awakens", "Starforge Awakens", "Epic E minor build, 128 BPM — the origin story", "SONGS", "yaml", "my_song.yaml"),
    ("captains-log", "The Captain's Log", "Full narrated, 124 BPM — the journey so far", "SONGS", "yaml", "captains_log_song.yaml"),
    ("captains-log-short", "Captain's Log (Short)", "Short narrated mix, 124 BPM", "SONGS", "yaml", "captains_log_short.yaml"),

    # ChucK tracks — ambient / journey
    ("space-synth", "Space Synth", "Organic synths + bowls + chippy arps, hours-long journey", "AMBIENT", "chuck", "space-synth.ck"),
    ("coding-ambient", "Coding Ambient", "Floating pads + euclidean pulses + sparse melody", "AMBIENT", "chuck", "coding-ambient.ck"),
    ("coding-flow", "Coding Flow", "Warm pads + gentle melodies, layers fade in slowly", "AMBIENT", "chuck", "coding-flow.ck"),
    ("singing-bowls", "Singing Bowls", "Tibetan brass bowls, tapped and swirled", "AMBIENT", "chuck", "singing-bowls.ck"),
    ("cathedral-drift", "Cathedral Drift", "Deep reverb pads, slow transformation", "AMBIENT", "chuck", "cathedral-drift.ck"),

    # ChucK tracks — dark
    ("dark-space", "Dark Space", "80s laser show: massive pads, epic leads, Vangelis vibes", "DARK", "chuck", "dark-space.ck"),
    ("dark-techno", "Dark Techno", "Tension-driven tempo, sidechain pump, 6-min arc", "DARK", "chuck", "dark-techno.ck"),
    ("dark-ambient", "Dark Ambient", "Sinister drones, metallic resonance, creeping dread", "DARK", "chuck", "dark-ambient.ck"),
    ("dark-industrial", "Dark Industrial", "Harsh, mechanical, acid bass, relentless", "DARK", "chuck", "dark-industrial.ck"),

    # ChucK tracks — electronic
    ("gameboy-evolve", "Gameboy Evolve", "8-bit chiptune with real melodies, never repeats", "ELECTRONIC", "chuck", "gameboy-evolve.ck"),
    ("euro-rave", "Euro Rave", "Acid bass, four-on-the-floor, sidechain pump", "ELECTRONIC", "chuck", "euro-rave.ck"),

    # Templates (generate on-the-fly, no YAML file needed)
    ("tpl-trance", "Trance (Generate)", "Classic trance — pluck arps, acid, supersaw peak, 136 BPM", "TEMPLATES", "template", "trance"),
    ("tpl-lofi", "Lo-Fi (Generate)", "Jazzy chords, mellow plucks, light groove, 78 BPM", "TEMPLATES", "template", "lofi"),
    ("tpl-cinematic", "Cinematic (Generate)", "Deep tension build, dramatic pads, 100 BPM", "TEMPLATES", "template", "cinematic"),
    ("tpl-ambient", "Ambient (Generate)", "Vast drifting pads, no beats, pure space, 68 BPM", "TEMPLATES", "template", "ambient"),
    ("tpl-acid", "Acid House (Generate)", "303 bass line, minimal drums, hypnotic, 132 BPM", "TEMPLATES", "template", "acid"),
    ("tpl-hiphop", "Hip Hop (Generate)", "Boom-bap beat, bass heavy, voice forward, 88 BPM", "TEMPLATES", "template", "hiphop"),
    ("tpl-minimal", "Minimal Techno (Generate)", "Hypnotic repetition, deep groove, 124 BPM", "TEMPLATES", "template", "minimal"),
    ("tpl-anthem", "Epic Anthem (Generate)", "Uplifting supersaws, triumphant pads, 138 BPM", "TEMPLATES", "template", "anthem"),
]


def _data_path(subdir: str, filename: str) -> str:
    """Get path to a bundled data file."""
    ref = resources.files("sonic_forge").joinpath(subdir).joinpath(filename)
    # resources.files returns a Traversable — for real files, as_posix works
    return str(ref)


def _check_chuck() -> bool:
    """Check if ChucK is installed."""
    return shutil.which("chuck") is not None


def _cmd_for_song(key: str, engine: str, filename: str) -> str:
    """Return the CLI command that would play this song."""
    if engine == "yaml":
        path = _data_path("tracks", filename)
        return f'sonic-forge play {key}'
    elif engine == "chuck":
        return f'sonic-forge play {key}'
    elif engine == "template":
        return f'sonic-forge play {key}'
    return f'sonic-forge play {key}'


def _play_yaml(filename: str, play: bool = True) -> None:
    """Render and play a bundled YAML song."""
    import tempfile
    from sonic_forge.songfile import render_yaml_song
    path = _data_path("tracks", filename)
    out = os.path.join(tempfile.gettempdir(), filename.replace(".yaml", ".wav"))
    render_yaml_song(path, output_path=out, play=play)


def _play_chuck(filename: str, minutes: int = 3) -> None:
    """Play a ChucK track."""
    if not _check_chuck():
        print("\n  ChucK is not installed.")
        print("  Install: brew install chuck")
        print(f"  Then: sonic-forge play {filename.replace('.ck', '')}\n")
        return
    path = _data_path("chuck", filename)
    print(f"\n  Playing {filename} ({minutes}m)... Ctrl-C to stop\n")
    try:
        subprocess.run(["chuck", f"{path}:{minutes}"])
    except KeyboardInterrupt:
        print("\n  Stopped.")


def _play_template(template_name: str, minutes: int = 3, play: bool = True) -> None:
    """Generate and play an instrumental template."""
    import tempfile
    import yaml
    from sonic_forge.songfile import render_yaml_song

    # Create a minimal YAML that triggers the template's instrumental mode
    song_data = {
        "title": f"{template_name} session",
        "bpm": 130,  # will be overridden by template
        "sections": [{"cycles": 4, "layers": [{"synth": "pad", "notes": "c3 e3 g3"}]}],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(song_data, f)
        tmp_path = f.name
    try:
        render_yaml_song(tmp_path, play=play, template_name=template_name,
                         target_duration=minutes * 60)
    finally:
        os.unlink(tmp_path)


def play_song(key: str, minutes: int | None = None) -> None:
    """Play a song by its key."""
    for entry in SONGS:
        if entry[0] == key:
            _, name, desc, cat, engine, filename = entry
            print(f"\n  {name}")
            print(f"  {desc}\n")
            if engine == "yaml":
                _play_yaml(filename)
            elif engine == "chuck":
                m = minutes if minutes is not None else 60
                _play_chuck(filename, minutes=m)
            elif engine == "template":
                m = minutes if minutes is not None else 3
                _play_template(filename, minutes=m)
            return
    print(f"\n  Unknown song: {key}")
    print(f"  Run 'sonic-forge' to see all available tracks.\n")


def list_songs() -> None:
    """Print the full song catalog."""
    has_chuck = _check_chuck()
    current_cat = None

    print()
    print("  \033[1;36m SONIC FORGE \033[0m")
    print("  \033[36m bytebeat music + TTS voice system\033[0m")
    print()

    for i, (key, name, desc, cat, engine, filename) in enumerate(SONGS):
        if cat != current_cat:
            current_cat = cat
            labels = {
                "SONGS": "\033[1;33m  COMPOSED SONGS\033[0m",
                "AMBIENT": "\033[1;32m  AMBIENT / JOURNEY\033[0m  (requires ChucK)" if not has_chuck else "\033[1;32m  AMBIENT / JOURNEY\033[0m",
                "DARK": "\033[1;31m  DARK\033[0m  (requires ChucK)" if not has_chuck else "\033[1;31m  DARK\033[0m",
                "ELECTRONIC": "\033[1;35m  ELECTRONIC\033[0m  (requires ChucK)" if not has_chuck else "\033[1;35m  ELECTRONIC\033[0m",
                "TEMPLATES": "\033[1;34m  TEMPLATES\033[0m  (generated on-the-fly)",
            }
            print(f"\n  {labels.get(cat, cat)}")
            print(f"  {'─' * 64}")

        num = f"{i + 1:>2}"
        avail = "" if engine != "chuck" or has_chuck else " \033[2m[need chuck]\033[0m"
        print(f"  {num}) \033[1m{name:<24}\033[0m \033[2m{key:<22}\033[0m {desc}{avail}")

    print(f"\n  {'─' * 64}")
    print(f"  \033[36m{len(SONGS)} tracks available\033[0m\n")


def interactive_menu() -> None:
    """Show the interactive launcher TUI."""
    has_chuck = _check_chuck()

    list_songs()

    print("  \033[1mPick a number above, or use the name directly next time:\033[0m")
    print("    sonic-forge play dark-space          sonic-forge play tpl-acid")
    print("    sonic-forge play midnight-drive      sonic-forge play gameboy-evolve -m 10")
    print()
    print("  \033[1mOTHER COMMANDS:\033[0m")
    print("    sonic-forge render song.yaml --play  Render any YAML song")
    print("    sonic-forge speak \"text\" --fx helmet  Text-to-speech with effects")
    print("    sonic-forge voices                   List all TTS voices")
    print("    sonic-forge catalog                  Show this track list again")
    print()

    # Interactive selection
    try:
        choice = input("  \033[1mPick a track (1-{}, name, or q): \033[0m".format(len(SONGS))).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not choice or choice.lower() == "q":
        return

    # Try as number
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(SONGS):
            key = SONGS[idx][0]
            engine = SONGS[idx][4]
            print(f"\n  \033[2mCommand: sonic-forge play {key}\033[0m")
            play_song(key)
            return
    except ValueError:
        pass

    # Try as key name (exact or partial match)
    choice_lower = choice.lower().replace(" ", "-")
    for entry in SONGS:
        if entry[0] == choice_lower or choice_lower in entry[0]:
            print(f"\n  \033[2mCommand: sonic-forge play {entry[0]}\033[0m")
            play_song(entry[0])
            return

    print(f"\n  Unknown selection: {choice}")
    print(f"  Try a number (1-{len(SONGS)}) or a track name.\n")
