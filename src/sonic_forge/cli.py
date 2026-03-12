"""sonic-forge CLI — bytebeat music + TTS voice system."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="sonic-forge",
    help="Sonic Forge — bytebeat music DSL + multi-engine TTS voice system.",
    no_args_is_help=True,
)


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
        engine=engine, fx=fx,
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


if __name__ == "__main__":
    app()
