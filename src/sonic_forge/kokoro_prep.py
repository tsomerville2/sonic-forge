"""Kokoro Script Converter — transform plain scripts into Kokoro-optimized narration.

Inserts punctuation-based pause control and optional filler words to make
Kokoro-82M narration sound natural with proper pacing and breathing.

Discovery: Kokoro interprets stacked periods/exclamation marks as pauses.
  - Periods (.) work from 4-32 count, produce "mmmm" thinking sounds at 16+
  - Exclamation marks (!) scale from 32-128, peak at 128 (2.4s gap)
  - Em-dashes produce NO pauses — must be replaced
  - Filler words (heh, tsk, sheesh, well, oh) work naturally

Usage:
    from sonic_forge.kokoro_prep import prep_script
    result = prep_script("Your plain text here", mode="simple")
    result = prep_script("Your plain text here", mode="smart")
"""

from __future__ import annotations

import re
import random
from typing import Literal

# Pause tokens
BREATH = "." * 6          # ~0.5s breath pause
THINK = "." * 16          # ~1.6s thinking pause with "mmmm"
SECTION = "." * 32        # ~2.3s section break
LONG = "!" * 128          # ~2.4s long contemplation

# Filler words that Kokoro renders naturally
FILLERS_TRANSITION = ["well", "now", "so", "oh"]
FILLERS_EMPHASIS = ["heh", "tsk", "phew"]
FILLERS_SECTION = ["sheesh", "yikes", "ahhh"]


def _strip_dashes(text: str) -> str:
    """Remove em-dash pause patterns (— — —) that don't work in Kokoro."""
    # Replace spaced em-dash patterns with a single space
    text = re.sub(r'(\s*—\s*)+', ' ', text)
    return text


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving sentence-ending punctuation."""
    # Split on . ! ? followed by space or end of string
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs on double newlines."""
    paras = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in paras if p.strip()]


def _add_comma_breathing(sentence: str) -> str:
    """Add short breath pauses after commas in longer clauses."""
    # Only add breathing to sentences with commas and decent length
    if ',' not in sentence or len(sentence) < 60:
        return sentence
    # Add 4 periods after commas that precede clauses of 30+ chars
    parts = sentence.split(',')
    result = []
    for i, part in enumerate(parts):
        result.append(part)
        if i < len(parts) - 1:
            next_part = parts[i + 1] if i + 1 < len(parts) else ""
            if len(next_part.strip()) > 25:
                result.append(",....")
            else:
                result.append(",")
    return "".join(result)


def prep_simple(text: str, pace: Literal["slow", "normal", "fast"] = "normal") -> str:
    """Rule-based script conversion. No LLM needed.

    Args:
        text: Plain narration script
        pace: How much pause to inject — slow adds more breathing

    Returns:
        Kokoro-optimized script with punctuation pauses
    """
    text = _strip_dashes(text)
    paragraphs = _split_paragraphs(text)

    breath = {"slow": "." * 8, "normal": "." * 6, "fast": "." * 4}[pace]
    think = {"slow": "." * 24, "normal": "." * 16, "fast": "." * 10}[pace]
    section = {"slow": "." * 32, "normal": "." * 24, "fast": "." * 16}[pace]

    output_paragraphs = []
    for para in paragraphs:
        sentences = _split_sentences(para)
        processed = []
        for i, sent in enumerate(sentences):
            sent = _add_comma_breathing(sent)
            processed.append(sent)
            # Add pause between sentences (not after last)
            if i < len(sentences) - 1:
                # Longer pause before important-sounding sentences
                next_sent = sentences[i + 1] if i + 1 < len(sentences) else ""
                if any(w in next_sent.lower() for w in [
                    "this means", "that means", "the key", "the goal",
                    "nothing about", "here's how", "your role",
                    "let their", "remember", "importantly"
                ]):
                    processed.append(think)
                else:
                    processed.append(breath)

        output_paragraphs.append(" ".join(processed))

    # Join paragraphs with section breaks
    return (section + " ").join(output_paragraphs)


def prep_smart(text: str, pace: Literal["slow", "normal", "fast"] = "normal") -> str:
    """LLM-enhanced script conversion. Uses Claude/Ollama to identify
    natural pause points, emphasis, and filler word placement.

    Args:
        text: Plain narration script
        pace: How much pause to inject

    Returns:
        Kokoro-optimized script with punctuation pauses and fillers
    """
    import subprocess
    import json

    text = _strip_dashes(text)

    breath = {"slow": "." * 8, "normal": "." * 6, "fast": "." * 4}[pace]
    think = {"slow": "." * 24, "normal": "." * 16, "fast": "." * 10}[pace]
    section = {"slow": "." * 32, "normal": "." * 24, "fast": "." * 16}[pace]

    prompt = f"""You are a narration director preparing a script for text-to-speech.

The TTS engine (Kokoro) uses punctuation to control pauses:
- BREATH: "{breath}" (insert between sentences in same thought)
- THINK: "{think}" (insert before important statements, after questions, at concept transitions)
- SECTION: "{section}" (insert between major topic changes)

Filler words that sound natural (use sparingly, 2-4 per page max):
- Before transitions: "well", "now", "so"
- Before emphasis: "oh"
- After heavy content: "phew", "sheesh"

Rules:
1. Keep ALL original words exactly as written
2. Insert pause markers BETWEEN sentences/clauses — never inside a word
3. Add comma-breathing (,....) after long clauses (30+ chars before next comma)
4. Use THINK pauses before key definitions, principles, or important statements
5. Use SECTION pauses between major topic shifts
6. Add a filler word + THINK before 2-3 of the most impactful statements
7. Return ONLY the converted script text, nothing else

Input script:
{text}

Output the Kokoro-optimized script:"""

    # Try Claude CLI first, fall back to ollama
    try:
        result = subprocess.run(
            ["claude", "--print", "-p", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback to ollama
    try:
        result = subprocess.run(
            ["ollama", "run", "llama3.2", prompt],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Final fallback: use simple mode
    print("  No LLM available (tried claude, ollama). Falling back to simple mode.")
    return prep_simple(text, pace)


def prep_script(
    text: str,
    mode: Literal["simple", "smart"] = "simple",
    pace: Literal["slow", "normal", "fast"] = "normal",
) -> str:
    """Convert a plain narration script to Kokoro-optimized format.

    Args:
        text: Plain narration script (plain text or with em-dash pauses)
        mode: "simple" for rule-based, "smart" for LLM-enhanced
        pace: "slow" (more pauses), "normal", or "fast" (fewer pauses)

    Returns:
        Kokoro-optimized script with punctuation-based pauses
    """
    if mode == "smart":
        return prep_smart(text, pace)
    return prep_simple(text, pace)
