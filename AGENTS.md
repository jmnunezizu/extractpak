# Agent Instructions

This repository builds native tools for extracting Monkey Island Special Edition
assets and generating ScummVM-compatible Ultimate Talkie Edition outputs.

## Working Rules

- Preserve existing CLI behavior unless the user explicitly asks to change it.
- Do not rewrite `extractpak.c` or the Python builders from scratch; make
  focused changes that fit the current structure.
- Do not commit, generate, or copy copyrighted game assets into the repository.
- Treat files under `~/Downloads/MonkeyIsland*` and Ultimate Talkie builder
  folders as local inputs only.
- Keep MI1 and MI2 behavior separate. Do not refactor MI2 while working on MI1
  unless the change is clearly shared infrastructure and is covered by tests.
- Keep orchestration in Python package code under `scummkit/`. The build
  pipeline should not require shell scripts.
- Use `pathlib`, `argparse`, `dataclasses`, `subprocess`, and `struct` in
  Python code, following the existing package style.
- Keep Ogg as the primary validated output path. Be explicit when FLAC/MP3/raw
  behavior is less tested or unsupported.
- Use clear diagnostics for missing external tools, unsupported formats, and
  builder layout mismatches.
- Do not assume external tools are installed. Check for tools before using
  them and report actionable errors.
- Preserve `.work/` outputs when they are useful for debugging, especially in
  verbose builds.
- Avoid destructive commands. Do not remove user-generated build outputs unless
  the command or existing code path clearly owns that output directory.

## Validation

Run the lightweight checks after code changes:

```bash
PYTHONPYCACHEPREFIX=/tmp/extractpak-pycache python3 -m py_compile scummkit/*.py scummkit/commands/*.py
python3 -m pytest
```

Compile the C extractor after `extractpak.c` changes:

```bash
clang extractpak.c -o extractpak
```

Useful real-build smoke commands when local assets are available:

```bash
python3 -m scummkit build mi1 \
  --pak ~/Downloads/MonkeyIsland/Monkey1.pak \
  --builder ~/Downloads/MI1_Ultimate_Talkie_Edition_Builder \
  --out /tmp/mi1-talkie-test \
  --audio ogg \
  --music hybrid \
  --verbose

python3 -m scummkit build mi2 \
  --pak ~/Downloads/MonkeyIsland2/app/monkey2.pak \
  --builder ~/Downloads/MI2_Ultimate_Talkie_Edition_Builder \
  --out /tmp/mi2-talkie-test \
  --audio ogg \
  --verbose
```

## Project Structure

```text
.
├── docs/                              # Reverse-engineering notes and builder analysis.
│   ├── mi1-ultimate-talkie-builder-analysis.md  # MI1 builder pipeline, formats, and parity notes.
│   └── mi2-ultimate-talkie-builder-analysis.md  # MI2 builder pipeline, formats, and packer notes.
├── scummkit/                          # Preferred Python package and CLI implementation.
│   ├── __init__.py                    # Package marker and version-adjacent metadata location.
│   ├── __main__.py                    # Enables `python3 -m scummkit`.
│   ├── audio.py                       # Audio conversion helpers and external encoder checks.
│   ├── cli.py                         # Top-level argparse parser and dispatch.
│   ├── commands/                      # Command-specific parser registration and handlers.
│   ├── mi1.py                         # MI1 build orchestration.
│   ├── mi1_resources.py               # MI1 SCUMM resource parsing and inspection helpers.
│   ├── mi1_sbl.py                     # MI1 SBL injection implementation.
│   ├── mi2.py                         # MI2 build orchestration.
│   ├── music.py                       # MI1 cdaudio.bat-compatible music processing.
│   ├── monster.py                     # ScummVM speech archive packer and verifier.
│   ├── paths.py                       # Shared path resolution and validation helpers.
│   ├── runner.py                      # Subprocess, verbose, and dry-run execution helpers.
│   ├── sbl.py                         # WAV-to-SBL conversion logic.
│   ├── voices.py                      # MI1/MI2 voice.bat-compatible voice processing.
│   └── xwb.py                         # XACT wave bank parser and extractor.
├── tests/                             # pytest suite for the Python package.
│   ├── test_cli.py                    # CLI parsing and dry-run behavior tests.
│   ├── test_monster.py                # monster.tbl and speech archive packer tests.
│   ├── test_sbl.py                    # WAV-to-SBL conversion tests.
│   └── test_xwb.py                    # XWB parser tests.
├── AGENTS.md                          # Instructions and orientation notes for coding agents.
├── LICENSE                            # MIT license for local modifications and documentation.
├── NOTICE                             # Attribution and upstream licensing notes.
├── README.md                          # Public project documentation and user guide.
├── extractpak.c                       # C PAK extractor; must compile with `clang extractpak.c -o extractpak`.
└── pyproject.toml                     # Python project metadata and pytest configuration.
```

## Common Commands

List PAK contents:

```bash
./extractpak --list ~/Downloads/MonkeyIsland/Monkey1.pak
./extractpak --list ~/Downloads/MonkeyIsland2/app/monkey2.pak
```

Extract only classic SCUMM resources:

```bash
./extractpak --only classic/en ~/Downloads/MonkeyIsland/Monkey1.pak monkey1-classic
./extractpak --only classic/en ~/Downloads/MonkeyIsland2/app/monkey2.pak monkey2-classic
```

Inspect generated MI1 resources:

```bash
python3 -m scummkit inspect mi1 resources --game-dir /tmp/mi1-talkie-test
python3 -m scummkit inspect mi1 room --game-dir /tmp/mi1-talkie-test --room 41
python3 -m scummkit inspect mi1 resource --game-dir /tmp/mi1-talkie-test --room 41 --id 71
```
