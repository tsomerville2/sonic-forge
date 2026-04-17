"""sonic-forge CLI — bytebeat music + TTS voice system."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer


app = typer.Typer(
    name="sonic-forge",
    help="Sonic Forge — bytebeat music DSL + multi-engine TTS voice system.",
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context) -> None:
    """Sonic Forge — bytebeat music DSL + multi-engine TTS voice system.

    Run with no arguments for the interactive launcher.
    """
    if ctx.invoked_subcommand is None:
        from sonic_forge.launcher import interactive_menu
        interactive_menu()


@app.command("play")
def play_cmd(
    name: str = typer.Argument(..., help="Track name or file path (e.g. dark-space, song.mp3)."),
    minutes: Optional[int] = typer.Option(None, "--minutes", "-m", help="Duration in minutes (ChucK: default 60, templates: default 3)."),
    visual: Optional[str] = typer.Option(None, "--visual", help="Talking head: droid, human, alien. Add :pixel for pixel art (e.g. alien:pixel:nes)."),
) -> None:
    """Play a built-in track or audio file, with optional talking head.

    sonic-forge play dark-space                 ChucK, plays 1 hour, Ctrl-C to stop
    sonic-forge play dark-space -m 10           ChucK, 10 minutes
    sonic-forge play tpl-acid                   Generate 3 min of acid house
    sonic-forge play song.mp3                   Play an mp3/wav file
    sonic-forge play song.mp3 --visual droid    Replay with talking head animation
    sonic-forge play song.mp3 --visual alien:pixel:nes
    """
    import subprocess

    # If it's a file path, play it directly
    if os.path.isfile(name):
        if visual:
            _play_file_with_visual(name, visual)
        else:
            print(f"\n  Playing {name}...")
            subprocess.run(["afplay", name])
        return

    from sonic_forge.launcher import play_song
    play_song(name, minutes=minutes)


def _play_file_with_visual(filepath: str, visual: str) -> None:
    """Play an audio file with talking head animation — image or pixel/ASCII."""
    import subprocess
    from sonic_forge.image_heads import CHARACTERS_DIR

    parts = visual.split(":")
    char_name = parts[0] if parts else "droid"

    # Check if this is an image character
    if (CHARACTERS_DIR / char_name).is_dir():
        from sonic_forge.image_heads import animate_image_character
        print(f"\n  Playing with {char_name} visual...")
        animate_image_character(filepath, char_name)
        return

    # Fallback to pixel/ASCII talking heads (need WAV)
    wav_path = filepath
    cleanup_wav = False

    if filepath.lower().endswith(".mp3"):
        wav_path = filepath.rsplit(".", 1)[0] + ".wav"
        if not os.path.exists(wav_path):
            try:
                subprocess.run(
                    ["afconvert", filepath, wav_path, "-d", "LEI16", "-f", "WAVE"],
                    check=True, capture_output=True,
                )
                cleanup_wav = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("  Could not convert to WAV — playing audio only...")
                subprocess.run(["afplay", filepath])
                return

    style = parts[1] if len(parts) > 1 else "ascii"
    palette = parts[2] if len(parts) > 2 else "nes"

    try:
        from sonic_forge.talking_heads import animate_character
        print(f"\n  Playing with {char_name} visual...")
        animate_character(wav_path, char_name=char_name, style=style, palette_name=palette)
    except Exception:
        subprocess.run(["afplay", wav_path])
    finally:
        if cleanup_wav and os.path.exists(wav_path):
            os.remove(wav_path)


@app.command("stop")
def stop_cmd() -> None:
    """Stop all playing audio (kills afplay and chuck processes)."""
    import signal
    import subprocess
    killed = []
    for proc in ("afplay", "chuck"):
        result = subprocess.run(["pkill", "-9", proc], capture_output=True)
        if result.returncode == 0:
            killed.append(proc)
    if killed:
        print(f"\n  Stopped: {', '.join(killed)}\n")
    else:
        print("\n  Nothing playing.\n")


@app.command("catalog")
def catalog_cmd() -> None:
    """List all tracks — built-in + your installed songs."""
    from sonic_forge.launcher import list_songs
    list_songs()


@app.command("install")
def install_cmd(
    source: str = typer.Argument(..., help="Path to a .yaml or .ck song file."),
) -> None:
    """Install a song into your collection (~/.sonic-forge/songs/).

    sonic-forge install my_song.yaml
    sonic-forge install dark_forest.ck
    """
    from sonic_forge.launcher import install_song
    install_song(source)


@app.command("export")
def export_cmd(
    name: str = typer.Argument(..., help="Track name to export (e.g. acid-session, dark-space)."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output path."),
) -> None:
    """Export a built-in song file to the current directory.

    Grab any song's source to learn from, remix, or share.

    sonic-forge export acid-session        Get the YAML, edit it, make it yours
    sonic-forge export dark-space          Get the ChucK source
    sonic-forge export trance-og -o remix.yaml
    """
    from sonic_forge.launcher import export_song
    export_song(name, dest=output)


@app.command("dsl")
def dsl_cmd() -> None:
    """Show the song format reference — synths, notes, mini-notation.

    Everything you need to write your own songs or teach an LLM to compose.
    """
    from sonic_forge.launcher import show_dsl
    show_dsl()


@app.command("render")
def render_cmd(
    song: str = typer.Argument(..., help="YAML song file to render."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output WAV path."),
    play: bool = typer.Option(False, "--play", help="Play after rendering."),
    voice: Optional[str] = typer.Option(None, "--voice", help="TTS voice name (Samantha, af_heart, Zarvox...)."),
    engine: Optional[str] = typer.Option(None, "--engine", help="TTS engine: say (macOS), kokoro (Kokoro-82M)."),
    fx: Optional[str] = typer.Option(None, "--fx", help="Robot FX: helmet (muffled, droid), intercom (radio, medium clarity), droid (R2-style), ringmod (metallic), bitcrush (lo-fi, harsh)."),
    template: Optional[str] = typer.Option(None, "--template", help="Apply genre template."),
    lead: Optional[float] = typer.Option(None, "--lead", help="Voiceover lead time (seconds)."),
    rate: Optional[int] = typer.Option(None, "--rate", help="Speech rate (WPM)."),
    voice_stem: Optional[str] = typer.Option(None, "--voice-stem", help="Save voice-only WAV (for lip sync)."),
    music_vol: Optional[float] = typer.Option(None, "--music-vol", help="Music volume (0.0-2.0, default 1.0)."),
    voice_vol: Optional[float] = typer.Option(None, "--voice-vol", help="Voice volume (0.0-2.0, default 1.0)."),
) -> None:
    """Render a YAML song to WAV.

    sonic-forge render song.yaml --play
    sonic-forge render song.yaml --voice af_heart --engine kokoro --fx helmet --play
    sonic-forge render song.yaml --voice-vol 0.5 --music-vol 1.5 --play
    sonic-forge render song.yaml --voice Daniel --template lofi --play
    """
    from sonic_forge.songfile import render_yaml_song
    render_yaml_song(
        song, output_path=output, play=play,
        voice_override=voice, template_name=template,
        lead_override=lead, speech_rate=rate,
        engine=engine, fx=fx, voice_stem=voice_stem,
        music_vol=music_vol, voice_vol=voice_vol,
    )


@app.command("templates")
def templates_cmd() -> None:
    """List available genre templates."""
    from sonic_forge.templates import list_templates
    list_templates()


@app.command("robotize")
def robotize_cmd(
    input_wav: str = typer.Argument(..., help="WAV file to process."),
    effects: Optional[list[str]] = typer.Option(None, "--fx", help="Effects to apply (ringmod, bitcrush, vocoder, droid, helmet, intercom)."),
    output_dir: Optional[str] = typer.Option(None, "-o", "--output-dir", help="Output directory."),
) -> None:
    """Apply robot/droid effects to a WAV file.

    sonic-forge robotize voice.wav
    sonic-forge robotize voice.wav --fx helmet --fx droid
    """
    from sonic_forge.robotize import robotize_file
    robotize_file(input_wav, output_dir=output_dir, effects=effects)


@app.command("speak")
def speak_cmd(
    topic: Optional[str] = typer.Argument(None, help="Topic for AI to write about, or literal text with --text."),
    text: Optional[str] = typer.Option(None, "--text", "-T", help="Speak literal text (no AI). Overrides topic."),
    voice: Optional[str] = typer.Option(None, "--voice", "-v", help="Voice name: short (onyx, heart, bella), full (af_heart), edge (te-IN-MohanNeural), or gender (male/female with --lang)."),
    engine: Optional[str] = typer.Option(None, "--engine", "-e", help="TTS engine: say, kokoro, edge."),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Language: telugu, hindi, french, spanish, etc. Auto-picks best engine."),
    fx: Optional[str] = typer.Option(None, "--fx", help="Robot FX: helmet, intercom, droid, ringmod, bitcrush."),
    rate: Optional[int] = typer.Option(None, "--rate", help="Speech rate in WPM (macOS say)."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save WAV to this path."),
    no_play: bool = typer.Option(False, "--no-play", help="Generate only, don't play."),
    visual: Optional[str] = typer.Option(None, "--visual", help="Talking head: droid, human, alien. Add :pixel for pixel art (e.g. alien:pixel:nes)."),
    music: bool = typer.Option(False, "--music", help="Add bytebeat music backing (briefing mode)."),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="Music template when --music is used: cinematic, ambient, lofi, trance, acid, hiphop, minimal, anthem."),
) -> None:
    """Speak text aloud — plain TTS, with optional music, FX, or talking heads.

    Quick start (macOS say, default voice):
      sonic-forge speak --text "Hello world"

    Pick a voice by short name (Kokoro-82M, local, high quality):
      sonic-forge speak --text "Hello" --voice onyx        # deep male
      sonic-forge speak --text "Hello" --voice heart       # warm female
      sonic-forge speak --text "Hello" --voice bella       # friendly female
      sonic-forge speak --text "Hello" --voice george      # British male
      sonic-forge speak --text "Hello" --voice emma        # British female

    Non-English languages (auto-picks best engine — Kokoro if available, Edge otherwise):
      sonic-forge speak --text "Bonjour le monde" --lang french
      sonic-forge speak --text "Hola mundo" --lang spanish
      sonic-forge speak --text "नमस्ते दुनिया" --lang hindi
      sonic-forge speak --text "మా CICD పైప్‌లైన్" --lang telugu     # Edge (Kokoro can't)
      sonic-forge speak --text "வணக்கம்" --lang tamil                # Edge
      sonic-forge speak --text "こんにちは" --lang japanese
      sonic-forge speak --text "مرحبا" --lang arabic                 # Edge

    Pick gender within a language:
      sonic-forge speak --text "Hello" --lang english --voice female
      sonic-forge speak --text "తెలుగు" --lang telugu --voice female

    Save to WAV (for video narration):
      sonic-forge speak --text "Welcome" --voice onyx -o intro.wav --no-play
      sonic-forge speak --text "హలో" --lang telugu -o hello-te.wav --no-play

    Robot/comms effects:
      sonic-forge speak --text "Captain on deck" --fx helmet
      sonic-forge speak --text "Copy that" --voice fenrir --fx intercom
      sonic-forge speak --text "Systems online" --fx droid

    AI-written briefing (needs Claude, Gemini, or Ollama):
      sonic-forge speak "boost crew morale"
      sonic-forge speak "mission status" --voice onyx --fx helmet

    With bytebeat music backing:
      sonic-forge speak "status update" --music
      sonic-forge speak "mission log" --music --template ambient
      sonic-forge speak --text "All systems go" --music --template trance

    Talking head animation:
      sonic-forge speak --text "Greetings" --visual alien:pixel:nes --fx helmet
      sonic-forge speak --text "Hello crew" --voice michael --visual droid

    See all voices:
      sonic-forge voices                         # everything
      sonic-forge voices --engine kokoro         # 27 English voices
      sonic-forge voices --engine edge           # 20 languages (cloud, free)
      sonic-forge voices --lang telugu           # Telugu-capable voices only
    """
    if music:
        # Music mode — render speech over bytebeat backing track
        _speak_with_music(
            topic=topic, text=text, voice=voice or "Daniel",
            engine=engine, fx=fx, template=template or "cinematic",
            output=output, visual=visual,
        )
        return

    # Plain TTS mode
    actual_text = text or topic
    if not actual_text:
        print("\n  Provide text or a topic. Run 'sonic-forge speak --help' for usage.\n")
        raise typer.Exit(1)

    if not text and topic:
        # Topic mode — use LLM to write speech
        from sonic_forge.llm import llm_json_request, setup_hint
        speech_prompt = """You write short spoken scripts. Respond with JSON:
{"text": "the full text to speak aloud"}
RULES: Max 50 words. Written for the ear. Plain English. Punchy and direct."""
        print("\n  Writing script...")
        data = llm_json_request(speech_prompt, topic)
        if data:
            actual_text = data.get("text", topic)
        else:
            print(setup_hint())
            actual_text = topic

    from sonic_forge.tts import speak
    if visual:
        # Generate WAV first, then play with talking head
        import tempfile
        wav_path = output or tempfile.mktemp(suffix=".wav")
        speak(actual_text, engine=engine, voice=voice, lang=lang, rate=rate, fx=fx,
              output_path=wav_path, play=False)
        _play_file_with_visual(wav_path, visual)
        if not output:
            import os
            os.remove(wav_path)
    else:
        speak(actual_text, engine=engine, voice=voice, lang=lang, rate=rate, fx=fx,
              output_path=output, play=not no_play)


def _speak_with_music(topic, text, voice, engine, fx, template, output, visual):
    """Speech over bytebeat music — the old 'brief' functionality."""
    import tempfile

    sections = None
    title = "Briefing"

    if not topic and not text:
        print("\n  Provide a topic or use --text. Run 'sonic-forge speak --help' for usage.\n")
        raise typer.Exit(1)

    if text:
        sections = [s.strip() for s in text.split(".") if s.strip()]
        title = sections[0][:40] if sections else "Briefing"
    else:
        from sonic_forge.llm import llm_json_request, setup_hint
        brief_prompt = """You write short spoken briefings for a starship audio system. Each section plays over music so it MUST be brief.

Respond with JSON only:
{"title": "short title", "sections": ["Section one.", "Section two.", "Section three.", "Section four."]}

STRICT RULES:
- MAXIMUM 15 words per section. This is non-negotiable. Count your words.
- 4-6 sections total.
- Written for the EAR. No URLs, no code, no punctuation tricks.
- Plain English. Say "pie pie eye" not "PyPI". Spell out numbers.
- Punchy and direct. Like a news anchor, not an essayist."""

        print("\n  Writing briefing script...")
        data = llm_json_request(brief_prompt, topic)

        if data:
            title = data.get("title", "Briefing")
            sections = data.get("sections", [])
            if isinstance(sections, str):
                sections = [s.strip() for s in sections.split(". ") if s.strip()]
        else:
            print(setup_hint())
            print("  Using your text as-is (no AI rewrite).\n")
            sections = [s.strip() for s in topic.split(".") if s.strip()]
            if not sections:
                sections = [topic]
            title = sections[0][:40]

    if not sections:
        print("\n  No content. Provide --text or set up an AI provider.\n")
        raise typer.Exit(1)

    print(f"\n  {title}")
    for i, sec in enumerate(sections, 1):
        print(f"    {i}. {sec}")

    # Build YAML with cycle counts sized to speech length
    safe_title = title.replace('"', '\\"')
    yaml_lines = [f'title: "{safe_title}"', f"voice: {voice}",
                  "voice_lead: 0.5", "", "sections:"]
    for sec_text in sections:
        words = len(sec_text.split())
        speech_secs = (words / 150) * 60 + 1.5
        cycles = max(2, round(speech_secs / 2.4 + 0.5))
        safe_text = sec_text.replace('"', '\\"')
        yaml_lines.append(f'  - say: "{safe_text}"')
        yaml_lines.append(f"    cycles: {cycles}")
    yaml_content = "\n".join(yaml_lines) + "\n"

    out_path = output or tempfile.mktemp(suffix=".wav", prefix="speak_")
    yaml_path = out_path.replace(".wav", ".yaml")

    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    print("\n  Rendering...")

    from sonic_forge.songfile import render_yaml_song

    voice_stem_path = out_path.replace(".wav", "_voice.wav") if visual else None
    render_yaml_song(
        yaml_path, output_path=out_path, play=not visual,
        template_name=template,
        voice_override=voice, engine=engine, fx=fx,
        voice_stem=voice_stem_path,
    )

    if visual and os.path.exists(out_path):
        _play_file_with_visual(out_path, visual)

    if not output:
        for f in (yaml_path, out_path):
            if os.path.exists(f):
                os.remove(f)
        if voice_stem_path and os.path.exists(voice_stem_path):
            os.remove(voice_stem_path)
    else:
        print(f"\n  Saved: {out_path}\n")


@app.command("voices")
def voices_cmd(
    engine: Optional[str] = typer.Option(None, "--engine", "-e", help="Filter by engine: say, kokoro, edge."),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Filter by language (telugu, hindi, french, en, de, etc.)."),
) -> None:
    """List available TTS voices by engine and/or language.

    All voices (3 engines):
      sonic-forge voices

    By engine:
      sonic-forge voices --engine say       # 184 macOS voices (offline, basic)
      sonic-forge voices --engine kokoro    # 27 English voices (offline, high quality)
      sonic-forge voices --engine edge      # 20 languages (cloud, free, great quality)

    By language:
      sonic-forge voices --lang telugu      # shows which engines have Telugu
      sonic-forge voices --lang hindi       # Kokoro + Edge both available
      sonic-forge voices --lang en          # English voices across engines

    Kokoro covers: English (US+UK), Spanish, French, Hindi, Italian,
                   Japanese, Portuguese, Chinese.
    Edge adds: Telugu, Tamil, Kannada, Malayalam, Bengali, Marathi,
               Gujarati, Korean, German, Arabic, Russian, and more.
    """
    show_say = engine is None or engine == "say"
    show_kokoro = engine is None or engine == "kokoro"
    show_edge = engine is None or engine == "edge"

    if show_say:
        _list_say_voices(lang)
    if show_kokoro:
        _list_kokoro_voices(lang)
    if show_edge:
        _list_edge_voices(lang)


def _list_say_voices(lang_filter=None):
    """List macOS say voices."""
    import subprocess
    result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    if result.returncode != 0:
        print("  macOS say not available.")
        return

    lines = result.stdout.strip().splitlines()
    voices = []
    for line in lines:
        # Format: "Name                lang_REGION  # sample text"
        parts = line.split("#", 1)
        name_lang = parts[0].strip()
        # Split on multiple spaces to separate name from lang code
        chunks = name_lang.split()
        if len(chunks) >= 2:
            lang_code = chunks[-1]
            name = " ".join(chunks[:-1])
            lang_short = lang_code.split("_")[0]
            if lang_filter and lang_short != lang_filter:
                continue
            voices.append((name, lang_code))

    print(f"\n  macOS say — {len(voices)} voices")
    print(f"  {'Voice':<22} {'Language':<10} {'Usage'}")
    print(f"  {'─' * 22} {'─' * 10} {'─' * 40}")
    for name, lang_code in voices:
        print(f"  {name:<22} {lang_code:<10} --engine say --voice \"{name}\"")
    print()


# Kokoro voice catalog — all 54 voices
_KOKORO_VOICES = {
    "American English — Female": [
        ("af_alloy", "Alloy"), ("af_aoede", "Aoede"), ("af_bella", "Bella"),
        ("af_heart", "Heart"), ("af_jessica", "Jessica"), ("af_kore", "Kore"),
        ("af_nicole", "Nicole"), ("af_nova", "Nova"), ("af_river", "River"),
        ("af_sarah", "Sarah"), ("af_sky", "Sky"),
    ],
    "American English — Male": [
        ("am_adam", "Adam"), ("am_echo", "Echo"), ("am_eric", "Eric"),
        ("am_fenrir", "Fenrir"), ("am_liam", "Liam"), ("am_michael", "Michael"),
        ("am_onyx", "Onyx"), ("am_puck", "Puck"), ("am_santa", "Santa"),
    ],
    "British English — Female": [
        ("bf_alice", "Alice"), ("bf_emma", "Emma"),
        ("bf_isabella", "Isabella"), ("bf_lily", "Lily"),
    ],
    "British English — Male": [
        ("bm_daniel", "Daniel"), ("bm_fable", "Fable"),
        ("bm_george", "George"), ("bm_lewis", "Lewis"),
    ],
    "Spanish": [
        ("ef_dora", "Dora"), ("em_alex", "Alex"), ("em_santa", "Santa"),
    ],
    "French": [("ff_siwis", "Siwis")],
    "Hindi": [
        ("hf_alpha", "Alpha"), ("hf_beta", "Beta"),
        ("hm_omega", "Omega"), ("hm_psi", "Psi"),
    ],
    "Italian": [("if_sara", "Sara"), ("im_nicola", "Nicola")],
    "Japanese": [
        ("jf_alpha", "Alpha"), ("jf_gongitsune", "Gongitsune"),
        ("jf_nezumi", "Nezumi"), ("jf_tebukuro", "Tebukuro"),
        ("jm_kumo", "Kumo"),
    ],
    "Portuguese": [
        ("pf_dora", "Dora"), ("pm_alex", "Alex"), ("pm_santa", "Santa"),
    ],
    "Chinese": [
        ("zf_xiaobei", "Xiaobei"), ("zf_xiaoni", "Xiaoni"),
        ("zf_xiaoxiao", "Xiaoxiao"), ("zf_xiaoyi", "Xiaoyi"),
        ("zm_yunjian", "Yunjian"), ("zm_yunxi", "Yunxi"),
        ("zm_yunxia", "Yunxia"), ("zm_yunyang", "Yunyang"),
    ],
}

_KOKORO_LANG_MAP = {
    "en": ["American English — Female", "American English — Male",
           "British English — Female", "British English — Male"],
    "es": ["Spanish"], "fr": ["French"], "hi": ["Hindi"],
    "it": ["Italian"], "ja": ["Japanese"], "pt": ["Portuguese"],
    "zh": ["Chinese"],
}


def _list_kokoro_voices(lang_filter=None):
    """List Kokoro-82M voices."""
    # Check if kokoro is installed
    try:
        import kokoro_onnx  # noqa: F401
        available = True
    except ImportError:
        available = False

    total = sum(len(v) for v in _KOKORO_VOICES.values())
    status = "" if available else " [not installed — pip install 'sonic-forge[kokoro]']"
    print(f"\n  Kokoro-82M — {total} voices{status}")

    groups = _KOKORO_VOICES
    if lang_filter:
        group_names = _KOKORO_LANG_MAP.get(lang_filter, [])
        if not group_names:
            print(f"  No Kokoro voices for language '{lang_filter}'")
            print(f"  Available: {', '.join(_KOKORO_LANG_MAP.keys())}")
            return
        groups = {k: v for k, v in groups.items() if k in group_names}

    for group_name, voices in groups.items():
        print(f"\n  {group_name}:")
        for voice_id, display_name in voices:
            print(f"    {voice_id:<18} {display_name:<14} --engine kokoro --voice {voice_id}")
    print()


def _list_edge_voices(lang_filter=None):
    """List Edge-TTS languages (simplified — shows --lang + male/female pattern)."""
    import shutil
    from sonic_forge.tts import _EDGE_LANGUAGES

    available = shutil.which("edge-tts") is not None
    status = "" if available else " [not installed — run: pipx install edge-tts]"
    print(f"\n  Edge-TTS — {len(_EDGE_LANGUAGES)} languages (Microsoft Neural voices){status}")

    # Normalize lang filter: accept both "telugu" and "te" style
    if lang_filter:
        lf = lang_filter.lower()
        # Try exact language name first
        matches = {k: v for k, v in _EDGE_LANGUAGES.items() if k == lf}
        # Then try locale prefix match (e.g. "te" matches "te-IN")
        if not matches:
            matches = {k: v for k, v in _EDGE_LANGUAGES.items() if v[0].lower().startswith(lf)}
        if not matches:
            print(f"  No Edge voice for language '{lang_filter}'")
            print(f"  Try: {', '.join(list(_EDGE_LANGUAGES.keys())[:8])}...")
            return
        langs = matches
    else:
        langs = _EDGE_LANGUAGES

    print(f"  {'Language':<14} {'Locale':<8} {'Usage'}")
    print(f"  {'─' * 14} {'─' * 8} {'─' * 50}")
    for name, (locale, male, female) in langs.items():
        print(f"  {name:<14} {locale:<8} --lang {name}  (male default, or --voice female)")
    print()
    if not lang_filter:
        print("  Tip: 'sonic-forge speak --text \"hello\" --lang telugu' picks a male voice by default.")
        print("       Add --voice female to switch, or --voice <full-edge-id> for a specific voice.\n")


@app.command("testmodel")
def testmodel_cmd(
    prompt: Optional[str] = typer.Argument(None, help="Prompt to send to the model."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Ollama model name (e.g. granite4:3b, qwen3:4b)."),
) -> None:
    """Test an Ollama model — see raw output and timing.

    sonic-forge testmodel --model granite4:3b "brief my crew"
    sonic-forge testmodel "what is bytebeat?"
    sonic-forge testmodel                          # pick a model interactively
    """
    import json
    import re
    import time
    import urllib.request

    ollama_base = os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434")

    # Check Ollama is running
    try:
        with urllib.request.urlopen(f"{ollama_base}/api/tags", timeout=2) as resp:
            tags = json.loads(resp.read())
        models = [m["name"] for m in tags.get("models", [])]
    except Exception:
        print("\n  Ollama not running. Start it with: ollama serve\n")
        raise typer.Exit(1)

    if not models:
        print("\n  No models installed. Try: ollama pull granite4:3b\n")
        raise typer.Exit(1)

    # Pick model
    if not model:
        print(f"\n  Available models ({len(models)}):\n")
        for i, m in enumerate(models, 1):
            size = tags["models"][i - 1].get("size", 0)
            size_gb = size / 1e9 if size else 0
            print(f"    {i:>2}. {m:<30} {size_gb:.1f} GB")
        print()
        choice = input("  Pick a model (number or name): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                model = models[idx]
            else:
                print("  Invalid choice.")
                raise typer.Exit(1)
        else:
            model = choice

    if not prompt:
        prompt = input("  Prompt: ").strip()
        if not prompt:
            print("  No prompt given.")
            raise typer.Exit(1)

    print(f"\n  Model:  {model}")
    print(f"  Prompt: {prompt}\n")

    # Send to Ollama
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{ollama_base}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    wall_start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  Error: {e}\n")
        raise typer.Exit(1)
    wall_elapsed = time.time() - wall_start

    # Extract response text
    content = data.get("message", {}).get("content", "")
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    # Extract Ollama timing (nanoseconds → seconds)
    load_ns = data.get("load_duration", 0)
    prompt_ns = data.get("prompt_eval_duration", 0)
    gen_ns = data.get("eval_duration", 0)
    total_ns = data.get("total_duration", 0)
    tokens = data.get("eval_count", 0)

    load_s = load_ns / 1e9
    prompt_s = prompt_ns / 1e9
    gen_s = gen_ns / 1e9
    total_s = total_ns / 1e9
    tok_per_s = tokens / gen_s if gen_s > 0 else 0

    # Print result
    print("  ─── response ───\n")
    for line in content.splitlines():
        print(f"  {line}")

    print(f"\n  ─── timing ───\n")
    print(f"  Model load:   {load_s:>6.2f}s")
    print(f"  Prompt eval:  {prompt_s:>6.2f}s")
    print(f"  Generation:   {gen_s:>6.2f}s  ({tokens} tokens, {tok_per_s:.1f} tok/s)")
    print(f"  Total:        {total_s:>6.2f}s  (wall: {wall_elapsed:.2f}s)")
    print()


@app.command("brief", hidden=True)
def brief_cmd(
    topic: Optional[str] = typer.Argument(None, help="Topic for AI briefing."),
    text: Optional[str] = typer.Option(None, "--text", "-T", help="Literal text to speak."),
    template: Optional[str] = typer.Option("cinematic", "--template", "-t", help="Music template."),
    voice: Optional[str] = typer.Option("Daniel", "--voice", "-v", help="TTS voice name."),
    engine: Optional[str] = typer.Option(None, "--engine", "-e", help="TTS engine: say, kokoro."),
    fx: Optional[str] = typer.Option(None, "--fx", help="Robot FX."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save WAV."),
    visual: Optional[str] = typer.Option(None, "--visual", help="Talking head."),
) -> None:
    """[Moved to 'speak --music'] Audio briefing with music backing."""
    print("  Note: 'brief' is now 'speak --music'. Redirecting...\n")
    _speak_with_music(
        topic=topic, text=text, voice=voice or "Daniel",
        engine=engine, fx=fx, template=template or "cinematic",
        output=output, visual=visual,
    )


@app.command("sing")
def sing_cmd(
    topic: Optional[str] = typer.Argument(None, help="What the song is about (AI writes lyrics)."),
    lyrics: Optional[str] = typer.Option(None, "--lyrics", "-l", help="Lyrics text or path to .txt file (skip AI)."),
    style: str = typer.Option("rock", "--style", "-s", help="Music style: rock, pop, bluegrass, folk, hiphop, country, jazz, metal, acappella, indie, electronic, ambient."),
    voice: str = typer.Option("male", "--voice", "-v", help="Vocal gender: male or female."),
    duration: Optional[float] = typer.Option(None, "--duration", "-d", help="Song duration in seconds (auto-sized from lyrics if omitted)."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output mp3 path."),
    batch: int = typer.Option(1, "--batch", "-b", help="Number of takes to generate (pick your favorite)."),
    no_play: bool = typer.Option(False, "--no-play", help="Don't auto-play after generating."),
    acappella: bool = typer.Option(False, "--acappella", help="Vocals only, no instruments."),
    instrumental: bool = typer.Option(False, "--instrumental", help="Instruments only, no vocals."),
    visual: Optional[str] = typer.Option(None, "--visual", help="Talking head: droid, human, alien. Add :pixel for pixel art (e.g. alien:pixel:nes)."),
) -> None:
    """Generate a song with real singing vocals (ACE-Step AI).

    Three modes — vocals + instruments, vocals only, or instruments only:
      sonic-forge sing "space crew morale"                    # full song
      sonic-forge sing "space crew morale" --acappella        # voice only
      sonic-forge sing "epic battle theme" --instrumental     # music only

    From a topic (AI writes lyrics):
      sonic-forge sing "space crew morale booster"
      sonic-forge sing "watching cranes move" --style bluegrass
      sonic-forge sing "love song" --style pop --voice female --batch 4

    With talking head animation:
      sonic-forge sing "alien contact" --visual alien:pixel:nes
      sonic-forge sing "robot uprising" --visual droid --acappella

    From your own lyrics:
      sonic-forge sing --lyrics "verse one here. chorus here."
      sonic-forge sing --lyrics my_song.txt --style folk
      sonic-forge sing --lyrics cranes.txt --style bluegrass -o cranes.mp3

    First run downloads ~4GB of models (one-time only).
    """
    from sonic_forge.sing import sing as do_sing
    do_sing(
        topic=topic, lyrics=lyrics, style=style, voice=voice,
        duration=duration, output=output, batch=batch, no_play=no_play,
        acappella=acappella, instrumental=instrumental, visual=visual,
    )


@app.command("character")
def character_cmd(
    name: Optional[str] = typer.Argument(None, help="Character name (e.g. aliengirl, captain, robot)."),
    spritesheet: Optional[str] = typer.Argument(None, help="Path to spritesheet image (JPG or PNG)."),
    grid: str = typer.Option("3x3", "--grid", "-g", help="Grid layout as ROWSxCOLS (e.g. 3x3, 3x5, 5x5)."),
    remove: bool = typer.Option(False, "--remove", help="Remove a character."),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all installed characters."),
    width: int = typer.Option(60, "--width", "-w", help="Preview width in columns."),
) -> None:
    """Add, list, or remove image characters for talking head animation.

    Add a new character from a 3x3 spritesheet:
      sonic-forge character aliengirl ~/Downloads/spritesheet.jpg
      sonic-forge character captain /tmp/captain-sheet.png

    The spritesheet should be a 3x3 grid:
      Row 1: mouth closed  — eyes open, closed, variant
      Row 2: mouth open    — eyes open, closed, variant
      Row 3: mouth wide    — eyes open, closed, variant

    List installed characters:
      sonic-forge character --list

    Remove a character:
      sonic-forge character aliengirl --remove

    Preview a character:
      sonic-forge character aliengirl

    If the character already exists, it will be replaced.
    """
    import shutil
    from sonic_forge.image_heads import CHARACTERS_DIR, list_characters

    if list_all or (name is None and not remove):
        chars = list_characters()
        if not chars:
            print("\n  No image characters installed.")
            print(f"  Add one: sonic-forge character <name> <spritesheet.jpg>\n")
        else:
            print(f"\n  Installed characters ({len(chars)}):\n")
            for c in sorted(chars):
                char_dir = CHARACTERS_DIR / c
                sprites = list(char_dir.glob("*sprite*"))
                src = sprites[0].name if sprites else "individual frames"
                print(f"    {c:<20} ({src})")
            print(f"\n  Use with: sonic-forge play song.mp3 --visual <name>\n")
        return

    if not name:
        print("\n  Provide a character name. Run 'sonic-forge character --help' for usage.\n")
        raise typer.Exit(1)

    char_dir = CHARACTERS_DIR / name

    if remove:
        if char_dir.exists():
            shutil.rmtree(char_dir)
            print(f"\n  Removed character '{name}'.\n")
        else:
            print(f"\n  Character '{name}' not found.\n")
        return

    if spritesheet:
        # Add/replace character
        src = Path(spritesheet).expanduser().resolve()
        if not src.exists():
            print(f"\n  File not found: {spritesheet}\n")
            raise typer.Exit(1)

        # If source is inside the char dir, copy it out first
        import tempfile
        tmp_copy = None
        try:
            if char_dir.exists() and str(src).startswith(str(char_dir)):
                tmp_copy = tempfile.mktemp(suffix=src.suffix)
                shutil.copy2(str(src), tmp_copy)
                src = Path(tmp_copy)

            # Clear old character if exists
            if char_dir.exists():
                shutil.rmtree(char_dir)
                print(f"  Replacing existing character '{name}'...")

            char_dir.mkdir(parents=True, exist_ok=True)

            # Copy spritesheet
            dest = char_dir / f"spritesheet{src.suffix}"
            shutil.copy2(str(src), str(dest))
        finally:
            if tmp_copy and os.path.exists(tmp_copy):
                os.remove(tmp_copy)

        # Parse grid
        grid_parts = grid.lower().split("x")
        if len(grid_parts) != 2 or not grid_parts[0].isdigit() or not grid_parts[1].isdigit():
            print(f"\n  Invalid grid format: {grid}. Use ROWSxCOLS like 3x3 or 3x5.\n")
            raise typer.Exit(1)
        grid_rows, grid_cols = int(grid_parts[0]), int(grid_parts[1])

        # Verify it slices correctly
        from sonic_forge.spritesheet import slice_spritesheet, save_grid_info
        try:
            frames = slice_spritesheet(str(dest), rows=grid_rows, cols=grid_cols)
            save_grid_info(str(char_dir), grid_rows, grid_cols)
            print(f"\n  Character '{name}' installed — {len(frames)} frames ({grid_rows}x{grid_cols} grid) from {src.name}")
            print(f"  Location: {char_dir}")
            print(f"\n  Use with: sonic-forge play song.mp3 --visual {name}")
            print(f"            sonic-forge speak --text 'hello' --visual {name}\n")
        except Exception as e:
            shutil.rmtree(char_dir)
            print(f"\n  Failed to slice spritesheet: {e}")
            print(f"  Expected a {grid_rows}x{grid_cols} grid image (JPG or PNG).\n")
            raise typer.Exit(1)
        return

    # No spritesheet arg — preview if character exists
    if char_dir.exists():
        from sonic_forge.spritesheet import load_character_frames
        frames = load_character_frames(str(char_dir))
        if not frames:
            print(f"\n  Character '{name}' exists but has no valid frames.\n")
            raise typer.Exit(1)

        # Show halfblock preview of the closed/open frame
        from sonic_forge.image_heads import _img_to_halfblocks
        preview_key = ("closed", "open")
        if preview_key not in frames:
            preview_key = list(frames.keys())[0]
        lines = _img_to_halfblocks(frames[preview_key], width)
        print(f"\n  Character: {name}  ({len(frames)} frames)\n")
        for ln in lines:
            print(f"  {ln}")
        print(f"\n  Use with: sonic-forge play song.mp3 --visual {name}\n")
    else:
        print(f"\n  Character '{name}' not found.")
        print(f"  Add it: sonic-forge character {name} <spritesheet.jpg>\n")


@app.command("beat")
def beat_cmd(
    template: str = typer.Argument("cinematic", help="Genre template: trance, lofi, cinematic, ambient, acid, hiphop, minimal, anthem, bluegrass."),
    duration: Optional[float] = typer.Option(None, "--duration", "-d", help="Duration in seconds (default ~30s)."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save WAV to this path."),
    no_play: bool = typer.Option(False, "--no-play", help="Generate only, don't play."),
) -> None:
    """Generate bytebeat instrumental music from the command line.

    sonic-forge beat                          # cinematic, ~30s
    sonic-forge beat trance                   # trance template
    sonic-forge beat acid -d 60               # 60s of acid house
    sonic-forge beat bluegrass -o banjo.wav   # save bluegrass to file
    sonic-forge beat ambient -d 120           # 2 min ambient
    """
    import tempfile
    from sonic_forge.templates import apply_template

    song = apply_template(template, [])  # instrumental = no texts

    # Build minimal YAML
    import yaml
    yaml_path = tempfile.mktemp(suffix=".yaml", prefix="beat_")
    with open(yaml_path, "w") as f:
        yaml.dump(song, f, default_flow_style=False)

    out_path = output or tempfile.mktemp(suffix=".wav", prefix="beat_")

    print(f"\n  Generating {template} beat...")

    from sonic_forge.songfile import render_yaml_song
    render_yaml_song(
        yaml_path, output_path=out_path, play=not no_play,
        target_duration=duration,
    )

    if output:
        print(f"\n  Saved: {out_path}\n")

    # Cleanup temp yaml
    if os.path.exists(yaml_path) and yaml_path.startswith(tempfile.gettempdir()):
        os.remove(yaml_path)
    if not output and os.path.exists(out_path):
        os.remove(out_path)


@app.command("narrate")
def narrate_cmd(
    input_path: str = typer.Argument(..., help="Text file with paragraphs separated by blank lines. Supports [pause: label] and [pause: 1.2] markup. Use '-' for stdin."),
    output: str = typer.Argument(..., help="Target WAV path. Manifest emitted alongside at OUTPUT.timing.json (unless --no-manifest)."),
    voice: Optional[str] = typer.Option(None, "--voice", "-v", help="Voice short name or full ID. Defaults: af_heart for kokoro, natural choice per lang otherwise."),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Auto-pick engine + voice by language (telugu, hindi, english, french, ...)."),
    engine: Optional[str] = typer.Option(None, "--engine", "-e", help="Force engine: say / kokoro / edge. Auto-picked if omitted."),
    phonics: Optional[str] = typer.Option(None, "--phonics", help="JSON file of word→pronunciation replacements applied before TTS. Optional."),
    seed: Optional[int] = typer.Option(None, "--seed", help="Seed pause-pool randomness for reproducibility."),
    fps: int = typer.Option(30, "--fps", help="Frame rate assumed for manifest total_frames."),
    no_manifest: bool = typer.Option(False, "--no-manifest", help="Skip the *.timing.json output."),
    sample_rate: int = typer.Option(24000, "--sample-rate", help="Output sample rate in Hz."),
) -> None:
    """Produce a long-form narration WAV + timing manifest.

    Paragraph-chunked TTS with ffmpeg-generated silence between paragraphs.
    Pause pools (tiny/short/medium/long/xlong) give natural variation, and
    the emitted `*.timing.json` lets Remotion/DaVinci align visuals to audio.

    Markup inside the input file:
      Blank lines → default medium pause.
      [pause: short]   → pick from the short pool.
      [pause: xlong]   → pick from the xlong pool.
      [pause: 1.2]     → 1.2s ± 15% jitter.

    English, default Kokoro voice:
      sonic-forge narrate script.txt narration.wav --voice am_fenrir

    With phonics dictionary (project-specific word fixups):
      sonic-forge narrate script.txt narration.wav --phonics ./phonics.json

    Reproducible pause timing:
      sonic-forge narrate script.txt narration.wav --seed 608

    Telugu via edge-tts (Kokoro can't do Telugu):
      sonic-forge narrate script.txt narration.wav --lang telugu

    From stdin:
      cat script.txt | sonic-forge narrate - narration.wav
    """
    from sonic_forge.narrate import narrate as do_narrate

    try:
        do_narrate(
            input_path=input_path,
            output_path=output,
            voice=voice,
            engine=engine,
            lang=lang,
            phonics=phonics,
            seed=seed,
            fps=fps,
            sample_rate=sample_rate,
            write_manifest=not no_manifest,
            verbose=True,
        )
    except RuntimeError as e:
        print(f"\n  {e}\n")
        raise typer.Exit(1)


@app.command("kokoro-prep")
def kokoro_prep_cmd(
    input_file: str = typer.Argument(..., help="Path to plain text script file."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save optimized script to file."),
    mode: str = typer.Option("simple", "--mode", "-m", help="Conversion mode: simple (rule-based) or smart (LLM-enhanced)."),
    pace: str = typer.Option("normal", "--pace", "-p", help="Pacing: slow, normal, or fast."),
    speak: bool = typer.Option(False, "--speak", "-s", help="Generate audio with Kokoro after conversion."),
    voice: str = typer.Option("am_onyx", "--voice", "-v", help="Kokoro voice for --speak."),
    audio_output: Optional[str] = typer.Option(None, "--audio", "-a", help="Save audio WAV to this path (implies --speak)."),
) -> None:
    """Convert a plain script to Kokoro-optimized narration with pauses.

    Inserts punctuation-based pause control that Kokoro interprets as
    natural breathing, thinking pauses, and section breaks.

    Rule-based (no dependencies):
      sonic-forge kokoro-prep script.txt
      sonic-forge kokoro-prep script.txt -o optimized.txt
      sonic-forge kokoro-prep script.txt --pace slow

    LLM-enhanced (needs claude or ollama):
      sonic-forge kokoro-prep script.txt --mode smart

    Convert and speak:
      sonic-forge kokoro-prep script.txt --speak
      sonic-forge kokoro-prep script.txt --speak -v af_aoede
      sonic-forge kokoro-prep script.txt -a output.wav
    """
    from sonic_forge.kokoro_prep import prep_script

    text = Path(input_file).read_text()
    print(f"\n  Converting script ({len(text)} chars, mode={mode}, pace={pace})...")

    result = prep_script(text, mode=mode, pace=pace)

    if output:
        Path(output).write_text(result)
        print(f"  Saved: {output}")
    else:
        print(f"\n--- Kokoro-optimized script ---\n")
        print(result)
        print(f"\n--- End ({len(result)} chars) ---\n")

    if speak or audio_output:
        from sonic_forge.tts import speak as do_speak
        wav_path = audio_output or None
        print(f"  Speaking with Kokoro ({voice})...")
        do_speak(result, voice=voice, engine="kokoro", output_path=wav_path, play=not bool(audio_output))


if __name__ == "__main__":
    app()
