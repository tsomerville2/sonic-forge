"""sonic-forge CLI — bytebeat music + TTS voice system."""

from __future__ import annotations

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
    name: str = typer.Argument(..., help="Track name (e.g. dark-space, midnight-drive, tpl-acid)."),
    minutes: Optional[int] = typer.Option(None, "--minutes", "-m", help="Duration in minutes (ChucK: default 60, templates: default 3)."),
) -> None:
    """Play a built-in track by name.

    sonic-forge play dark-space                 ChucK, plays 1 hour, Ctrl-C to stop
    sonic-forge play dark-space -m 10           ChucK, 10 minutes
    sonic-forge play tpl-acid                   Generate 3 min of acid house
    sonic-forge play tpl-acid -m 10             Generate 10 min of acid house
    sonic-forge play midnight-drive             Render and play the composed song
    """
    from sonic_forge.launcher import play_song
    play_song(name, minutes=minutes)


@app.command("catalog")
def catalog_cmd() -> None:
    """List all built-in tracks — songs, ChucK, templates."""
    from sonic_forge.launcher import list_songs
    list_songs()


@app.command("render")
def render_cmd(
    song: str = typer.Argument(..., help="YAML song file to render."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output WAV path."),
    play: bool = typer.Option(False, "--play", help="Play after rendering."),
    voice: Optional[str] = typer.Option(None, "--voice", help="TTS voice name (Samantha, af_heart, Zarvox...)."),
    engine: Optional[str] = typer.Option(None, "--engine", help="TTS engine: say (macOS), kokoro (Kokoro-82M)."),
    fx: Optional[str] = typer.Option(None, "--fx", help="Robot effect: helmet, intercom, droid, ringmod, bitcrush."),
    template: Optional[str] = typer.Option(None, "--template", help="Apply genre template."),
    lead: Optional[float] = typer.Option(None, "--lead", help="Voiceover lead time (seconds)."),
    rate: Optional[int] = typer.Option(None, "--rate", help="Speech rate (WPM)."),
    voice_stem: Optional[str] = typer.Option(None, "--voice-stem", help="Save voice-only WAV (for lip sync)."),
) -> None:
    """Render a YAML song to WAV.

    sonic-forge render song.yaml --play
    sonic-forge render song.yaml --voice af_heart --engine kokoro --fx helmet --play
    sonic-forge render song.yaml --voice Daniel --template lofi --play
    """
    from sonic_forge.songfile import render_yaml_song
    render_yaml_song(
        song, output_path=output, play=play,
        voice_override=voice, template_name=template,
        lead_override=lead, speech_rate=rate,
        engine=engine, fx=fx, voice_stem=voice_stem,
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
    text: str = typer.Argument(..., help="Text to speak aloud."),
    voice: Optional[str] = typer.Option(None, "--voice", "-v", help="Voice name (af_heart, Samantha, Zarvox...)."),
    engine: Optional[str] = typer.Option(None, "--engine", "-e", help="TTS engine: say, kokoro."),
    fx: Optional[str] = typer.Option(None, "--fx", help="Robot effect: helmet, intercom, droid, ringmod, bitcrush."),
    rate: Optional[int] = typer.Option(None, "--rate", help="Speech rate in WPM (macOS say)."),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save WAV to this path."),
    no_play: bool = typer.Option(False, "--no-play", help="Generate only, don't play."),
) -> None:
    """Speak text aloud using macOS say or Kokoro TTS.

    sonic-forge speak "Hello world"
    sonic-forge speak "Incoming transmission" --engine kokoro --voice af_heart
    sonic-forge speak "Captain on deck" --fx helmet
    sonic-forge speak "Warning" --voice Zarvox --fx intercom
    """
    from sonic_forge.tts import speak
    speak(text, engine=engine, voice=voice, rate=rate, fx=fx,
          output_path=output, play=not no_play)


@app.command("voices")
def voices_cmd(
    engine: Optional[str] = typer.Option(None, "--engine", "-e", help="Filter by engine: say, kokoro."),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Filter by language code (e.g. en, de, ja, zh)."),
) -> None:
    """List available TTS voices by engine.

    sonic-forge voices
    sonic-forge voices --engine say
    sonic-forge voices --engine kokoro
    sonic-forge voices --engine say --lang en
    sonic-forge voices --engine say --lang de
    """
    show_say = engine is None or engine == "say"
    show_kokoro = engine is None or engine == "kokoro"

    if show_say:
        _list_say_voices(lang)
    if show_kokoro:
        _list_kokoro_voices(lang)


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


if __name__ == "__main__":
    app()
