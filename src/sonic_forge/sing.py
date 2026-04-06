"""sonic-forge sing — text-to-singing via ACE-Step 1.5 (SFT model).

Generates actual sung vocals with instruments from a text description or lyrics.
Models are downloaded on first use (~4GB total).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACESTEP_REPO = "clockworksquirrel/ace-step-apple-silicon"
ACESTEP_DIR_NAME = "ace-step"
API_PORT = 8001
API_BASE = f"http://127.0.0.1:{API_PORT}"
POLL_INTERVAL = 3  # seconds

# Default generation parameters (proven vocal recipe)
DEFAULT_PARAMS = {
    "inference_steps": 50,
    "guidance_scale": 7.0,
    "thinking": False,
    "use_cot_caption": False,
    "use_cot_language": False,
    "vocal_language": "en",
}

STYLES = {
    "rock": "uplifting anthemic rock, electric guitar, driving drums, stadium energy",
    "pop": "pop ballad, simple piano accompaniment, emotional, intimate recording",
    "bluegrass": "bluegrass folk, acoustic guitar, banjo picking, upbeat country feel",
    "folk": "acoustic folk, warm fingerpicked guitar, gentle and sincere",
    "hiphop": "hip-hop beat, confident delivery, boom bap drums, vinyl crackle",
    "country": "country song, steel guitar, warm and heartfelt, Nashville sound",
    "jazz": "smooth jazz, piano and upright bass, late night club atmosphere",
    "metal": "heavy metal, distorted guitars, powerful screaming vocals, double kick drums",
    "acappella": "a cappella, no instruments, no accompaniment, dry recording, close microphone",
    "indie": "indie rock, jangly guitars, lo-fi warmth, authentic feel",
    "electronic": "electronic pop, synthesizer, vocoded synth vocals, pulsing beat",
    "ambient": "ambient, ethereal pads, soft dreamy vocal, floating atmosphere",
}

LYRIC_PROMPT = """You write song lyrics for a text-to-singing AI. The lyrics will be SUNG, not spoken.

Respond with JSON only:
{"caption": "genre description with vocal style", "lyrics": "the full lyrics with section tags"}

STRICT RULES:
- Use [Verse] and [Chorus] section tags. Optionally [Bridge].
- Keep lines SHORT: 6-10 syllables each. The AI clips long lines.
- 2-3 verses + 1-2 choruses for a 30s song. Scale up for longer.
- Write for SINGING — rhythmic, rhyming, melodic phrasing.
- The caption MUST include "solo [male/female] vocalist singing clearly" plus genre and instruments.
- Do NOT include [Instrumental], [Intro], or [Outro] tags — those suppress vocals.
- Make the lyrics match the user's topic. Be creative but on-topic."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _data_dir() -> Path:
    """Where ACE-Step lives: ~/.sonic-forge/ace-step/"""
    return Path.home() / ".sonic-forge" / ACESTEP_DIR_NAME


def _is_installed() -> bool:
    """Check if ACE-Step repo + SFT model are present."""
    d = _data_dir()
    return (
        (d / "pyproject.toml").exists()
        and (d / "checkpoints" / "acestep-v15-sft").exists()
    )


def _uv_bin() -> str:
    """Find uv binary."""
    uv = shutil.which("uv")
    if uv:
        return uv
    # Common install location
    candidate = Path.home() / ".local" / "bin" / "uv"
    if candidate.exists():
        return str(candidate)
    return "uv"


def _install_ace_step() -> None:
    """Clone repo, install deps, download models. Only runs once."""
    d = _data_dir()
    uv = _uv_bin()

    if not d.exists():
        print(f"\n  First-time setup: downloading ACE-Step (~4GB)...")
        print(f"  This only happens once. Models go in {d}\n")

        # Clone
        print("  [1/3] Cloning ACE-Step Apple Silicon fork...")
        subprocess.run(
            ["git", "clone", "--depth", "1",
             f"https://github.com/{ACESTEP_REPO}.git", str(d)],
            check=True,
        )

        # Install Python deps
        print("  [2/3] Installing Python dependencies (uv sync)...")
        subprocess.run([uv, "sync"], cwd=str(d), check=True)

    # Download SFT model if not present
    sft_dir = d / "checkpoints" / "acestep-v15-sft"
    if not sft_dir.exists():
        print("  [3/3] Downloading SFT vocal model...")
        subprocess.run(
            [uv, "run", "python", "-c",
             "from acestep.model_downloader import download_submodel, get_checkpoints_dir; "
             "download_submodel('acestep-v15-sft', get_checkpoints_dir())"],
            cwd=str(d), check=True,
        )

    # Main model (turbo + vae + text encoder + LM) — needed as base
    turbo_dir = d / "checkpoints" / "acestep-v15-turbo"
    if not turbo_dir.exists():
        print("  Downloading base model components (VAE, text encoder, LM)...")
        subprocess.run(
            [uv, "run", "python", "-c",
             "from acestep.model_downloader import ensure_main_model, get_checkpoints_dir; "
             "ensure_main_model(get_checkpoints_dir())"],
            cwd=str(d), check=True,
        )

    print("  Setup complete.\n")


def _api_healthy() -> bool:
    """Check if ACE-Step API is running."""
    try:
        with urllib.request.urlopen(f"{API_BASE}/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _start_api() -> None:
    """Start the ACE-Step API server in the background."""
    d = _data_dir()
    uv = _uv_bin()
    env = os.environ.copy()
    env["ACESTEP_CONFIG_PATH"] = "acestep-v15-sft"

    log_path = d / ".api.log"
    log_file = open(log_path, "w")

    subprocess.Popen(
        [uv, "run", "acestep-api", "--port", str(API_PORT)],
        cwd=str(d), env=env,
        stdout=log_file, stderr=log_file,
    )

    # Wait for startup
    print("  Starting ACE-Step server (first generation takes ~90s to load)...")
    for i in range(120):  # up to 2 minutes
        time.sleep(1)
        if _api_healthy():
            print("  Server ready.")
            return
        if i % 10 == 9:
            print(f"  Still loading... ({i+1}s)")

    raise RuntimeError(
        f"ACE-Step server failed to start. Check {log_path}"
    )


def _generate(caption: str, lyrics: str, duration: float,
              batch_size: int) -> list[str]:
    """Submit generation job and wait for results. Returns list of mp3 paths."""
    payload = {
        "prompt": caption,
        "lyrics": lyrics,
        "audio_duration": duration,
        "batch_size": batch_size,
        **DEFAULT_PARAMS,
    }

    # Submit job
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_BASE}/release_task",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    task_id = result["data"]["task_id"]

    # Poll for completion
    poll_payload = json.dumps({"task_id_list": [task_id]}).encode()
    while True:
        time.sleep(POLL_INTERVAL)
        req = urllib.request.Request(
            f"{API_BASE}/query_result",
            data=poll_payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())

        items = result.get("data", [])
        if not items:
            continue

        result_str = items[0].get("result", "[]")
        tracks = json.loads(result_str) if isinstance(result_str, str) else result_str
        if not tracks:
            continue

        # Check if any track has status == 1 (completed)
        if tracks[0].get("status", 0) == 1:
            paths = []
            for t in tracks:
                url = t.get("file", "")
                if "path=" in url:
                    path = urllib.parse.unquote(url.split("path=")[1])
                    paths.append(path)
            return paths


def _write_lyrics(topic: str, style: str, voice: str, duration: float) -> tuple[str, str]:
    """Use LLM to write song lyrics. Returns (caption, lyrics)."""
    from sonic_forge.llm import llm_json_request, setup_hint

    style_desc = STYLES.get(style, STYLES["rock"])
    voice_desc = "male" if voice == "male" else "female"

    user_msg = (
        f"Write a {duration:.0f}-second {style} song about: {topic}\n"
        f"Voice: solo {voice_desc} vocalist singing clearly\n"
        f"Style hint for caption: {style_desc}"
    )

    print("  Writing lyrics...")
    data = llm_json_request(LYRIC_PROMPT, user_msg)

    if not data:
        print(setup_hint())
        raise SystemExit(1)

    caption = data.get("caption", f"{style_desc}, solo {voice_desc} vocalist singing clearly")
    lyrics = data.get("lyrics", "")

    # Ensure caption has vocal descriptor
    if "vocalist" not in caption.lower() and "vocal" not in caption.lower():
        caption += f", solo {voice_desc} vocalist singing clearly"

    return caption, lyrics


def _format_lyrics(raw: str) -> str:
    """Ensure lyrics have [Verse]/[Chorus] tags if missing."""
    if "[Verse]" in raw or "[Chorus]" in raw:
        return raw

    # Split into stanzas by double newlines
    stanzas = [s.strip() for s in raw.split("\n\n") if s.strip()]
    if not stanzas:
        return f"[Verse]\n{raw}"

    parts = []
    for i, stanza in enumerate(stanzas):
        tag = "[Chorus]" if i % 3 == 1 and len(stanzas) > 2 else "[Verse]"
        parts.append(f"{tag}\n{stanza}")

    return "\n\n".join(parts)


def _estimate_duration(lyrics: str) -> float:
    """Estimate minimum song duration from lyrics.

    Rule of thumb: ~3 seconds per sung line + 10s padding.
    ACE-Step clips lyrics that don't fit the duration.
    """
    lines = [l.strip() for l in lyrics.splitlines()
             if l.strip() and not l.strip().startswith("[")]
    return max(30, len(lines) * 3 + 10)


def sing(
    topic: Optional[str] = None,
    lyrics: Optional[str] = None,
    style: str = "rock",
    voice: str = "male",
    duration: Optional[float] = None,
    output: Optional[str] = None,
    batch: int = 1,
    no_play: bool = False,
    acappella: bool = False,
    instrumental: bool = False,
    visual: Optional[str] = None,
) -> Optional[str]:
    """Generate a sung song. Returns path to the output mp3."""
    import urllib.parse  # needed in _generate

    wall_start = time.time()

    # Ensure ACE-Step is installed
    if not _is_installed():
        _install_ace_step()

    # Ensure API is running
    if not _api_healthy():
        _start_api()

    # Determine mode
    if acappella and instrumental:
        print("\n  Pick one: --acappella or --instrumental, not both.\n")
        raise SystemExit(1)

    mode = "acappella" if acappella else "instrumental" if instrumental else "song"
    voice_desc = "male" if voice == "male" else "female"
    style_desc = STYLES.get(style, STYLES["rock"])

    # Get caption + lyrics
    if instrumental:
        # Instrumental mode: no vocals, just music
        formatted = "[Instrumental]"
        caption = style_desc
        if topic:
            caption = f"{style_desc}, {topic}"
        print(f"\n  Mode: instrumental")
    elif lyrics:
        # User provided lyrics — could be a file path or literal text
        if os.path.isfile(lyrics):
            with open(lyrics) as f:
                raw_lyrics = f.read()
        else:
            raw_lyrics = lyrics

        formatted = _format_lyrics(raw_lyrics)
        if acappella:
            caption = f"a cappella, solo {voice_desc} voice singing, no instruments, no accompaniment, dry recording, close microphone"
        else:
            caption = f"{style_desc}, solo {voice_desc} vocalist singing clearly"
    elif topic:
        if acappella:
            caption, formatted = _write_lyrics(topic, "acappella", voice, duration or 30)
        else:
            caption, formatted = _write_lyrics(topic, style, voice, duration or 30)
    else:
        print("\n  Provide a topic or --lyrics. Run 'sonic-forge sing --help' for usage.\n")
        raise SystemExit(1)

    # Auto-estimate duration from lyrics if not explicitly set
    if duration is None:
        if instrumental:
            duration = 30  # default for instrumental
        else:
            duration = _estimate_duration(formatted)

    # Show what we're generating
    mode_label = {"song": "vocals + instruments", "acappella": "vocals only",
                  "instrumental": "instruments only"}[mode]
    print(f"\n  Mode: {mode_label}")
    print(f"  Caption: {caption}")
    if not instrumental:
        print(f"  Lyrics:")
        for line in formatted.strip().splitlines():
            print(f"    {line}")
    print(f"\n  Generating {duration:.0f}s {mode} ({batch} take{'s' if batch > 1 else ''})...")

    # Generate
    gen_start = time.time()
    paths = _generate(caption, formatted, duration, batch)
    gen_elapsed = time.time() - gen_start

    if not paths:
        print("  Generation failed — no audio returned.")
        return None

    # Copy to output
    out_dir = Path(output).parent if output else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for i, src in enumerate(paths):
        if output:
            if len(paths) == 1:
                dest = output
            else:
                base, ext = os.path.splitext(output)
                dest = f"{base}-{i+1}{ext}"
        else:
            slug = (topic or "song")[:30].lower()
            slug = "".join(c if c.isalnum() or c in "-_ " else "" for c in slug)
            slug = slug.strip().replace(" ", "-")
            if len(paths) == 1:
                dest = f"{slug}.mp3"
            else:
                dest = f"{slug}-{i+1}.mp3"

        shutil.copy2(src, dest)
        saved.append(dest)

    wall_elapsed = time.time() - wall_start

    # Report
    print(f"\n  Done in {wall_elapsed:.1f}s (generation: {gen_elapsed:.1f}s)")
    for s in saved:
        print(f"  Saved: {s}")

    # Play first track (with optional talking head)
    if not no_play and saved:
        if visual:
            _play_with_visual(saved[0], visual, caption)
        else:
            print(f"\n  Playing {saved[0]}...")
            subprocess.Popen(
                ["afplay", saved[0]],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    return saved[0] if saved else None


def _mp3_to_wav(mp3_path: str) -> Optional[str]:
    """Convert mp3 to wav using macOS afconvert. Returns wav path or None."""
    wav_path = mp3_path.rsplit(".", 1)[0] + ".wav"
    try:
        subprocess.run(
            ["afconvert", mp3_path, wav_path, "-d", "LEI16", "-f", "WAVE"],
            check=True, capture_output=True,
        )
        return wav_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _play_with_visual(mp3_path: str, visual: str, caption: str) -> None:
    """Play song with talking head animation — image or pixel/ASCII."""
    from sonic_forge.image_heads import CHARACTERS_DIR

    parts = visual.split(":")
    char_name = parts[0] if parts else "droid"

    # Check if this is an image character (has folder in ~/.sonic-forge/characters/)
    if (CHARACTERS_DIR / char_name).is_dir():
        from sonic_forge.image_heads import animate_image_character
        print(f"\n  Playing with {char_name} visual...")
        animate_image_character(mp3_path, char_name, text=caption)
        return

    # Fallback to pixel/ASCII talking heads
    wav_path = _mp3_to_wav(mp3_path)
    if not wav_path:
        print("  Could not convert to WAV for visual — playing audio only...")
        subprocess.Popen(
            ["afplay", mp3_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return

    style = parts[1] if len(parts) > 1 else "ascii"
    palette = parts[2] if len(parts) > 2 else "nes"

    try:
        from sonic_forge.talking_heads import animate_character
        print(f"\n  Playing with {char_name} visual...")
        animate_character(
            wav_path, char_name=char_name, text=caption,
            style=style, palette_name=palette,
        )
    except Exception:
        subprocess.run(["afplay", wav_path])
