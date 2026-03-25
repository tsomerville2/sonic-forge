---
shipname: sonic-forge
purpose: >-
  Bytebeat music DSL + multi-engine TTS voice system. Inspired by Switch.Angel
  and Tidal Cycles.
tech_stack: []
status: active
created: '2026-03-12'
tags:
  - bytebeat
  - tts
  - music
  - cli
  - python
  - pip
  - tidal-cycles
  - switch-angel
  - kokoro
fleets:
  - name: sonic-forge-fleet
    rank: 0
    star: null
    role: member
commands: {}
---
# sonic-forge

Bytebeat music DSL + multi-engine TTS voice system. `pip install sonic-forge`

## What Is This?

A Python CLI that makes music from code. 27 bundled tracks, 5 synths, 6 drum sounds,
Tidal/Strudel mini-notation, YAML song format, macOS + Kokoro neural TTS, robot voice FX.

Inspired by **Switch.Angel** and her Tidal Cycles live coding streams.
https://www.youtube.com/@Switch-Angel

## Quick Start

```
pipx install sonic-forge        # Recommended — isolated install, global CLI
pipx ensurepath                 # One-time: adds ~/.local/bin to your PATH
# Then open a new terminal

sonic-forge                     # Interactive TUI — browse 27 tracks
sonic-forge play dark-space     # ChucK ambient, 1 hour
sonic-forge play tpl-acid -m 10 # 10 min of acid house
sonic-forge speak "hello" --voice daniel --fx helmet
sonic-forge stop                # Kill all playing audio
```

> **PATH gotcha:** If `sonic-forge` says "command not found" after install,
> run `pipx ensurepath` and restart your terminal. This is a one-time fix
> that covers all pipx-installed tools forever.

## About This Metadata

This project uses **tagsidecar** (`npx tagsidecar`) for project metadata and captain's log.

- `∑ship.md` — project identity, tags, fleet membership (this file)
- `∆captainslog.md` — timestamped discoveries, breakthroughs, and notes

tagsidecar is a lightweight npm tool for developers who work across many projects.
It stores structured metadata alongside your code in simple markdown files with
YAML frontmatter. No database, no server — just files that travel with your repo.

```
npm install -g tagsidecar       # or use npx tagsidecar
tagsidecar ship show            # see this project's metadata
tagsidecar captainslog add "my discovery" --type discovery --content "what I found"
tagsidecar search "some query"  # search across all your projects
tagsidecar discover             # find all ships in subdirectories
```

Learn more: https://www.npmjs.com/package/tagsidecar

