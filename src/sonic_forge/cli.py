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
    voice: Optional[str] = typer.Option(None, "--voice", help="TTS voice name."),
    template: Optional[str] = typer.Option(None, "--template", help="Apply genre template."),
    lead: Optional[float] = typer.Option(None, "--lead", help="Voiceover lead time (seconds)."),
    rate: Optional[int] = typer.Option(None, "--rate", help="Speech rate (WPM)."),
) -> None:
    """Render a YAML song to WAV.

    sonic-forge render song.yaml --play
    sonic-forge render song.yaml --voice Daniel --template lofi
    """
    from sonic_forge.songfile import render_from_yaml
    render_from_yaml(
        song, output_path=output, play=play,
        voice_override=voice, template_name=template,
        lead_override=lead, speech_rate=rate,
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


if __name__ == "__main__":
    app()
