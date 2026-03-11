#!/bin/bash
# Template Demo Player — arrow keys to browse, space to play
# Same captain's log lyrics, 8 different genre templates

VENV_PYTHON="/Users/t/clients/starship/starforge/venv/bin/python"
DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"

rm -f /tmp/demo_player_*.py
TMPSCRIPT="/tmp/demo_player_$$.py"

cat > "$TMPSCRIPT" << 'PYEOF'
import curses, subprocess, os, sys, time

DEMO_DIR = sys.argv[1]

TRACKS = [
    ("trance",    "136 BPM", "Pluck arps, acid, supersaw peak, breakdowns",     "Samantha"),
    ("lofi",      " 78 BPM", "Jazzy chords, mellow plucks, light boom-bap",     "Samantha"),
    ("cinematic", "100 BPM", "Tension build to massive hit, dramatic arc",       "Daniel"),
    ("ambient",   " 68 BPM", "No beats, pure pads, vast slow atmosphere",        "Moira"),
    ("acid",      "132 BPM", "303 bass line is the star, minimal drums",         "Alex"),
    ("hiphop",    " 88 BPM", "Boom-bap beat, bass heavy, voice forward",         "Alex"),
    ("minimal",   "124 BPM", "Hypnotic repetition, subtle changes, deep groove", "Daniel"),
    ("anthem",    "138 BPM", "Uplifting supersaws, triumphant builds, huge pads", "Karen"),
]

current = 0
afplay_proc = None
playing_idx = -1

def kill_player():
    global afplay_proc, playing_idx
    if afplay_proc and afplay_proc.poll() is None:
        afplay_proc.terminate()
        try:
            afplay_proc.wait(timeout=1)
        except:
            afplay_proc.kill()
    afplay_proc = None
    playing_idx = -1

def play_track(idx):
    global afplay_proc, playing_idx
    kill_player()
    name = TRACKS[idx][0]
    wav = os.path.join(DEMO_DIR, f"captains_log_{name}.wav")
    if os.path.exists(wav):
        afplay_proc = subprocess.Popen(
            ["afplay", wav],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        playing_idx = idx

def main(stdscr):
    global current

    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)
    curses.init_pair(5, curses.COLOR_WHITE, -1)
    curses.init_pair(6, curses.COLOR_RED, -1)

    stdscr.nodelay(True)
    stdscr.keypad(True)

    # Auto-play first track
    play_track(0)

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        def safe_add(y, x, text, attr=0):
            try:
                if 0 <= y < h - 1 and 0 <= x < w:
                    stdscr.addstr(y, x, text[:w-x-1], attr)
            except curses.error:
                pass

        # Title
        title = " TEMPLATE DEMO — Captain's Log "
        cx = max(0, (w - len(title)) // 2)
        safe_add(1, cx, title, curses.A_BOLD | curses.color_pair(1))

        subtitle = "Same lyrics, 8 different genres"
        cx2 = max(0, (w - len(subtitle)) // 2)
        safe_add(2, cx2, subtitle, curses.color_pair(5))

        # Track list
        y = 4
        for i, (name, bpm, desc, voice) in enumerate(TRACKS):
            if y >= h - 4:
                break

            is_selected = (i == current)
            is_playing = (i == playing_idx and afplay_proc and afplay_proc.poll() is None)

            # Selection marker
            if is_selected and is_playing:
                marker = " ▶▶ "
                name_attr = curses.A_BOLD | curses.color_pair(3)
            elif is_selected:
                marker = " >> "
                name_attr = curses.A_BOLD | curses.color_pair(2)
            elif is_playing:
                marker = "  ▶ "
                name_attr = curses.color_pair(3)
            else:
                marker = "    "
                name_attr = curses.color_pair(5)

            safe_add(y, 2, f"{marker}{name:12s}", name_attr)
            safe_add(y, 19, bpm, curses.color_pair(4))
            safe_add(y, 28, voice, curses.color_pair(6))
            safe_add(y, 39, desc[:w-42], curses.color_pair(5))
            y += 1

        # Now playing info
        y = max(y + 1, h - 6)
        if playing_idx >= 0 and afplay_proc and afplay_proc.poll() is None:
            name, bpm, desc, voice = TRACKS[playing_idx]
            tick = int(time.time() * 4) % 4
            frames = ["♪ ♫  ", " ♪ ♫ ", "  ♪ ♫", " ♫ ♪ "]
            safe_add(y, 2, f"{frames[tick]} NOW PLAYING: {name} ({bpm}, voice: {voice})",
                     curses.A_BOLD | curses.color_pair(3))
        elif playing_idx >= 0:
            safe_add(y, 2, "  finished — SPACE or ENTER to replay",
                     curses.color_pair(5))

        # Controls
        if h > 3:
            safe_add(h - 2, 2,
                     "↑↓ select   ENTER/SPACE play   q quit",
                     curses.color_pair(5))

        stdscr.refresh()

        # Input
        key = -1
        while True:
            k = stdscr.getch()
            if k == -1:
                break
            key = k

        if key == -1:
            time.sleep(0.05)
            continue

        if key == ord('q') or key == ord('Q') or key == 27:
            kill_player()
            break
        elif key == curses.KEY_DOWN or key == ord('j'):
            current = (current + 1) % len(TRACKS)
        elif key == curses.KEY_UP or key == ord('k'):
            current = (current - 1) % len(TRACKS)
        elif key == ord('\n') or key == ord(' '):
            play_track(current)
        elif key == curses.KEY_RIGHT or key == ord('l'):
            current = (current + 1) % len(TRACKS)
            play_track(current)
        elif key == curses.KEY_LEFT or key == ord('h'):
            current = (current - 1) % len(TRACKS)
            play_track(current)

curses.wrapper(main)
PYEOF

exec "$VENV_PYTHON" "$TMPSCRIPT" "$DEMO_DIR"
rm -f "$TMPSCRIPT"
