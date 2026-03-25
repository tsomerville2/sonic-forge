"""Lightweight LLM integration — tries claude CLI first, then API/Ollama."""

import json
import os
import re
import shutil
import subprocess


def _coerce_json(text):
    """Extract JSON from LLM response that might have markdown fences."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    # Try to find JSON object in the text
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _claude_cli_json(prompt, message):
    """Use `claude -p` (Claude Code CLI) — zero deps, uses existing auth."""
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return None
    try:
        full_prompt = f"{prompt}\n\nUser request: {message}"
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            [claude_bin, "-p", full_prompt, "--model", "haiku"],
            capture_output=True, text=True, timeout=30, env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return _coerce_json(result.stdout)
    except Exception:
        pass
    return None


def _load_env_keys():
    """Load API keys from ~/.dev/keys.md and .env if they exist."""
    for path in [os.path.expanduser("~/.dev/keys.md"), ".env"]:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip())


def _claude_api_json(prompt, message):
    """Send JSON request to Claude API."""
    try:
        import anthropic
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=prompt,
            messages=[{"role": "user", "content": message}],
        )
        content = resp.content[0].text if resp.content else ""
        return _coerce_json(content)
    except Exception:
        return None


def _gemini_json(prompt, message):
    """Send JSON request to Gemini."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(f"{prompt}\n\nUser request: {message}")
        return _coerce_json(resp.text)
    except Exception:
        return None


def _pick_ollama_model():
    """Pick the best available Ollama model."""
    explicit = os.environ.get("OLLAMA_MODEL")
    if explicit:
        return explicit
    import urllib.request
    ollama_base = os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434")
    try:
        with urllib.request.urlopen(f"{ollama_base}/api/tags", timeout=2) as resp:
            data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        local = [m for m in models if "-cloud" not in m]
        for prefix in ("gemma3:4b", "qwen3.5", "qwen3", "granite4:latest",
                       "gemma3:12b", "llama3", "mistral"):
            for m in local:
                if m.startswith(prefix):
                    return m
        return local[0] if local else "llama3.2"
    except Exception:
        return "llama3.2"


# Thinking models that need think:false for fast structured output
_THINKING_MODELS = {"qwen3.5", "qwen3", "deepseek", "lfm2.5-thinking"}


def _is_thinking_model(model_name):
    """Check if a model is a thinking model that should have thinking disabled."""
    return any(model_name.startswith(prefix) for prefix in _THINKING_MODELS)


def _ollama_json(prompt, message):
    """Send JSON request to Ollama."""
    import urllib.request
    ollama_base = os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434")
    try:
        model = _pick_ollama_model()
        payload_dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": message},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        # Disable thinking for reasoning models — saves 30-120s per call
        if _is_thinking_model(model):
            payload_dict["think"] = False
        payload = json.dumps(payload_dict).encode()
        req = urllib.request.Request(
            f"{ollama_base}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            content = data.get("message", {}).get("content", "")
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            return _coerce_json(content)
    except Exception:
        return None


def llm_json_request(prompt, message):
    """Send prompt to the best available LLM, return parsed JSON or None.

    Priority: claude CLI > claude API > gemini API > ollama
    """
    # 1. Claude Code CLI — best option, zero deps, uses existing auth
    result = _claude_cli_json(prompt, message)
    if result is not None:
        return result

    # 2. API-based providers
    _load_env_keys()

    if os.environ.get("ANTHROPIC_API_KEY"):
        result = _claude_api_json(prompt, message)
        if result is not None:
            return result

    if os.environ.get("GEMINI_API_KEY"):
        result = _gemini_json(prompt, message)
        if result is not None:
            return result

    # 3. Ollama — local, no key needed
    ollama_base = os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434")
    try:
        import urllib.request
        urllib.request.urlopen(f"{ollama_base}/api/tags", timeout=1)
        result = _ollama_json(prompt, message)
        if result is not None:
            return result
    except Exception:
        pass

    return None


def setup_hint():
    """Return a string explaining how to set up LLM access."""
    return (
        "\n  No AI provider detected. To enable AI-generated briefings:\n"
        "\n"
        "  Claude Code:  Install claude CLI (already handles auth)\n"
        "  Ollama:       ollama serve       (free, local, no API key)\n"
        "  Claude API:   export ANTHROPIC_API_KEY=sk-ant-...\n"
        "  Gemini API:   export GEMINI_API_KEY=...\n"
        "\n"
        "  Without AI, use --text to provide your own script.\n"
    )
