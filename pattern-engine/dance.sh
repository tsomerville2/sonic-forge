#!/bin/bash
# Ship Dance Visualizer — ASCII ship dances to the trance music
# Uses curses for animation, afplay for audio, synced to BPM

VENV_PYTHON="/Users/t/clients/starship/starforge/venv/bin/python"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Generate the music first if needed
WAV="$SCRIPT_DIR/trance1_1.wav"
if [ ! -f "$WAV" ]; then
    echo "  Generating music..."
    "$VENV_PYTHON" "$SCRIPT_DIR/trance1_1.py"
fi

rm -f /tmp/ship_dance_*.py
TMPSCRIPT="/tmp/ship_dance_$$.py"

cat > "$TMPSCRIPT" << 'PYEOF'
import curses, subprocess, os, sys, time, math, random

WAV_PATH = sys.argv[1] if len(sys.argv) > 1 else ""
BPM = 136
BEAT_SEC = 60.0 / BPM
CYCLE_SEC = BEAT_SEC * 4  # 4 beats per cycle

# Section timestamps (seconds) and intensity (0.0-1.0)
SECTIONS = [
    (0.0,  0.2, "pluck arp alone"),
    (12.3, 0.3, "acid sawtooth"),
    (17.6, 0.5, "kick enters"),
    (22.9, 0.5, "sidechain duck"),
    (28.0, 0.6, "bass pulse"),
    (45.6, 0.7, "supersaw detune"),
    (63.2, 0.8, "cymbal wash"),
    (80.8, 1.0, "FULL POWER"),
]

SHIP = [
    "       ◈       ",
    "      ╱█╲      ",
    "    ╱█████╲    ",
    "  ╱ ◉ ███ ◉ ╲  ",
    " ╱═══█████═══╲ ",
    "╱   ╱ ███ ╲   ╲",
    "▔▔▔╱═══════╲▔▔▔",
    "   ╰═══════╯   ",
]

SHIP_W = max(len(line) for line in SHIP)
SHIP_H = len(SHIP)

# Exhaust flame frames
FLAMES = [
    ["   ╱░░░░░╲   ", "    ╱░░░╲    ", "     ╱░╲     "],
    ["   ╱▓▓▓▓▓╲   ", "    ╱▓▓▓╲    ", "     ╱▓╲     "],
    ["   ╱█▓░▓█╲   ", "    ╱█▓█╲    ", "     ╱█╲     "],
    ["   ╱░▓█▓░╲   ", "    ╱░▓░╲    ", "     ╱░╲     "],
]

# Stars field
stars = []

def init_stars(w, h):
    global stars
    stars = [(random.randint(0, w-1), random.randint(0, h-1),
              random.choice("·.+*✦✧")) for _ in range(40)]

def get_section(t):
    """Return current section intensity and name."""
    intensity, name = 0.2, "..."
    for sec_t, sec_i, sec_name in SECTIONS:
        if t >= sec_t:
            intensity, name = sec_i, sec_name
    return intensity, name

def main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    # Color pairs
    curses.init_pair(1, curses.COLOR_YELLOW, -1)   # ship
    curses.init_pair(2, curses.COLOR_RED, -1)       # flames
    curses.init_pair(3, curses.COLOR_CYAN, -1)      # stars
    curses.init_pair(4, curses.COLOR_GREEN, -1)     # info
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)   # beat flash
    curses.init_pair(6, curses.COLOR_WHITE, -1)     # text

    stdscr.nodelay(True)
    stdscr.keypad(True)

    h, w = stdscr.getmaxyx()
    init_stars(w, h)

    # Start music
    afplay = None
    if WAV_PATH and os.path.exists(WAV_PATH):
        afplay = subprocess.Popen(
            ["afplay", WAV_PATH],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    start_time = time.time()

    def safe_add(y, x, text, attr=0):
        try:
            if 0 <= y < h - 1 and 0 <= x < w:
                stdscr.addstr(y, x, text[:w-x-1], attr)
        except curses.error:
            pass

    while True:
        stdscr.erase()
        now = time.time()
        t = now - start_time
        intensity, section_name = get_section(t)

        # Beat phase (0.0 to 1.0 within each beat)
        beat_phase = (t % BEAT_SEC) / BEAT_SEC
        cycle_phase = (t % CYCLE_SEC) / CYCLE_SEC
        beat_num = int(t / BEAT_SEC)
        on_beat = beat_phase < 0.15  # first 15% of beat = "on"

        # Ship position — bounces on beat, sways with cycle
        base_y = h // 2 - SHIP_H // 2 - 2
        base_x = w // 2 - SHIP_W // 2

        # Vertical bounce on beat (more intense = bigger bounce)
        bounce = 0
        if on_beat:
            bounce = -int(2 * intensity * (1.0 - beat_phase / 0.15))

        # Horizontal sway with cycle
        sway = int(3 * intensity * math.sin(cycle_phase * 2 * math.pi))

        ship_y = base_y + bounce
        ship_x = base_x + sway

        # Draw stars (parallax — some move)
        for sx, sy, sc in stars:
            # Stars drift down slowly, faster stars = brighter
            drift = (t * (0.5 + intensity * 2)) % h
            star_y = int((sy + drift) % h)
            star_x = int((sx + math.sin(t * 0.3 + sx) * intensity) % w)
            twinkle = random.random() > 0.3
            if twinkle:
                safe_add(star_y, star_x, sc, curses.color_pair(3))

        # Beat flash border
        if on_beat and intensity > 0.4:
            flash_char = "█" if intensity > 0.7 else "▓" if intensity > 0.5 else "░"
            flash_attr = curses.color_pair(5) | curses.A_BOLD
            for x in range(0, w - 1, 3):
                safe_add(0, x, flash_char, flash_attr)
                safe_add(h - 2, x, flash_char, flash_attr)

        # Draw ship
        ship_attr = curses.color_pair(1) | curses.A_BOLD
        if on_beat and intensity > 0.6:
            ship_attr = curses.color_pair(5) | curses.A_BOLD  # flash magenta on beat
        for i, line in enumerate(SHIP):
            safe_add(ship_y + i, ship_x, line, ship_attr)

        # Draw exhaust flames (animate with beat)
        flame_idx = beat_num % len(FLAMES)
        flame = FLAMES[flame_idx]
        flame_intensity = int(len(flame) * intensity)
        flame_attr = curses.color_pair(2) | curses.A_BOLD
        for i in range(flame_intensity):
            fx = ship_x + (SHIP_W - len(flame[i])) // 2
            safe_add(ship_y + SHIP_H + i, fx, flame[i], flame_attr)

        # Energy bar
        bar_y = h - 5
        bar_w_max = min(40, w - 10)
        filled = int(bar_w_max * intensity)
        bar = "█" * filled + "░" * (bar_w_max - filled)
        safe_add(bar_y, (w - bar_w_max) // 2, bar,
                 curses.color_pair(2) if intensity > 0.7 else curses.color_pair(4))

        # Section name
        safe_add(bar_y + 1, (w - len(section_name)) // 2, section_name,
                 curses.color_pair(4) | curses.A_BOLD)

        # Beat indicator (4 dots per cycle)
        beat_in_cycle = int(cycle_phase * 4)
        dots = ""
        for b in range(4):
            if b == beat_in_cycle:
                dots += " ● "
            else:
                dots += " ○ "
        safe_add(bar_y + 2, (w - len(dots)) // 2, dots, curses.color_pair(6))

        # Time display
        mins = int(t) // 60
        secs = int(t) % 60
        time_str = f"{mins}:{secs:02d}"
        safe_add(1, w - len(time_str) - 2, time_str, curses.color_pair(6))

        # Title
        title = "✦ STARFORGE DANCE ✦"
        safe_add(1, (w - len(title)) // 2, title,
                 curses.color_pair(1) | curses.A_BOLD)

        stdscr.refresh()

        # Input
        key = -1
        while True:
            k = stdscr.getch()
            if k == -1:
                break
            key = k

        if key == ord('q') or key == ord('Q') or key == 27:
            if afplay and afplay.poll() is None:
                afplay.terminate()
            break

        # Check if music ended
        if afplay and afplay.poll() is not None:
            if afplay and afplay.poll() is not None:
                afplay = None
                # Restart
                if os.path.exists(WAV_PATH):
                    afplay = subprocess.Popen(
                        ["afplay", WAV_PATH],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    start_time = time.time()

        time.sleep(0.033)  # ~30 fps

    if afplay and afplay.poll() is None:
        afplay.terminate()

curses.wrapper(main)
PYEOF

exec "$VENV_PYTHON" "$TMPSCRIPT" "$WAV"
rm -f "$TMPSCRIPT"
