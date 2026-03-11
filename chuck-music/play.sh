#!/bin/bash
# Starforge Music Player — pick a track and code to it
# Usage: bash LABS/chuck-music/play.sh

MUSIC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  STARFORGE MUSIC"
echo "  ==============="
echo ""
echo "  AMBIENT / JOURNEY"
echo "  1) space-synth       — organic synths + bowls + chippy arps. hours-long journey"
echo "  2) coding-ambient    — floating pads + euclidean pulses + sparse melody"
echo "  3) coding-flow       — warm pads + gentle melodies, layers fade in slowly"
echo "  4) singing-bowls     — Tibetan brass bowls, tapped and swirled"
echo "  5) cathedral-drift   — deep reverb pads, slow transformation"
echo ""
echo "  DARK"
echo "  6) dark-space        — 80s laser show: massive pads, epic leads, Vangelis vibes"
echo "  7) dark-techno       — tension-driven tempo, sidechain pump, 6-min arc"
echo "  8) dark-ambient      — sinister drones, metallic resonance, creeping dread"
echo "  9) dark-industrial   — harsh, mechanical, acid bass, relentless"
echo ""
echo "  ELECTRONIC"
echo "  10) gameboy-evolve   — 8-bit chiptune with real melodies, never repeats"
echo "  11) euro-rave        — acid bass, four-on-the-floor, sidechain pump, 6-min arc"
echo ""
read -p "  Pick a track (1-11, q to quit): " choice

case "$choice" in
    1) track="space-synth.ck" ;;
    2) track="coding-ambient.ck" ;;
    3) track="coding-flow.ck" ;;
    4) track="singing-bowls.ck" ;;
    5) track="cathedral-drift.ck" ;;
    6) track="dark-space.ck" ;;
    7) track="dark-techno.ck" ;;
    8) track="dark-ambient.ck" ;;
    9) track="dark-industrial.ck" ;;
    10) track="gameboy-evolve.ck" ;;
    11) track="euro-rave.ck" ;;
    q) exit 0 ;;
    *) echo "  Unknown choice"; exit 1 ;;
esac

read -p "  Song length in minutes (default 6, try 2 for a quick preview): " mins
if [ -z "$mins" ]; then mins=6; fi

echo ""
echo "  Playing $track (${mins}m arc)... Ctrl-C to stop"
echo ""
chuck "$MUSIC_DIR/$track":$mins
