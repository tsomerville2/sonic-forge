#!/bin/bash
# Starforge Sound Demo Tour v2
# Run this, rate each sound, and it saves LABS/sound-rating.md for Claude to read.
# v2: synths volume-reduced ~60%, warp has harmonics, bytebeat added

RATING_FILE="$(dirname "$0")/sound-rating.md"

cat > "$RATING_FILE" << 'HEADER'
# Sound Rating — Demo Tour Results

| # | Sound | Type | Like? | Volume (1-10) | Notes |
|---|-------|------|-------|---------------|-------|
HEADER

sounds=(
  "Glass|system|/System/Library/Sounds/Glass.aiff|boot chime"
  "Hero|system|/System/Library/Sounds/Hero.aiff|success/completion"
  "Basso|system|/System/Library/Sounds/Basso.aiff|error buzz"
  "Ping|system|/System/Library/Sounds/Ping.aiff|scan beep"
  "Purr|system|/System/Library/Sounds/Purr.aiff|warp engage"
  "Pop|system|/System/Library/Sounds/Pop.aiff|dock/connect"
  "Sosumi|system|/System/Library/Sounds/Sosumi.aiff|alert/warning"
  "Tink|system|/System/Library/Sounds/Tink.aiff|keystroke/comm"
  "Submarine|system|/System/Library/Sounds/Submarine.aiff|sonar alt"
  "Funk|system|/System/Library/Sounds/Funk.aiff|funky descending"
  "boot|synth|/tmp/sting_boot.wav|rising C major arpeggio"
  "forge|synth|/tmp/sting_forge.wav|sweep + chord burst"
  "error|synth|/tmp/sting_error.wav|falling minor third + buzz"
  "scan|synth|/tmp/sting_scan.wav|sonar ping + echo"
  "warp|synth|/tmp/sting_warp.wav|exponential freq sweep"
  "alert|synth|/tmp/sting_alert.wav|double pulse"
  "success|synth|/tmp/sting_success.wav|ascending fifth + shimmer"
  "bytebeat|synth|/tmp/sting_bytebeat.wav|math formula → music (bitwise ops on time)"
)

echo ""
echo "  ◈ STARFORGE SOUND DEMO TOUR"
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ${#sounds[@]} sounds to rate. For each:"
echo "    - Listen"
echo "    - Like it? (y/n/meh)"
echo "    - Volume 1-10 (10=loudest)"
echo "    - Any notes (or just press enter)"
echo ""
echo "  Type 'r' to replay, 'q' to quit early."
echo ""

i=1
for entry in "${sounds[@]}"; do
  IFS='|' read -r name type path desc <<< "$entry"

  if [ ! -f "$path" ]; then
    echo "  ⚠  Skipping $name — file not found: $path"
    echo "| $i | $name | $type | SKIP | - | file not found |" >> "$RATING_FILE"
    ((i++))
    continue
  fi

  echo "  [$i/${#sounds[@]}] $name ($type) — $desc"

  while true; do
    afplay "$path" &
    AFPLAY_PID=$!
    wait $AFPLAY_PID 2>/dev/null

    read -p "  Like? (y/n/meh/r=replay/q=quit): " like
    [ "$like" = "r" ] && continue
    [ "$like" = "q" ] && break 2
    break
  done

  read -p "  Volume 1-10 (10=loudest): " vol
  read -p "  Notes (enter to skip): " notes

  echo "| $i | $name | $type | $like | $vol | $notes |" >> "$RATING_FILE"
  echo ""
  ((i++))
done

echo "" >> "$RATING_FILE"
echo "## Summary" >> "$RATING_FILE"
echo "" >> "$RATING_FILE"
echo "Rated on $(date '+%Y-%m-%d %H:%M')" >> "$RATING_FILE"

echo ""
echo "  ✓ Ratings saved to: $RATING_FILE"
echo "  Run starforge and Claude will read it."
echo ""
