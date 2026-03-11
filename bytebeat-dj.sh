#!/bin/bash
# Bytebeat DJ — interactive player with speed, volume, and track controls
# Writes Python to temp file so curses gets proper terminal access

VENV_PYTHON="/Users/t/clients/starship/starforge/venv/bin/python"

# Clean up any stale temp files, then create fresh one
rm -f /tmp/bytebeat_dj_*.py
TMPSCRIPT="/tmp/bytebeat_dj_$$.py"

cat > "$TMPSCRIPT" << 'PYEOF'
import wave, curses, subprocess, os, sys, time, threading

TRACKS = [
    ("classic",    "t*(t>>8|t>>9)&46&t>>8^(t&t>>13|t>>6)",
     lambda t: (t*(((t>>12)|(t>>8)))&(46&(t>>8)))^((t&(t>>13))|(t>>6))),
    ("melody",     "t*((t>>9)|(t>>13))&16",
     lambda t: t*((t>>9)|(t>>13))&16),
    ("bass",       "t&(t>>8)",
     lambda t: t&(t>>8)),
    ("rhythm",     "(t*(t>>5|t>>8))>>(t>>16)",
     lambda t: (t*((t>>5)|(t>>8)))>>(t>>16) if (t>>16) < 32 else 0),
    ("chaos",      "(t*5&t>>7)|(t*3&t>>10)",
     lambda t: (t*5&(t>>7))|(t*3&(t>>10))),
    ("crowd",      "(t<<1)^((t<<1)+(t>>7)&t>>12)|t>>7",
     lambda t: ((t<<1)^((t<<1)+(t>>7)&t>>12))|t>>(4-(1^7&(t>>19)))|t>>7),
    ("sierpinski", "t&t>>8",
     lambda t: t&t>>8),
    ("42melody",   "t*(42&t>>10)",
     lambda t: (t*(42&t>>10))&255),
    ("glitch",     "t*((t>>12|t>>8)&63&t>>4)",
     lambda t: t*((t>>12|t>>8)&63&t>>4)),
    ("cathedral",  "(t>>6|t|t>>(t>>16))*10+((t>>11)&7)",
     lambda t: (t>>6|t|t>>(t>>16))*10+((t>>11)&7)),
    ("gameboy",    "t*9&t>>4|t*5&t>>7|t*3&t>>10",
     lambda t: (t*9&t>>4|t*5&t>>7|t*3&t>>10)-1),
    ("underwater", "(t*(t>>5|t>>8))>>(t>>16)",
     lambda t: (t*(t>>5|t>>8))>>(t>>16)),
    ("alien",      "t*(((t>>9)^((t>>9)-1)^1)%13)",
     lambda t: t*(((t>>9)^((t>>9)-1)^1)%13)),
]

SPEEDS = [
    (2000,  "0.25x"), (3000,  "0.38x"), (4000,  "0.5x"),
    (5000,  "0.63x"), (6000,  "0.75x"), (7000,  "0.88x"),
    (8000,  "1.0x"),  (9000,  "1.13x"), (10000, "1.25x"),
    (12000, "1.5x"),  (14000, "1.75x"), (16000, "2.0x"),
    (20000, "2.5x"),  (24000, "3.0x"),  (32000, "4.0x"),
]

current_track = 0
speed_idx = 6
volume = 0.5
afplay_proc = None
generating = False
WAV_PATH = "/tmp/bytebeat_dj.wav"
DURATION = 600  # 10 minutes — bytebeat is infinite math, let it ride

def generate_wav(track_idx, rate):
    global generating
    generating = True
    name, _, func = TRACKS[track_idx]
    samples = rate * DURATION
    with wave.open(WAV_PATH, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(1)
        f.setframerate(rate)
        buf = bytearray(samples)
        for t in range(samples):
            try:
                buf[t] = func(t) & 255
            except:
                buf[t] = 128
        f.writeframes(bytes(buf))
    generating = False

def kill_player():
    global afplay_proc
    if afplay_proc and afplay_proc.poll() is None:
        afplay_proc.terminate()
        try:
            afplay_proc.wait(timeout=1)
        except:
            afplay_proc.kill()
    afplay_proc = None

def start_playback():
    global afplay_proc
    kill_player()
    generate_wav(current_track, SPEEDS[speed_idx][0])
    afplay_proc = subprocess.Popen(
        ["afplay", "-v", str(volume), WAV_PATH],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def adjust_volume():
    """Restart playback with new volume (no regeneration needed)."""
    global afplay_proc
    kill_player()
    if os.path.exists(WAV_PATH):
        afplay_proc = subprocess.Popen(
            ["afplay", "-v", str(volume), WAV_PATH],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

def main(stdscr):
    global current_track, speed_idx, volume, afplay_proc

    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_WHITE, -1)

    stdscr.nodelay(True)
    stdscr.keypad(True)

    start_playback()

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        name, formula_str, _ = TRACKS[current_track]
        rate, slabel = SPEEDS[speed_idx]

        # Title
        title = " BYTEBEAT DJ "
        cx = max(0, (w - len(title)) // 2)
        try:
            stdscr.addstr(1, cx, title, curses.A_BOLD | curses.color_pair(1))
        except curses.error:
            pass

        def safe_add(y, x, text, attr=0):
            try:
                if y < h - 1 and x < w:
                    stdscr.addstr(y, x, text[:w-x-1], attr)
            except curses.error:
                pass

        y = 3
        safe_add(y, 2, f"Track {current_track+1}/{len(TRACKS)}", curses.color_pair(2))
        y += 1
        safe_add(y, 4, name, curses.A_BOLD | curses.color_pair(3))
        y += 1
        fdisp = formula_str if len(formula_str) < w - 8 else formula_str[:w-11] + "..."
        safe_add(y, 4, fdisp, curses.color_pair(6))

        # Speed bar
        y += 2
        bar_w = min(30, w - 25)
        if bar_w > 5:
            safe_add(y, 2, "Speed:", curses.color_pair(5))
            pos = int((speed_idx / max(1, len(SPEEDS)-1)) * bar_w)
            bar = "[" + "=" * pos + "O" + "-" * (bar_w - pos) + "]"
            safe_add(y, 9, bar, curses.color_pair(5))
            safe_add(y, 10 + bar_w, f" {slabel} ({rate}Hz)", curses.color_pair(6))

        # Volume bar
        y += 1
        if bar_w > 5:
            safe_add(y, 2, "Vol:  ", curses.color_pair(4))
            vol_pos = int(min(1.0, volume) * bar_w)
            vol_bar = "[" + "=" * vol_pos + "O" + "-" * (bar_w - vol_pos) + "]"
            safe_add(y, 9, vol_bar, curses.color_pair(4))
            safe_add(y, 10 + bar_w, f" {int(volume*100)}%", curses.color_pair(6))

        # Status
        y += 2
        playing = afplay_proc and afplay_proc.poll() is None
        if generating:
            safe_add(y, 4, "generating...", curses.color_pair(1))
        elif playing:
            tick = int(time.time() * 4) % 4
            frames = ["♪ ♫  ", " ♪ ♫ ", "  ♪ ♫", " ♫ ♪ "]
            safe_add(y, 4, f"{frames[tick]} PLAYING", curses.color_pair(3))
        else:
            safe_add(y, 4, "stopped — SPACE to play", curses.color_pair(4))

        # Track list
        y += 2
        safe_add(y, 2, "Tracks:", curses.color_pair(2))
        y += 1
        for i, (tname, _, _) in enumerate(TRACKS):
            if y >= h - 4:
                break
            marker = " >> " if i == current_track else "    "
            attr = curses.A_BOLD | curses.color_pair(3) if i == current_track else curses.color_pair(6)
            safe_add(y, 2, f"{marker}{i+1:2d}. {tname}", attr)
            y += 1

        # Controls
        if h > 3:
            safe_add(h-2, 2, "< > track   ^ v speed   +/- vol   SPACE restart   1-9 jump   q quit", curses.color_pair(6))

        stdscr.refresh()

        # Input — drain all pending keys, act on last meaningful one
        key = -1
        while True:
            k = stdscr.getch()
            if k == -1:
                break
            key = k

        if key == -1:
            time.sleep(0.05)
            # Auto-loop if track ended
            if not generating and afplay_proc and afplay_proc.poll() is not None:
                start_playback()
            continue

        if key == ord('q') or key == ord('Q'):
            kill_player()
            break
        elif key == curses.KEY_RIGHT or key == ord('l'):
            current_track = (current_track + 1) % len(TRACKS)
            start_playback()
        elif key == curses.KEY_LEFT or key == ord('h'):
            current_track = (current_track - 1) % len(TRACKS)
            start_playback()
        elif key == curses.KEY_UP or key == ord('k'):
            if speed_idx < len(SPEEDS) - 1:
                speed_idx += 1
                start_playback()
        elif key == curses.KEY_DOWN or key == ord('j'):
            if speed_idx > 0:
                speed_idx -= 1
                start_playback()
        elif key == ord('+') or key == ord('='):
            volume = min(2.0, round(volume + 0.1, 1))
            adjust_volume()
        elif key == ord('-') or key == ord('_'):
            volume = max(0.0, round(volume - 0.1, 1))
            adjust_volume()
        elif key == ord(' '):
            start_playback()
        elif ord('1') <= key <= ord('9'):
            idx = key - ord('1')
            if idx < len(TRACKS):
                current_track = idx
                start_playback()
        elif key == ord('0'):
            if len(TRACKS) > 9:
                current_track = 9
                start_playback()

curses.wrapper(main)
PYEOF

exec "$VENV_PYTHON" "$TMPSCRIPT"
rm -f "$TMPSCRIPT"
