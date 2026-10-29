"""sonic-forge interactive launcher — the TUI that greets you."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path


# ── User songs directory ────────────────────────────────────────────────

USER_SONGS_DIR = Path.home() / ".sonic-forge" / "songs"


def _ensure_user_dir() -> Path:
    """Create ~/.sonic-forge/songs/ if it doesn't exist."""
    USER_SONGS_DIR.mkdir(parents=True, exist_ok=True)
    return USER_SONGS_DIR


# ── Built-in song catalog ──────────────────────────────────────────────

BUILTIN_SONGS = [
    # (key, display_name, description, category, engine, file_or_template)
    # engine: "yaml" = bytebeat render, "chuck" = real-time synth, "template" = generate on-the-fly

    # Bytebeat — composed songs with narration
    ("trance-session", "Switch.Angel Session", "Acid trance, 136 BPM — recreated from her streams", "BYTEBEAT_NARRATED", "yaml", "trance1_1.yaml"),
    ("midnight-drive", "Midnight Drive", "Moody C minor, 110 BPM — night city vibes", "BYTEBEAT_NARRATED", "yaml", "midnight.yaml"),
    ("starforge-awakens", "Starforge Awakens", "Epic E minor build, 128 BPM — origin story", "BYTEBEAT_NARRATED", "yaml", "my_song.yaml"),
    ("captains-log", "The Captain's Log", "Full narrated, 124 BPM — the journey so far", "BYTEBEAT_NARRATED", "yaml", "captains_log_song.yaml"),
    ("captains-log-short", "Captain's Log (Short)", "Short narrated mix, 124 BPM", "BYTEBEAT_NARRATED", "yaml", "captains_log_short.yaml"),

    # Bytebeat — instrumental (no voice, just music)
    ("acid-session", "Acid Session", "303 bass, supersaw stabs — inspired by Switch.Angel, 136 BPM", "BYTEBEAT", "yaml", "acid_session.yaml"),
    ("trance-og", "Trance OG", "The original — pluck arps to full supersaw, 138 BPM", "BYTEBEAT", "yaml", "trance_og.yaml"),
    ("trance-epic", "Trance Epic", "Huge pads, dual arps, acid peak, 138 BPM", "BYTEBEAT", "yaml", "trance_epic.yaml"),

    # ChucK — ambient / journey (real-time generative)
    ("space-synth", "Space Synth", "Organic synths + bowls + chippy arps, never repeats", "CHUCK_AMBIENT", "chuck", "space-synth.ck"),
    ("coding-ambient", "Coding Ambient", "Floating pads + euclidean pulses + sparse melody", "CHUCK_AMBIENT", "chuck", "coding-ambient.ck"),
    ("coding-flow", "Coding Flow", "Warm pads + gentle melodies, layers fade in slowly", "CHUCK_AMBIENT", "chuck", "coding-flow.ck"),
    ("singing-bowls", "Singing Bowls", "Tibetan brass bowls, tapped and swirled", "CHUCK_AMBIENT", "chuck", "singing-bowls.ck"),
    ("cathedral-drift", "Cathedral Drift", "Deep reverb pads, slow transformation", "CHUCK_AMBIENT", "chuck", "cathedral-drift.ck"),

    # ChucK — dark
    ("dark-space", "Dark Space", "80s laser show: massive pads, Vangelis vibes", "CHUCK_DARK", "chuck", "dark-space.ck"),
    ("dark-techno", "Dark Techno", "Tension-driven, sidechain pump, 6-min arc", "CHUCK_DARK", "chuck", "dark-techno.ck"),
    ("dark-ambient", "Dark Ambient", "Sinister drones, metallic resonance, dread", "CHUCK_DARK", "chuck", "dark-ambient.ck"),
    ("dark-industrial", "Dark Industrial", "Harsh, mechanical, acid bass, relentless", "CHUCK_DARK", "chuck", "dark-industrial.ck"),

    # ChucK — electronic
    ("gameboy-evolve", "Gameboy Evolve", "8-bit chiptune, real melodies, never repeats", "CHUCK_ELECTRONIC", "chuck", "gameboy-evolve.ck"),
    ("euro-rave", "Euro Rave", "Acid bass, four-on-the-floor, sidechain pump", "CHUCK_ELECTRONIC", "chuck", "euro-rave.ck"),

    # Bytebeat templates (generate on-the-fly)
    ("tpl-trance", "Trance", "Pluck arps, acid, supersaw peak, 136 BPM", "TEMPLATES", "template", "trance"),
    ("tpl-lofi", "Lo-Fi", "Jazzy chords, mellow plucks, light groove, 78 BPM", "TEMPLATES", "template", "lofi"),
    ("tpl-cinematic", "Cinematic", "Deep tension build, dramatic pads, 100 BPM", "TEMPLATES", "template", "cinematic"),
    ("tpl-ambient", "Ambient", "Vast drifting pads, no beats, pure space, 68 BPM", "TEMPLATES", "template", "ambient"),
    ("tpl-acid", "Acid House", "303 bass line, minimal drums, hypnotic, 132 BPM", "TEMPLATES", "template", "acid"),
    ("tpl-hiphop", "Hip Hop", "Boom-bap beat, bass heavy, voice forward, 88 BPM", "TEMPLATES", "template", "hiphop"),
    ("tpl-minimal", "Minimal Techno", "Hypnotic repetition, deep groove, 124 BPM", "TEMPLATES", "template", "minimal"),
    ("tpl-anthem", "Epic Anthem", "Uplifting supersaws, triumphant pads, 138 BPM", "TEMPLATES", "template", "anthem"),
]

# Category display config: (label, color_code, suffix)
_CAT_DISPLAY = {
    "BYTEBEAT_NARRATED": ("BYTEBEAT — NARRATED", "33", "rendered to WAV, pure Python"),
    "BYTEBEAT":          ("BYTEBEAT — INSTRUMENTAL", "33", "rendered to WAV, pure Python"),
    "CHUCK_AMBIENT":     ("CHUCK — AMBIENT / JOURNEY", "32", "real-time generative, requires ChucK"),
    "CHUCK_DARK":        ("CHUCK — DARK", "31", "real-time generative, requires ChucK"),
    "CHUCK_ELECTRONIC":  ("CHUCK — ELECTRONIC", "35", "real-time generative, requires ChucK"),
    "TEMPLATES":         ("BYTEBEAT — TEMPLATES", "34", "generated on-the-fly from genre blueprints"),
}


def _data_path(subdir: str, filename: str) -> str:
    """Get path to a bundled data file."""
    ref = resources.files("sonic_forge").joinpath(subdir).joinpath(filename)
    return str(ref)


def _check_chuck() -> bool:
    """Check if ChucK is installed. Auto-install via brew if missing on macOS."""
    if shutil.which("chuck"):
        return True
    # Auto-install on macOS
    if sys.platform == "darwin" and shutil.which("brew"):
        print("  ChucK not found — installing via brew...")
        try:
            subprocess.run(["brew", "install", "chuck"],
                           capture_output=True, timeout=120)
            return shutil.which("chuck") is not None
        except Exception:
            pass
    return False


def _get_user_songs() -> list[tuple]:
    """Scan ~/.sonic-forge/songs/ for user-installed .yaml and .ck files."""
    songs = []
    user_dir = USER_SONGS_DIR
    if not user_dir.exists():
        return songs

    for f in sorted(user_dir.iterdir()):
        if f.suffix == ".yaml":
            key = f.stem.replace("_", "-")
            songs.append((key, f.stem, f"User song — {f.name}", "USER", "user-yaml", str(f)))
        elif f.suffix == ".ck":
            key = f.stem.replace("_", "-")
            songs.append((key, f.stem, f"User ChucK track — {f.name}", "USER", "user-chuck", str(f)))
    return songs


def _all_songs() -> list[tuple]:
    """Built-in songs + user songs."""
    user = _get_user_songs()
    if user:
        return BUILTIN_SONGS + user
    return BUILTIN_SONGS


# ── Playback ────────────────────────────────────────────────────────────

def _play_yaml(filename: str, play: bool = True) -> None:
    """Render and play a bundled YAML song."""
    import tempfile
    from sonic_forge.songfile import render_yaml_song
    path = _data_path("tracks", filename)
    out = os.path.join(tempfile.gettempdir(), filename.replace(".yaml", ".wav"))
    render_yaml_song(path, output_path=out, play=play)


def _play_user_yaml(filepath: str, play: bool = True) -> None:
    """Render and play a user-installed YAML song."""
    import tempfile
    from sonic_forge.songfile import render_yaml_song
    out = os.path.join(tempfile.gettempdir(), Path(filepath).stem + ".wav")
    render_yaml_song(filepath, output_path=out, play=play)


def _play_chuck(filename: str, minutes: int = 60) -> None:
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


def _play_user_chuck(filepath: str, minutes: int = 60) -> None:
    """Play a user-installed ChucK track."""
    if not _check_chuck():
        print("\n  ChucK is not installed. Install: brew install chuck\n")
        return
    name = Path(filepath).name
    print(f"\n  Playing {name} ({minutes}m)... Ctrl-C to stop\n")
    try:
        subprocess.run(["chuck", f"{filepath}:{minutes}"])
    except KeyboardInterrupt:
        print("\n  Stopped.")


def _play_template(template_name: str, minutes: int = 3, play: bool = True) -> None:
    """Generate and play an instrumental template."""
    import tempfile
    import yaml
    from sonic_forge.songfile import render_yaml_song

    song_data = {
        "title": f"{template_name} session",
        "bpm": 130,
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
    """Play a song by its key or file path."""
    # If it's a file path, play it directly
    if key.endswith(".yaml") and Path(key).exists():
        print(f"\n  Playing {Path(key).name}\n")
        _play_user_yaml(key)
        return
    if key.endswith(".ck") and Path(key).exists():
        print(f"\n  Playing {Path(key).name}\n")
        _play_user_chuck(key, minutes=minutes if minutes is not None else 60)
        return

    for entry in _all_songs():
        if entry[0] == key:
            _, name, desc, cat, engine, filename = entry
            print(f"\n  {name}")
            print(f"  {desc}\n")
            if engine == "yaml":
                _play_yaml(filename)
            elif engine == "user-yaml":
                _play_user_yaml(filename)
            elif engine == "chuck":
                _play_chuck(filename, minutes=minutes if minutes is not None else 60)
            elif engine == "user-chuck":
                _play_user_chuck(filename, minutes=minutes if minutes is not None else 60)
            elif engine == "template":
                _play_template(filename, minutes=minutes if minutes is not None else 3)
            return
    print(f"\n  Unknown song: {key}")
    print(f"  Run 'sonic-forge' to see all available tracks.\n")


# ── Install ─────────────────────────────────────────────────────────────

def export_song(key: str, dest: str | None = None) -> None:
    """Export a built-in song's source file to the current directory."""
    import shutil as sh
    for entry in BUILTIN_SONGS:
        if entry[0] == key:
            _, name, desc, cat, engine, filename = entry
            if engine == "yaml":
                src = _data_path("tracks", filename)
            elif engine == "chuck":
                src = _data_path("chuck", filename)
            else:
                print(f"\n  Template songs can't be exported (they're generated on-the-fly).")
                print(f"  Run 'sonic-forge dsl' to see how to write your own.\n")
                return
            dest_path = Path(dest) if dest else Path.cwd() / filename
            sh.copy2(src, dest_path)
            print(f"\n  Exported: {filename} -> {dest_path}")
            print(f"  Edit it, then: sonic-forge render {dest_path.name} --play")
            print(f"  Save it:       sonic-forge install {dest_path.name}\n")
            return
    print(f"\n  Unknown song: {key}")
    print(f"  Run 'sonic-forge catalog' to see available tracks.\n")


def install_song(source: str) -> None:
    """Install a .yaml or .ck song file into ~/.sonic-forge/songs/."""
    import shutil as sh
    src = Path(source)
    if not src.exists():
        print(f"\n  File not found: {source}\n")
        return
    if src.suffix not in (".yaml", ".ck"):
        print(f"\n  Only .yaml and .ck files can be installed.\n")
        return

    dest_dir = _ensure_user_dir()
    dest = dest_dir / src.name
    sh.copy2(src, dest)
    key = src.stem.replace("_", "-")
    print(f"\n  Installed: {src.name} -> ~/.sonic-forge/songs/")
    print(f"  Play with: sonic-forge play {key}\n")


# ── Display ─────────────────────────────────────────────────────────────

def list_songs() -> None:
    """Print the full song catalog."""
    has_chuck = _check_chuck()
    all_songs = _all_songs()
    current_cat = None

    print()
    print("  \033[1;36m SONIC FORGE \033[0m")
    print("  \033[36m bytebeat music DSL + multi-engine TTS voice system\033[0m")
    print()
    print("  \033[35m♥\033[0m \033[1;35mInspired by Switch.Angel\033[0m \033[35m♥\033[0m")
    print("  \033[35mShe introduced us to Tidal Cycles and live coding music.\033[0m")
    print("  \033[35mThis whole project exists because of her.\033[0m")
    print("  \033[1;35mhttps://www.youtube.com/@Switch-Angel\033[0m  \033[2;35m— go subscribe!\033[0m")
    print()

    for i, (key, name, desc, cat, engine, filename) in enumerate(all_songs):
        if cat != current_cat:
            current_cat = cat

            if cat == "USER":
                label = "YOUR SONGS"
                color = "36"
                suffix = f"~/.sonic-forge/songs/"
            elif cat in _CAT_DISPLAY:
                label, color, suffix = _CAT_DISPLAY[cat]
                if "ChucK" in suffix and not has_chuck:
                    suffix += " [not installed — brew install chuck]"
            else:
                label, color, suffix = cat, "0", ""

            print(f"\n  \033[1;{color}m  {label}\033[0m  \033[2m{suffix}\033[0m")
            print(f"  {'─' * 72}")

        num = f"{i + 1:>2}"
        avail = ""
        if engine in ("chuck", "user-chuck") and not has_chuck:
            avail = " \033[2m[need chuck]\033[0m"
        print(f"  {num}) \033[1m{name:<24}\033[0m \033[2m{key:<22}\033[0m {desc}{avail}")

    print(f"\n  {'─' * 72}")
    print(f"  \033[36m{len(all_songs)} tracks available\033[0m")

    # Show user songs dir hint if empty
    user_songs = _get_user_songs()
    if not user_songs:
        print(f"  \033[2mAdd your own: sonic-forge install my_song.yaml\033[0m")
    print()


def interactive_menu() -> None:
    """Show the interactive launcher TUI."""
    all_songs = _all_songs()

    list_songs()

    print("  \033[1mPLAY:\033[0m")
    print("    sonic-forge play acid-session         Bytebeat acid, renders to WAV")
    print("    sonic-forge play dark-space           ChucK real-time, 1 hour default")
    print("    sonic-forge play tpl-lofi -m 10       Generate 10 min of lo-fi")
    print()
    print("  \033[1;33mMAKE YOUR OWN SONGS:\033[0m")
    print("    sonic-forge dsl                       Show the full song format reference")
    print()
    print("    \033[2mQuick start — create a file called my_song.yaml:\033[0m")
    print("    \033[36m    title: my first song\033[0m")
    print("    \033[36m    bpm: 130\033[0m")
    print("    \033[36m    sections:\033[0m")
    print("    \033[36m      - cycles: 8\033[0m")
    print("    \033[36m        layers:\033[0m")
    print("    \033[36m          - synth: acid\033[0m")
    print("    \033[36m            notes: c2 eb2 f2 ab2\033[0m")
    print("    \033[36m            fast: 16\033[0m")
    print("    \033[36m          - mini: \"bd*4\"\033[0m")
    print()
    print("    sonic-forge render my_song.yaml --play    Hear it instantly")
    print("    sonic-forge install my_song.yaml          Save to your collection")
    print()
    print("  \033[1;33mSHARE & IMPORT:\033[0m")
    print(f"    \033[2mYour songs live in:\033[0m  ~/.sonic-forge/songs/")
    print("    sonic-forge install friend_song.yaml   Import someone's song")
    print("    sonic-forge export acid-session         Copy a built-in to current dir")
    print("    \033[2mShare a .yaml file — anyone with sonic-forge can play it!\033[0m")
    print()
    print("  \033[1mOTHER:\033[0m")
    print("    sonic-forge speak \"text\" --voice daniel  TTS (use just the name!)")
    print("    sonic-forge speak \"text\" --fx helmet     Robot voice effects")
    print("    sonic-forge voices                       List all 54+ TTS voices")
    print()
    print("  \033[2mInspired by Switch.Angel — https://www.youtube.com/@Switch-Angel\033[0m")
    print("  \033[2mShe led us to Tidal Cycles and opened our eyes to generative music.\033[0m")
    print()

    # Interactive selection
    try:
        choice = input("  \033[1mPick a track (1-{}, name, or q): \033[0m".format(len(all_songs))).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not choice or choice.lower() == "q":
        return

    # Try as number
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(all_songs):
            key = all_songs[idx][0]
            print(f"\n  \033[2mCommand: sonic-forge play {key}\033[0m")
            play_song(key)
            return
    except ValueError:
        pass

    # Try as key name (exact or partial match)
    choice_lower = choice.lower().replace(" ", "-")
    for entry in all_songs:
        if entry[0] == choice_lower or choice_lower in entry[0]:
            print(f"\n  \033[2mCommand: sonic-forge play {entry[0]}\033[0m")
            play_song(entry[0])
            return

    print(f"\n  Unknown selection: {choice}")
    print(f"  Try a number (1-{len(all_songs)}) or a track name.\n")


# ── DSL Reference ───────────────────────────────────────────────────────

DSL_REFERENCE = """
  \033[1;36mSONIC FORGE — SONG FORMAT REFERENCE\033[0m

  \033[1mYAML SONG FORMAT\033[0m
  Songs are .yaml files. Sections play in order. Each section has layers.

    title: my song
    bpm: 130
    voice: Samantha              # TTS voice (optional — for narrated songs)
    engine: kokoro               # TTS engine: say, kokoro (optional)
    fx: helmet                   # Robot effect (optional)
    voice_lead: 2.0              # Seconds before section to start speaking
    music_volume: 0.8            # Music level 0.0-2.0 (default 1.0)
    voice_volume: 0.5            # Voice level 0.0-2.0 (default 1.0)

    sections:
      - say: "narration text"    # Optional voiceover for this section
        cycles: 8                # How many 4-beat loops
        layers:
          - synth: acid          # Pitched synth
            notes: c2 eb2 f2 ab2 # Space-separated notes
            fast: 16             # Speed multiplier (optional)
          - mini: "bd*4"         # Tidal mini-notation for drums

  \033[1mVOLUME CONTROL\033[0m
    In YAML:   music_volume: 0.8 / voice_volume: 0.5  (0.0 = silent, 1.0 = full, 2.0 = boosted)
    On CLI:    --music-vol 0.8 --voice-vol 0.5         (overrides YAML values)
    Tip: For narrated songs, try music_volume: 0.6-0.8 and voice_volume: 0.4-0.6
         so the voice sits clearly on top of the music.

  \033[1mSYNTHS\033[0m (bytebeat waveform generators)
    acid     303-style resonant bass — the classic acid sound
    saw      Supersaw, thick and wide — great for leads and stabs
    pluck    Plucked string, clean attack — arps and melodies
    pad      Soft sustained chord — backgrounds and atmosphere
    bass     Deep sub bass — low end foundation

  \033[1mDRUM SOUNDS\033[0m (used in mini-notation)
    bd       Kick drum             sn       Snare
    hh       Hi-hat (closed)       oh       Open hi-hat
    cp       Clap                  ~        Rest (silence)

  \033[1mMINI-NOTATION\033[0m (Tidal/Strudel-inspired)
    "bd*4"               4 kicks per cycle
    "~ hh ~ hh"          Off-beat hi-hats
    "[hh hh hh ~]*4"     Grouped pattern repeated
    "hh(5,8)"            Euclidean rhythm: 5 hits in 8 slots
    "cp(3,8)"            Euclidean: 3 claps in 8 slots

  \033[1mNOTES\033[0m
    Format: note + octave, e.g. c3, eb4, g2, bb1
    Sharps/flats: use b for flat (eb, bb, ab), # for sharp
    Range: 0-8 octaves (bass lives at 0-2, melody at 3-5)

  \033[1mROBOT FX\033[0m (voice effects — use with --fx)
    helmet     Muffled, low clarity — heavy droid/Vader vibe
    intercom   Radio crackle, medium clarity — cockpit comms
    droid      R2-D2 style, low clarity — bleepy and robotic
    ringmod    Metallic ring, medium clarity — alien transmission
    bitcrush   Lo-fi digital, harsh — retro computer voice
    vocoder    Synthetic harmonic, medium clarity — synth voice

  \033[1mTEMPLATES\033[0m
    Instead of writing sections by hand, apply a genre template:
      sonic-forge render song.yaml --template acid --play
    Templates: trance, lofi, cinematic, ambient, acid, hiphop, minimal, anthem
    Narrated mode (sparse music) activates when sections have "say:" fields.
    Instrumental mode (full music) activates when there's no narration.

  \033[1mSHARING\033[0m
    sonic-forge install my_song.yaml     Add to ~/.sonic-forge/songs/
    sonic-forge install friend_track.ck  Install a ChucK track too
    sonic-forge export acid-session      Copy a built-in to edit/remix

  \033[1mEXAMPLES\033[0m

    \033[2mInstrumental track:\033[0m
    sonic-forge play acid-session        Listen to a bytebeat acid track
    sonic-forge render my.yaml --play    Render and play your own song
    sonic-forge render my.yaml -o out.wav --template lofi   Apply lofi template

    \033[2mNarrated track (balanced voice + music):\033[0m
      title: mission briefing
      bpm: 110
      voice: daniel                # Just the name works (resolves to bm_daniel)
      engine: kokoro
      music_volume: 0.6            # Keep music low so voice is clear
      voice_volume: 0.5            # Gentle voice, not overpowering
      sections:
        - say: "Clear voice sitting on top of quiet music"
          cycles: 8
          layers:
            - synth: pad
              notes: c3 eb3 g3
            - mini: "bd*4"

    \033[2mOverride volumes from CLI (no YAML edits needed):\033[0m
    sonic-forge render song.yaml --voice-vol 0.5 --music-vol 0.8 --play

  \033[1mINSPIRATION\033[0m
    Sonic Forge was inspired by Switch.Angel and her Tidal Cycles live coding.
    https://www.youtube.com/@Switch-Angel
    She opened our eyes to generative computer music. Go subscribe.
"""


def show_dsl() -> None:
    """Print the DSL reference."""
    print(DSL_REFERENCE)
