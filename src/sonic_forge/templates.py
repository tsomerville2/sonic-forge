"""
templates.py — Song structure templates for different genres/moods

Two modes per template:
  - NARRATED: music stays out of the voice's way. Pads, bass, light texture.
    The voice is the star. Shorter cycles.
  - INSTRUMENTAL: full builds, dense layers, wild energy. No voice competing.

Usage:
    from templates import TEMPLATES, apply_template
    song = apply_template("cinematic", ["line one", ...])       # narrated
    song = apply_template("cinematic", [])                       # instrumental (10 sections)
"""


def _has_narration(texts):
    """True if there are actual voiceover texts (not just empty/None)."""
    return any(t and t.strip() for t in texts)


# ===================================================================
# TRANCE
# ===================================================================

def _trance_narrated(texts):
    """Narrated trance: pad bed + gentle arp underneath voice, builds gently."""
    k = "g"
    n = len(texts)
    sections = []
    for i, text in enumerate(texts):
        p = i / max(1, n - 1)
        if p < 0.15:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": f"{k}2 bb2 d3"},
                {"synth": "pluck", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 8},
            ]})
        elif p < 0.5:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": f"{k}2 bb2 d3"},
                {"synth": "pluck", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 8},
                {"synth": "bass", "notes": f"{k}1", "fast": 4},
                {"mini": "bd*4"},
            ]})
        elif p < 0.8:
            sections.append({"say": text, "cycles": 3, "layers": [
                {"synth": "pad", "notes": f"{k}2 bb2 d3"},
                {"synth": "acid", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 8},
                {"synth": "bass", "notes": f"{k}1", "fast": 4},
                {"mini": "bd*4"},
                {"mini": "~ hh ~ hh"},
            ]})
        else:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": f"{k}2 bb2 d3"},
            ]})
    return sections


def _trance_instrumental(n=10):
    """Full trance: pluck → acid → supersaw peak → breakdown → peak again."""
    k = "g"
    return [
        {"cycles": 3, "layers": [
            {"synth": "pluck", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 16}]},
        {"cycles": 3, "layers": [
            {"synth": "acid", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 16},
            {"mini": "bd*4"}]},
        {"cycles": 3, "layers": [
            {"synth": "acid", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 16},
            {"synth": "bass", "notes": f"{k}1", "fast": 4},
            {"mini": "bd*4"}, {"mini": "~ hh ~ hh ~ hh ~ hh"}]},
        {"cycles": 4, "layers": [
            {"synth": "acid", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 16},
            {"synth": "saw", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 16},
            {"synth": "bass", "notes": f"{k}1", "fast": 16},
            {"synth": "pad", "notes": f"{k}2 bb2 d3"},
            {"mini": "bd*4"}, {"mini": "[hh hh hh ~]*4"},
            {"mini": "~ sn ~ sn"}, {"mini": "cp(3,8)"}]},
        {"cycles": 2, "layers": [
            {"synth": "pluck", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 16},
            {"synth": "pad", "notes": f"{k}2 bb2 d3"}]},
        {"cycles": 4, "layers": [
            {"synth": "saw", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 16},
            {"synth": "acid", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 16},
            {"synth": "bass", "notes": f"{k}1", "fast": 16},
            {"synth": "pad", "notes": f"{k}2 bb2 d3"},
            {"mini": "bd*4"}, {"mini": "[hh hh hh ~]*4"},
            {"mini": "~ sn ~ sn"}, {"mini": "cp(3,8)"}, {"mini": "oh*2"}]},
        {"cycles": 2, "layers": [
            {"synth": "pluck", "notes": f"{k}2 d3 {k}2 bb3 {k}3", "fast": 16},
            {"synth": "pad", "notes": f"{k}2 bb2 d3"}]},
    ]


# ===================================================================
# LO-FI
# ===================================================================

def _lofi_narrated(texts):
    """Narrated lo-fi: warm pad + slow pluck, gentle beat. Voice sits on top."""
    n = len(texts)
    sections = []
    for i, text in enumerate(texts):
        p = i / max(1, n - 1)
        if p < 0.15 or p > 0.85:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": "c3 e3 g3 b3"},
            ]})
        else:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": "a2 c3 e3"},
                {"synth": "bass", "notes": "a1 a1 c2 c2", "fast": 4},
                {"mini": "bd ~ bd ~"},
                {"mini": "~ ~ [sn ~] ~"},
            ]})
    return sections


def _lofi_instrumental(n=10):
    """Full lo-fi groove with melody and jazzy chords."""
    return [
        {"cycles": 3, "layers": [
            {"synth": "pad", "notes": "c3 e3 g3 b3"},
            {"synth": "pluck", "notes": "e4 g4 b4 g4", "fast": 4}]},
        {"cycles": 4, "layers": [
            {"synth": "pad", "notes": "a2 c3 e3 g3"},
            {"synth": "pluck", "notes": "e4 g4 b4 c5 b4 g4", "fast": 6},
            {"synth": "bass", "notes": "a1 a1 c2 c2", "fast": 4},
            {"mini": "bd ~ bd ~"}, {"mini": "~ ~ [sn ~] ~"}, {"mini": "hh(5,8)"}]},
        {"cycles": 4, "layers": [
            {"synth": "pad", "notes": "f2 a2 c3 e3"},
            {"synth": "pluck", "notes": "c5 a4 f4 a4 c5 e5", "fast": 6},
            {"synth": "bass", "notes": "f1 f1 a1 a1", "fast": 4},
            {"mini": "bd ~ bd ~"}, {"mini": "~ ~ [sn ~] ~"}, {"mini": "hh(5,8)"}]},
        {"cycles": 3, "layers": [
            {"synth": "pad", "notes": "c3 e3 g3 b3"},
            {"synth": "pluck", "notes": "c5 b4 g4 e4", "fast": 4}]},
    ]


# ===================================================================
# CINEMATIC
# ===================================================================

def _cinematic_narrated(texts):
    """Narrated cinematic: deep pads, slow tension. Voice carries the drama."""
    n = len(texts)
    sections = []
    for i, text in enumerate(texts):
        p = i / max(1, n - 1)
        if p < 0.2:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": "d2 a2 d3"},
            ]})
        elif p < 0.45:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": "d2 a2 d3"},
                {"synth": "bass", "notes": "d1", "fast": 2},
            ]})
        elif p < 0.7:
            sections.append({"say": text, "cycles": 3, "layers": [
                {"synth": "pad", "notes": "bb1 d2 f2"},
                {"synth": "bass", "notes": "bb0", "fast": 4},
                {"mini": "bd*4"},
            ]})
        elif p < 0.85:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": "d2 f2 a2"},
                {"synth": "bass", "notes": "d1", "fast": 4},
                {"mini": "bd*4"},
                {"mini": "~ ~ ~ sn"},
            ]})
        else:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": "d2 a2 d3"},
            ]})
    return sections


def _cinematic_instrumental(n=10):
    """Full cinematic: tension → massive hit → resolve."""
    return [
        {"cycles": 3, "layers": [
            {"synth": "pad", "notes": "d2 a2 d3"}]},
        {"cycles": 3, "layers": [
            {"synth": "pad", "notes": "d2 a2 d3"},
            {"synth": "bass", "notes": "d1", "fast": 4},
            {"synth": "pluck", "notes": "d4 f4 a4 d5", "fast": 8}]},
        {"cycles": 3, "layers": [
            {"synth": "pad", "notes": "bb1 d2 f2"},
            {"synth": "acid", "notes": "d2 f2 a2 d3 a2 f2", "fast": 12},
            {"synth": "bass", "notes": "bb0", "fast": 4},
            {"mini": "bd*4"}, {"mini": "~ ~ ~ sn"}]},
        {"cycles": 4, "layers": [
            {"synth": "saw", "notes": "d2 f2 a2 d3", "fast": 16},
            {"synth": "acid", "notes": "d2 f2 a2 d3", "fast": 16},
            {"synth": "pad", "notes": "d2 f2 a2"},
            {"synth": "bass", "notes": "d1", "fast": 8},
            {"mini": "bd*4"}, {"mini": "[hh hh hh ~]*4"},
            {"mini": "~ sn ~ sn"}, {"mini": "cp(3,8)"}]},
        {"cycles": 2, "layers": [
            {"synth": "pad", "notes": "d2 a2 d3 f3"},
            {"synth": "pluck", "notes": "a4 f4 d4 a3", "fast": 4}]},
        {"cycles": 2, "layers": [
            {"synth": "pad", "notes": "d2 a2 d3"}]},
    ]


# ===================================================================
# AMBIENT
# ===================================================================

def _ambient_narrated(texts):
    """Narrated ambient: pure pads drifting. Voice floats in vast space."""
    chords = ["c3 e3 g3", "a2 c3 e3", "f2 a2 c3", "g2 b2 d3",
              "e2 g2 b2", "d2 f2 a2", "c3 e3 g3"]
    sections = []
    for i, text in enumerate(texts):
        chord = chords[i % len(chords)]
        sections.append({"say": text, "cycles": 1, "layers": [
            {"synth": "pad", "notes": chord},
        ]})
    return sections


def _ambient_instrumental(n=10):
    """Full ambient: layered pads, slow pluck, vast space."""
    chords = ["c3 e3 g3", "a2 c3 e3", "f2 a2 c3", "g2 b2 d3",
              "e2 g2 b2", "d2 f2 a2", "c3 e3 g3"]
    sections = []
    for i in range(min(n, len(chords))):
        chord = chords[i]
        if i < 2 or i >= len(chords) - 1:
            sections.append({"cycles": 4, "layers": [
                {"synth": "pad", "notes": chord}]})
        elif i < 4:
            sections.append({"cycles": 4, "layers": [
                {"synth": "pad", "notes": chord},
                {"synth": "pluck", "notes": "g4 e4 c4 e4", "fast": 2}]})
        else:
            sections.append({"cycles": 4, "layers": [
                {"synth": "pad", "notes": chord},
                {"synth": "pad", "notes": "c2 g2"},
                {"synth": "pluck", "notes": "c5 g4 e4 g4", "fast": 2}]})
    return sections


# ===================================================================
# ACID HOUSE
# ===================================================================

def _acid_narrated(texts):
    """Narrated acid: low 303 line + kick only. Voice over the groove."""
    n = len(texts)
    sections = []
    for i, text in enumerate(texts):
        p = i / max(1, n - 1)
        if p < 0.15 or p > 0.85:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "acid", "notes": "c2 c2 eb2 c2", "fast": 8},
            ]})
        else:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "acid", "notes": "c2 c2 eb2 c2 f2 eb2 c2 bb1", "fast": 8},
                {"synth": "bass", "notes": "c1", "fast": 2},
                {"mini": "bd*4"},
            ]})
    return sections


def _acid_instrumental(n=10):
    """Full acid house: 303 goes wild, builds drums."""
    return [
        {"cycles": 3, "layers": [
            {"synth": "acid", "notes": "c2 c2 eb2 c2 f2 eb2 c2 bb1", "fast": 16}]},
        {"cycles": 3, "layers": [
            {"synth": "acid", "notes": "c2 c2 eb2 c2 f2 eb2 c2 bb1", "fast": 16},
            {"mini": "bd*4"}, {"mini": "~ hh ~ hh"}]},
        {"cycles": 4, "layers": [
            {"synth": "acid", "notes": "c2 eb2 f2 ab2 bb2 ab2 f2 eb2", "fast": 16},
            {"synth": "bass", "notes": "c1", "fast": 4},
            {"mini": "bd*4"}, {"mini": "[hh hh hh ~]*4"}, {"mini": "~ ~ cp ~"}]},
        {"cycles": 3, "layers": [
            {"synth": "acid", "notes": "f2 f2 ab2 f2 bb2 ab2 f2 eb2", "fast": 16},
            {"synth": "bass", "notes": "f1", "fast": 4},
            {"mini": "bd*4"}, {"mini": "hh*8"}, {"mini": "~ sn ~ sn"}]},
        {"cycles": 2, "layers": [
            {"synth": "acid", "notes": "c2 c2 eb2 c2", "fast": 8},
            {"mini": "bd*4"}]},
    ]


# ===================================================================
# HIP HOP
# ===================================================================

def _hiphop_narrated(texts):
    """Narrated hiphop: sparse boom-bap, bass, voice is the main event."""
    n = len(texts)
    sections = []
    for i, text in enumerate(texts):
        p = i / max(1, n - 1)
        if p < 0.1 or p > 0.9:
            sections.append({"say": text, "cycles": 1, "layers": [
                {"synth": "pad", "notes": "eb2 g2 bb2"},
            ]})
        else:
            sections.append({"say": text, "cycles": 1, "layers": [
                {"synth": "bass", "notes": "eb1 eb1 bb1 eb1", "fast": 4},
                {"mini": "bd ~ ~ bd ~ ~ bd ~"},
                {"mini": "~ ~ sn ~ ~ ~ sn ~"},
                {"mini": "hh(5,8)"},
            ]})
    return sections


def _hiphop_instrumental(n=10):
    """Full hiphop: boom-bap with melody and bass."""
    return [
        {"cycles": 2, "layers": [
            {"synth": "pad", "notes": "eb2 g2 bb2"}]},
        {"cycles": 4, "layers": [
            {"synth": "bass", "notes": "eb1 eb1 bb1 eb1", "fast": 4},
            {"synth": "pluck", "notes": "eb4 g4 bb4 g4", "fast": 4},
            {"mini": "bd ~ ~ bd ~ ~ bd ~"},
            {"mini": "~ ~ sn ~ ~ ~ sn ~"}, {"mini": "hh*8"}]},
        {"cycles": 4, "layers": [
            {"synth": "bass", "notes": "ab1 ab1 eb1 eb1", "fast": 4},
            {"synth": "pluck", "notes": "ab4 c5 eb5 c5", "fast": 4},
            {"synth": "pad", "notes": "ab2 c3 eb3"},
            {"mini": "bd ~ ~ bd ~ ~ bd ~"},
            {"mini": "~ ~ sn ~ ~ ~ sn ~"}, {"mini": "hh*8"}]},
        {"cycles": 2, "layers": [
            {"synth": "pad", "notes": "eb2 g2 bb2"},
            {"synth": "pluck", "notes": "bb4 g4 eb4 g4", "fast": 2}]},
    ]


# ===================================================================
# MINIMAL TECHNO
# ===================================================================

def _minimal_narrated(texts):
    """Narrated minimal: sparse percussion + low acid. Voice rides the groove."""
    n = len(texts)
    sections = []
    for i, text in enumerate(texts):
        p = i / max(1, n - 1)
        if p < 0.1:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"mini": "bd*4"},
            ]})
        elif p > 0.9:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"mini": "bd*4"}, {"mini": "hh(3,8)"},
            ]})
        else:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "acid", "notes": "c2 c2 eb2 c2", "fast": 4},
                {"synth": "bass", "notes": "c1", "fast": 2},
                {"mini": "bd*4"}, {"mini": "hh(5,8)"},
            ]})
    return sections


def _minimal_instrumental(n=10):
    """Full minimal techno: hypnotic, evolving percussion."""
    return [
        {"cycles": 3, "layers": [{"mini": "bd*4"}]},
        {"cycles": 3, "layers": [
            {"mini": "bd*4"}, {"mini": "hh*8"}, {"mini": "~ ~ cp ~"}]},
        {"cycles": 4, "layers": [
            {"synth": "acid", "notes": "c2 c2 eb2 c2", "fast": 8},
            {"synth": "bass", "notes": "c1", "fast": 2},
            {"mini": "bd*4"}, {"mini": "hh(7,8)"}, {"mini": "cp(3,8)"}]},
        {"cycles": 3, "layers": [
            {"synth": "acid", "notes": "eb2 c2 eb2 f2", "fast": 8},
            {"synth": "bass", "notes": "eb1", "fast": 2},
            {"mini": "bd*4"}, {"mini": "hh(5,8)"}]},
        {"cycles": 2, "layers": [
            {"mini": "bd*4"}, {"mini": "hh(3,8)"}]},
    ]


# ===================================================================
# EPIC ANTHEM
# ===================================================================

def _anthem_narrated(texts):
    """Narrated anthem: warm pad + gentle pluck. Voice is uplifting."""
    n = len(texts)
    sections = []
    for i, text in enumerate(texts):
        p = i / max(1, n - 1)
        if p < 0.15 or p > 0.85:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": "c3 e3 g3"},
            ]})
        elif p < 0.5:
            sections.append({"say": text, "cycles": 2, "layers": [
                {"synth": "pad", "notes": "c3 e3 g3"},
                {"synth": "bass", "notes": "c1", "fast": 4},
                {"mini": "bd*4"},
            ]})
        else:
            sections.append({"say": text, "cycles": 3, "layers": [
                {"synth": "pad", "notes": "c3 e3 g3"},
                {"synth": "pluck", "notes": "g4 e4 c4 e4", "fast": 4},
                {"synth": "bass", "notes": "c1", "fast": 4},
                {"mini": "bd*4"}, {"mini": "~ hh ~ hh"},
            ]})
    return sections


def _anthem_instrumental(n=10):
    """Full anthem: uplifting supersaws, triumphant builds."""
    return [
        {"cycles": 3, "layers": [
            {"synth": "pluck", "notes": "c4 e4 g4 c5 g4 e4", "fast": 8},
            {"synth": "pad", "notes": "c3 e3 g3"}]},
        {"cycles": 3, "layers": [
            {"synth": "pluck", "notes": "c4 e4 g4 c5 g4 e4", "fast": 8},
            {"synth": "pad", "notes": "a2 c3 e3"},
            {"synth": "bass", "notes": "a1", "fast": 4},
            {"mini": "bd*4"}, {"mini": "~ hh ~ hh"}]},
        {"cycles": 3, "layers": [
            {"synth": "saw", "notes": "c3 e3 g3 c4", "fast": 16},
            {"synth": "pad", "notes": "f2 a2 c3"},
            {"synth": "bass", "notes": "f1", "fast": 8},
            {"mini": "bd*4"}, {"mini": "[hh hh hh ~]*4"}, {"mini": "~ ~ cp ~"}]},
        {"cycles": 4, "layers": [
            {"synth": "saw", "notes": "c3 e3 g3 c4 g3 e3", "fast": 16},
            {"synth": "pluck", "notes": "c5 e5 g5 e5 c5", "fast": 8},
            {"synth": "pad", "notes": "c3 e3 g3"},
            {"synth": "bass", "notes": "c1", "fast": 4},
            {"mini": "bd*4"}, {"mini": "[hh hh hh ~]*4"},
            {"mini": "~ sn ~ sn"}, {"mini": "cp(3,8)"}]},
        {"cycles": 2, "layers": [
            {"synth": "pad", "notes": "c3 e3 g3"},
            {"synth": "pluck", "notes": "g4 e4 c4 e4", "fast": 4}]},
    ]


# ===================================================================
# Registry
# ===================================================================

TEMPLATES = {
    "trance": {
        "bpm": 136, "voice": "Samantha", "voice_lead": 2.0,
        "description": "Classic trance — pluck arps, acid, supersaw peak",
        "narrated": _trance_narrated, "instrumental": _trance_instrumental,
    },
    "lofi": {
        "bpm": 78, "voice": "Samantha", "voice_lead": 2.5,
        "description": "Lo-fi chill — jazzy chords, mellow plucks, light groove",
        "narrated": _lofi_narrated, "instrumental": _lofi_instrumental,
    },
    "cinematic": {
        "bpm": 100, "voice": "Daniel", "voice_lead": 2.5,
        "description": "Cinematic — deep tension build, dramatic pads",
        "narrated": _cinematic_narrated, "instrumental": _cinematic_instrumental,
    },
    "ambient": {
        "bpm": 68, "voice": "Moira", "voice_lead": 3.0,
        "description": "Ambient — vast drifting pads, no beats, pure space",
        "narrated": _ambient_narrated, "instrumental": _ambient_instrumental,
    },
    "acid": {
        "bpm": 132, "voice": "Alex", "voice_lead": 1.5,
        "description": "Acid house — 303 bass line, minimal drums, hypnotic",
        "narrated": _acid_narrated, "instrumental": _acid_instrumental,
    },
    "hiphop": {
        "bpm": 88, "voice": "Alex", "voice_lead": 1.5,
        "description": "Hip hop — boom-bap beat, bass heavy, voice forward",
        "narrated": _hiphop_narrated, "instrumental": _hiphop_instrumental,
    },
    "minimal": {
        "bpm": 124, "voice": "Daniel", "voice_lead": 2.0,
        "description": "Minimal techno — hypnotic repetition, deep groove",
        "narrated": _minimal_narrated, "instrumental": _minimal_instrumental,
        "music_volume": 0.5,
    },
    "anthem": {
        "bpm": 138, "voice": "Karen", "voice_lead": 2.0,
        "description": "Epic anthem — uplifting supersaws, triumphant pads",
        "narrated": _anthem_narrated, "instrumental": _anthem_instrumental,
    },
}


def apply_template(template_name, texts):
    """Apply a template to narration texts, return a song dict.

    If texts is empty/None, produces an instrumental version.
    If texts has content, produces a narrated version (sparser music).
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template '{template_name}'. "
                         f"Available: {', '.join(TEMPLATES.keys())}")

    tmpl = TEMPLATES[template_name]
    narrated = _has_narration(texts) if texts else False

    if narrated:
        sections = tmpl["narrated"](texts)
    else:
        sections = tmpl["instrumental"]()

    return {
        "title": f"untitled ({template_name})",
        "bpm": tmpl["bpm"],
        "voice": tmpl["voice"],
        "voice_lead": tmpl["voice_lead"],
        "music_volume": tmpl.get("music_volume", 1.0),
        "sections": sections,
    }


def list_templates():
    """Print available templates."""
    print("\nAvailable song templates:\n")
    for name, tmpl in TEMPLATES.items():
        print(f"  {name:12s}  {tmpl['bpm']:3d} BPM  —  {tmpl['description']}")
    print(f"\n  Each template has narrated (sparse) and instrumental (full) modes.")
    print(f"  Narrated mode auto-activates when your YAML has 'say:' fields.\n")
