#!/bin/bash
# TTS Engine Comparison Player — browse engines × voices, hear the difference
# Arrow keys to navigate, Enter/Space to play, Tab to switch view

VENV_PYTHON="/Users/t/clients/starship/starforge/venv/bin/python"
SAMPLES_DIR="$(cd "$(dirname "$0")/samples" && pwd)"

rm -f /tmp/tts_comparison_player_*.py
TMPSCRIPT="/tmp/tts_comparison_player_$$.py"

cat > "$TMPSCRIPT" << 'PYEOF'
import curses, subprocess, os, sys, time, glob

SAMPLES_DIR = sys.argv[1]

# Discover available engines and their samples
def scan_samples():
    engines = []
    for engine_dir in sorted(os.listdir(SAMPLES_DIR)):
        engine_path = os.path.join(SAMPLES_DIR, engine_dir)
        if not os.path.isdir(engine_path):
            continue
        wavs = sorted(glob.glob(os.path.join(engine_path, "*.wav")))
        if not wavs:
            continue

        lines = []
        fulls = []
        for wav in wavs:
            name = os.path.splitext(os.path.basename(wav))[0]
            if name.startswith("line_"):
                idx = int(name.split("_")[1])
                lines.append((idx, wav, name))
            elif name.startswith("full_"):
                voice = name[5:]
                fulls.append((voice, wav, name))

        lines.sort()
        engines.append({
            "key": engine_dir,
            "name": ENGINE_NAMES.get(engine_dir, engine_dir),
            "lines": lines,
            "fulls": fulls,
            "path": engine_path,
        })
    return engines

ENGINE_NAMES = {
    "kokoro": "Kokoro-82M",
    "kokoro-robot": "Kokoro ROBOT",
    "f5tts": "F5-TTS",
    "vibevoice": "VibeVoice 1.5B",
    "macos-say": "macOS say",
    "chattts": "ChatTTS",
}

ENGINE_INFO = {
    "kokoro": ("~300MB", "ONNX", "Clean, professional, FAST — 54 voices, 8 languages"),
    "kokoro-robot": ("~300MB", "ONNX+FX", "Robotized Kokoro — ringmod, bitcrush, vocoder, droid"),
    "f5tts": ("~1.2GB", "MLX", "Deep human quality, voice cloning"),
    "vibevoice": ("~3GB", "PyTorch", "Diffusion TTS, speaker cloning"),
    "macos-say": ("0MB", "System", "Built-in, instant — 34 voices incl. robots"),
    "chattts": ("~1.1GB", "PyTorch", "Natural laughs/breaths"),
}

NARRATION_TEXTS = [
    "captain's log",
    "clone detection. ten thousand clones across seventy two repos.",
    "semantic grouping. polyglot tokens.",
    "four sound systems evaluated. they said tidal was too rigid. they were wrong.",
    "we followed switch angel. five notes became a world.",
    "the forge makes music now. end of log.",
]

current_engine = 0
current_item = 0
view_mode = "full"  # "full" (voice showcase) or "lines" (individual narration lines)
afplay_proc = None
playing_info = None

def kill_player():
    global afplay_proc, playing_info
    if afplay_proc and afplay_proc.poll() is None:
        afplay_proc.terminate()
        try:
            afplay_proc.wait(timeout=1)
        except:
            afplay_proc.kill()
    afplay_proc = None
    playing_info = None

def play_wav(wav_path, info_str):
    global afplay_proc, playing_info
    kill_player()
    if os.path.exists(wav_path):
        afplay_proc = subprocess.Popen(
            ["afplay", wav_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        playing_info = info_str

def get_items(engine):
    if view_mode == "full":
        return engine["fulls"]
    else:
        return engine["lines"]

def main(stdscr):
    global current_engine, current_item, view_mode

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

    engines = scan_samples()
    if not engines:
        stdscr.addstr(1, 2, "No samples found! Run generate_samples.py first.")
        stdscr.refresh()
        stdscr.nodelay(False)
        stdscr.getch()
        return

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
        title = " TTS ENGINE COMPARISON "
        cx = max(0, (w - len(title)) // 2)
        safe_add(1, cx, title, curses.A_BOLD | curses.color_pair(1))

        mode_str = f"[TAB] Mode: {'Voice Showcase' if view_mode == 'full' else 'Individual Lines'}"
        safe_add(2, max(0, (w - len(mode_str)) // 2), mode_str, curses.color_pair(4))

        # Engine tabs
        y = 4
        tab_x = 2
        for i, engine in enumerate(engines):
            is_sel = (i == current_engine)
            name = engine["name"]
            info = ENGINE_INFO.get(engine["key"], ("?", "?", "?"))

            if is_sel:
                label = f" [{name}] "
                safe_add(y, tab_x, label, curses.A_BOLD | curses.color_pair(2))
            else:
                label = f"  {name}  "
                safe_add(y, tab_x, label, curses.color_pair(5))
            tab_x += len(label) + 1

        # Engine info
        y += 1
        if current_engine < len(engines):
            engine = engines[current_engine]
            info = ENGINE_INFO.get(engine["key"], ("?", "?", "?"))
            n_items = len(get_items(engine))
            pos_str = f"  [{current_item+1}/{n_items}]" if n_items > 0 else ""
            safe_add(y, 4, f"Size: {info[0]}  Runtime: {info[1]}  Vibe: {info[2]}{pos_str}",
                     curses.color_pair(5))

        # Items list (scrollable)
        y += 2
        items = get_items(engine)
        list_start_y = y
        # Total rows available: from here to 5 lines from bottom (status + controls)
        total_rows = max(h - 5 - list_start_y, 3)

        if not items:
            safe_add(y, 4, "(no samples in this mode)", curses.A_DIM)
        else:
            n = len(items)
            need_scroll = n > total_rows

            if not need_scroll:
                # Everything fits — no scroll logic needed
                scroll_offset = 0
                draw_count = n
                show_above = False
                show_below = False
            else:
                # Reserve 1 row each for above/below indicators when needed
                # Usable rows for actual items
                usable = total_rows

                # Center the cursor in the viewport
                half = usable // 2
                scroll_offset = current_item - half
                scroll_offset = max(0, min(scroll_offset, n - usable))

                show_above = scroll_offset > 0
                show_below = (scroll_offset + usable) < n

                # If showing indicators, they eat into usable rows
                item_rows = usable
                if show_above:
                    item_rows -= 1
                if show_below:
                    item_rows -= 1
                item_rows = max(item_rows, 1)

                # Recompute offset with reduced item_rows
                scroll_offset = current_item - item_rows // 2
                scroll_offset = max(0, min(scroll_offset, n - item_rows))
                show_above = scroll_offset > 0
                show_below = (scroll_offset + item_rows) < n
                draw_count = min(item_rows, n - scroll_offset)

            # Draw "above" indicator
            if need_scroll and show_above:
                safe_add(y, 2, f"    ... {scroll_offset} more above ...",
                         curses.A_DIM | curses.color_pair(5))
                y += 1

            # Draw items
            for i in range(scroll_offset, scroll_offset + draw_count):
                item = items[i]
                is_sel = (i == current_item)
                is_playing = (playing_info and playing_info == f"{engine['key']}:{item[2]}"
                              and afplay_proc and afplay_proc.poll() is None)

                if is_sel and is_playing:
                    marker = " >> "
                    attr = curses.A_BOLD | curses.color_pair(3)
                elif is_sel:
                    marker = " >> "
                    attr = curses.A_BOLD | curses.color_pair(2)
                elif is_playing:
                    marker = "  > "
                    attr = curses.color_pair(3)
                else:
                    marker = "    "
                    attr = curses.color_pair(5)

                if view_mode == "full":
                    voice_name = item[0]
                    label = f"{marker}{voice_name}"
                else:
                    idx = item[0]
                    text = NARRATION_TEXTS[idx] if idx < len(NARRATION_TEXTS) else "?"
                    label = f"{marker}[{idx+1}] {text[:w-12]}"

                safe_add(y, 2, label, attr)
                y += 1

            # Draw "below" indicator
            if need_scroll and show_below:
                remaining = n - (scroll_offset + draw_count)
                safe_add(y, 2, f"    ... {remaining} more below ...",
                         curses.A_DIM | curses.color_pair(5))
                y += 1

        # Now playing
        y = max(y + 1, h - 5)
        if playing_info and afplay_proc and afplay_proc.poll() is None:
            tick = int(time.time() * 3) % 3
            dots = "." * (tick + 1)
            safe_add(y, 2, f"  Playing: {playing_info}{dots}",
                     curses.A_BOLD | curses.color_pair(3))
        elif playing_info:
            safe_add(y, 2, "  Finished — ENTER to replay",
                     curses.color_pair(5))

        # Controls
        if h > 3:
            safe_add(h - 3, 2,
                     "  LEFT/RIGHT engine   UP/DOWN voice   ENTER play",
                     curses.color_pair(5))
            safe_add(h - 2, 2,
                     "  TAB mode   a play-all   q quit",
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
            items = get_items(engines[current_engine])
            if items:
                current_item = (current_item + 1) % len(items)
        elif key == curses.KEY_UP or key == ord('k'):
            items = get_items(engines[current_engine])
            if items:
                current_item = (current_item - 1) % len(items)
        elif key == curses.KEY_RIGHT or key == ord('l'):
            current_engine = (current_engine + 1) % len(engines)
            current_item = 0
        elif key == curses.KEY_LEFT or key == ord('h'):
            current_engine = (current_engine - 1) % len(engines)
            current_item = 0
        elif key == ord('\t'):
            view_mode = "lines" if view_mode == "full" else "full"
            current_item = 0
        elif key == ord('\n') or key == ord(' '):
            items = get_items(engines[current_engine])
            if items and current_item < len(items):
                item = items[current_item]
                play_wav(item[1], f"{engines[current_engine]['key']}:{item[2]}")
        elif key == ord('a'):
            # Play all engines' first full sample sequentially
            kill_player()
            for eng in engines:
                fulls = eng["fulls"]
                if fulls:
                    play_wav(fulls[0][1], f"{eng['key']}:{fulls[0][2]}")
                    while afplay_proc and afplay_proc.poll() is None:
                        time.sleep(0.1)

curses.wrapper(main)
PYEOF

exec "$VENV_PYTHON" "$TMPSCRIPT" "$SAMPLES_DIR"
rm -f "$TMPSCRIPT"
