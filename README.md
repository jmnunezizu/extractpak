<img src="images/scummkit-logo-web.png" alt="SCUMMKit logo" width="520">

# SCUMMKit

Cross-platform tools for building ScummVM-compatible Monkey Island Ultimate
Talkie Edition folders from legally owned Special Edition game files.

Point SCUMMKit at your local `Monkey1.pak` or `monkey2.pak`, choose an output
folder, and it extracts the classic resources, applies the talkie patches,
processes speech and sound assets, and writes a game directory you can add to
ScummVM.

SCUMMKit is designed for macOS, Linux, and Unix-like Windows environments such
as WSL or MSYS2. It uses Python plus common command line tools, and it does not
ship commercial game data or generated game output.

Supported games:

- [The Secret of Monkey Island: Special Edition](https://www.gog.com/en/game/the_secret_of_monkey_island_special_edition)
- [Monkey Island 2 Special Edition: LeChuck's Revenge](https://www.gog.com/en/game/monkey_island_2_special_edition_lechucks_revenge)

## What It Does

- Builds local ScummVM-compatible output folders for both supported games.
- Extracts classic SCUMM resources from Special Edition PAK files.
- Extracts and converts XACT wave bank (`.xwb`) speech, sound, music, and
  ambience assets.
- Packs ScummVM compressed speech archives such as `monkey.sog` and
  `monkey2.sog`.
- Injects high-quality SBL sound-effect resources for The Secret of Monkey
  Island.
- Converts music for The Secret of Monkey Island and supports `cd`, `hybrid`,
  and `se` root soundtrack modes.
- Provides SCUMM resource inspection and diagnostics commands.
- Python CLI: `python3 -m scummkit` and installed `scummkit`
- Automated pytest coverage for CLI parsing, archive packing, XWB parsing,
  SBL generation, and build diagnostics.

## What You Need

- A legally owned copy of one or both supported Special Edition games.
- Extracted game files, including the `.pak` file and matching `audio/`
  folder.
- Python 3.9 or newer.
- Common command line tools: `sox`, `ffmpeg`, `bspatch`, and `vgmstream-cli`.
- A compiled local `extractpak` helper.
- ScummVM to play the generated output folder.

You do not need the original Ultimate Talkie builder folder for normal builds.
SCUMMKit includes the minimal patch/table data with permission.

## Install / Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd SCUMMKit
   ```

2. Install required tools:

   macOS with Homebrew:

   ```bash
   brew install python sox ffmpeg vgmstream
   ```

   Debian/Ubuntu:

   ```bash
   sudo apt install python3 python3-pytest sox ffmpeg bsdiff clang
   ```

   Install `vgmstream-cli` from your package manager, upstream releases, or
   source if your distribution does not provide it.

   Windows users can run SCUMMKit from WSL, MSYS2, or another environment
   that provides Python, `bspatch`, `sox`, `ffmpeg`, and `vgmstream-cli` on
   `PATH`.

3. Compile the PAK extractor:

   ```bash
   clang extractpak.c -o extractpak
   ```

4. Verify the SCUMMKit environment:

   ```bash
   python3 -m scummkit doctor --out /tmp/scummkit-test
   ```

5. Verify the Python package:

   ```bash
   PYTHONPYCACHEPREFIX=/tmp/scummkit-pycache python3 -m py_compile scummkit/*.py scummkit/commands/*.py
   python3 -m pytest
   ```

### Tool Requirements

- Python 3.9 or newer: runs the `scummkit` package and tests.
- `extractpak`: local compiled helper for extracting `classic/en` resources
  from Monkey Island Special Edition PAK files.
- `bspatch`: applies the Ultimate Talkie binary patch files.
- `ffmpeg`: decodes WMA/XWMA sound-effect entries where needed.
- `sox`: performs trim, mix, gain, pad, and audio conversion operations.
- `vgmstream-cli`: decodes MI1 XACT music banks correctly.
- `clang`: optional but recommended; used to compile `extractpak.c`.

Audio encoder support:

- Ogg Vorbis: SoX with Ogg support, `oggenc`, or `ffmpeg`.
- FLAC: `flac` or `ffmpeg`.
- MP3: `lame` or `ffmpeg`.

### Doctor Command

`scummkit doctor` checks the assumptions that the native build pipeline relies
on before you start a long build:

```bash
python3 -m scummkit doctor
python3 -m scummkit doctor --out /tmp/scummkit-test
python3 -m scummkit doctor --json
```

It verifies the Python version, required external tools (`ffmpeg`, `sox`,
`vgmstream-cli`, and the local `extractpak` helper), package import health, and
optionally whether an output directory can be written. It exits with status `0`
when all required checks pass and non-zero when any required check fails.
Use `--json` when you need machine-readable output for scripts or CI probes.

## Quick Start

Check your local tools and Python package first:

```bash
python3 -m scummkit doctor --out /tmp/scummkit-test
```

Build Monkey Island 1:

```bash
python3 -m scummkit build mi1 \
  --pak ~/Downloads/MonkeyIsland/Monkey1.pak \
  --out ~/Downloads/ScummVM/MI1_Ultimate_Talkie_Edition \
  --audio ogg \
  --music se
```

Build Monkey Island 2:

```bash
python3 -m scummkit build mi2 \
  --pak ~/Downloads/MonkeyIsland2/app/monkey2.pak \
  --out ~/Downloads/ScummVM/MI2_Ultimate_Talkie_Edition \
  --audio ogg
```

Add the generated output folder to ScummVM, not the original Special Edition
installation folder.

## CLI Reference

Use `python3 -m scummkit --help` to list commands, and
`python3 -m scummkit <command> --help` for command-specific options.

| Command | When to use it |
| ------- | -------------- |
| `doctor` | Check Python, external tools, local `extractpak`, imports, and optional output-directory write access before starting a build. |
| `build mi1` / `build mi2` | Generate a complete ScummVM-compatible output folder for a supported game. |
| `builder-inputs mi1` / `builder-inputs mi2` | Confirm whether SCUMMKit is using bundled Ultimate Talkie patch/table data or data from an optional original builder folder. |
| `xwb` | Inspect or extract a Special Edition XACT wave bank. Useful when checking whether speech, music, ambience, or sound-effect entries exist in local game assets. |
| `monster` | Build or verify a ScummVM speech archive from processed samples and `monster.tbl`. Useful for isolating archive packing issues from the full build. |
| `wav2sbl` | Convert an 8-bit mono PCM WAV file into an MI1 SBL sound-effect chunk, or inspect an existing SBL file. |
| `inject mi1 sbl` | Inject MI1 SBL sound effects into `monkey.000`/`monkey.001` without running the full MI1 build again. |
| `inspect mi1 resources` | List indexed MI1 SCUMM resources in a generated output folder. |
| `inspect mi1 room` | List the scripts, sounds, costumes, and charsets attached to one MI1 room. |
| `inspect mi1 resource` | Show or dump one indexed MI1 resource for low-level patch/debug work. |
| `room-audio-report mi1` | Summarise one MI1 room's sound resources, scripts, ambience cues, and root music track references. This is the fastest starting point for missing-room-audio investigations. |
| `ambience-report mi1` | Map MI1 Special Edition ambience cue names to `Ambience.xwb` entries. Useful when tracing SE ambience coverage. |
| `script-reference-report mi1` | Scan MI1 scripts for candidate room, sound, or root-track byte references. Useful when a room behaves differently from the expected audio plan. |
| `speech-manifest mi1` | Generate a manifest from MI1 `speech.info`, optionally compare it with `monster.tbl`, and write a generated table for analysis. |
| `patch-diff mi1` | Compare original and patched MI1 SCUMM resource files, with optional JSON reports and sound-plan classification. |
| `bsdiff-inspect` | Inspect a raw BSDIFF40 patch file when debugging patch size, block structure, or provenance. |

Typical troubleshooting flow:

1. Run `doctor` first to rule out missing tools and write-permission issues.
2. Use `builder-inputs` if a build unexpectedly reads different patch/table
   data than you intended.
3. Use `room-audio-report mi1` for missing MI1 music, ambience, or sound
   effects in a specific room.
4. Use `inspect mi1 room` or `inspect mi1 resource` when the report points to
   a specific SCUMM room or resource.
5. Use `xwb`, `speech-manifest`, `monster`, or `patch-diff` when you need to
   isolate one asset format or one pipeline stage from the full build.

## Extracting GOG Installers

If you downloaded the Windows installers from GOG, extract them first with
`innoextract`.

```bash
brew install innoextract
```

Extract The Secret of Monkey Island: Special Edition:

```bash
innoextract -d MonkeyIsland setup_the_secret_of_monkey_islandtm_special_edition_1.0_\(18587\).exe
```

Extract Monkey Island™ 2 Special Edition: LeChuck’s Revenge:

```bash
innoextract -d MonkeyIsland2 setup_monkey_island2_se_2.0.0.10.exe
```

Typical resulting paths:

```text
MonkeyIsland/Monkey1.pak
MonkeyIsland/audio/
MonkeyIsland2/app/monkey2.pak
MonkeyIsland2/app/audio/
```

## Support Matrix

| Game                               | Build support                       | Notes                                                                                                                                                                                                     |
| ---------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The Secret of Monkey Island        | Ogg validated                       | Builds `monkey.000`, `monkey.001`, `monkey.sog`, root music tracks, and MI1 SBL sound-effect resources. Uses bundled Ultimate Talkie `patch10.*` and `monster.tbl` files with permission. |
| Monkey Island 2: LeChuck's Revenge | Ogg validated                       | Builds `monkey2.000`, `monkey2.001`, and `monkey2.sog`. Uses bundled Ultimate Talkie `patch02.*` and `monster.tbl` files with permission. FLAC/MP3 use the same compressed archive path when encoders are available. |

## Game-Specific Options

| Game | Option | Supported values | Recommended | Notes |
| ---- | ------ | ---------------- | ----------- | ----- |
| The Secret of Monkey Island | `--audio` | `ogg` | `ogg` | FLAC/MP3/raw are not currently validated for the MI1 build pipeline. |
| The Secret of Monkey Island | `--music` | `se`, `hybrid`, `cd` | `se` | `se` uses the full Special Edition soundtrack and ambience path. `hybrid` uses classic CD music plus selected SE ambience tracks. `cd` uses classic CD root tracks. |
| The Secret of Monkey Island | `--skip-sbl` | flag | off | Skips MI1 high-quality SBL sound-effect injection. |
| The Secret of Monkey Island | `--skip-music` | flag | off | Skips MI1 music conversion and root soundtrack copying. |
| Monkey Island 2: LeChuck's Revenge | `--audio` | `ogg`, `flac`, `mp3` | `ogg` | Ogg is the primary validated target. Raw `monster.sou` generation is not implemented. |

## Building Monkey Island 1

```bash
python3 -m scummkit build mi1 \
  --pak ~/Downloads/MonkeyIsland/Monkey1.pak \
  --out ~/Downloads/ScummVM/MI1_Ultimate_Talkie_Edition \
  --audio ogg \
  --music se
```

Required inputs:

- `Monkey1.pak`
- `audio/Speech.xwb`
- `audio/SFXNew.xwb`
- `audio/MusicOriginal.xwb`
- `audio/MusicNew.xwb`
- `audio/Ambience.xwb`
- bundled MI1 Ultimate Talkie patch data under `third_party/ultimate-talkie/mi1/`

Options:

- `--pak PATH`: path to `Monkey1.pak`.
- `--builder PATH`: optional path to the extracted MI1 Ultimate Talkie builder
  folder; defaults to bundled patch/table data.
- `--out PATH`: output folder to create.
- `--audio ogg|flac|mp3`: target compressed speech format. MI1 is validated
  for `ogg`.
- `--music cd|hybrid|se`: root soundtrack selection. Use `se` for the fullest
  Special Edition music and ambience path. CLI default: `hybrid`.
- `--skip-sbl`: skip native SBL sound-effect injection.
- `--skip-music`: skip music conversion and root soundtrack copying.
- `--dry-run`: print planned steps without writing final output.
- `--quiet`: explicitly request the default progress-oriented output.
- `--no-progress`: use plain stage output without inline progress updates.
- `--verbose`: print detailed processing and root soundtrack mapping output.

Expected output:

```text
monkey.000
monkey.001
monkey.sog
SCUMMKIT-BUILD.txt
track*.ogg
cd_music_ogg/*.ogg
se_music_ogg/*.ogg
music-root-map.txt
.work/
```

### Music Modes

`--music cd`

- Root `track*.ogg` files come only from `cd_music_ogg/`.
- This is the classic CD soundtrack path.

`--music se` recommended

- Root `track*.ogg` files come from `se_music_ogg/`.
- This uses the full Special Edition soundtrack.
- This includes the SCUMM Bar chatter ambience, because the chatter is mixed
  into the SE `track8.ogg`.

`--music hybrid` default

- Root `track*.ogg` files start from `cd_music_ogg/`.
- `se_music_ogg/track25.ogg` through `track29.ogg` are copied over the root
  output.
- This preserves the current default behavior and mirrors the original
  builder's optional extended-environment root-track workflow.

The original Windows builder generated both `cd_music_ogg/track8.ogg` and
`se_music_ogg/track8.ogg`. Only the SE version contains the SCUMM Bar chatter
mix. The optional `extended_SE_tracks_to_game_folder.bat` moved only SE tracks
`25` through `29` into the root folder; it did not move SE `track8`.

For that reason, `hybrid` keeps CD `track8.ogg`. Use `--music se` if you want
the SCUMM Bar chatter ambience in root playback.

## Building Monkey Island 2

```bash
python3 -m scummkit build mi2 \
  --pak ~/Downloads/MonkeyIsland2/app/monkey2.pak \
  --out ~/Downloads/ScummVM/MI2_Ultimate_Talkie_Edition \
  --audio ogg
```

Required inputs:

- `monkey2.pak`
- `audio/Speech.xwb`
- `audio/Patch.xwb`
- bundled MI2 Ultimate Talkie patch data under `third_party/ultimate-talkie/mi2/`

Options:

- `--pak PATH`: path to `monkey2.pak`.
- `--builder PATH`: optional path to the extracted MI2 Ultimate Talkie builder
  folder; defaults to bundled patch/table data.
- `--out PATH`: output folder to create.
- `--audio ogg|flac|mp3`: target compressed speech format. Ogg is the primary
  validated target.
- `--dry-run`: print planned steps without writing final output.
- `--quiet`: explicitly request the default progress-oriented output.
- `--no-progress`: use plain stage output without inline progress updates.
- `--verbose`: print detailed processing output.

Expected output:

```text
monkey2.000
monkey2.001
monkey2.sog
SCUMMKIT-BUILD.txt
.work/
```

For FLAC or MP3, the speech archive is named `monkey2.sof` or `monkey2.so3`.

## Bundled Patch Data

SCUMMKit includes the small authored Ultimate Talkie patch/table data set
needed to bind the classic game resources to the speech archives:

- MI1: `third_party/ultimate-talkie/mi1/patch10.000`,
  `third_party/ultimate-talkie/mi1/patch10.001`, and
  `third_party/ultimate-talkie/mi1/monster.tbl`.
- MI2: `third_party/ultimate-talkie/mi2/patch02.000`,
  `third_party/ultimate-talkie/mi2/patch02.001`, and
  `third_party/ultimate-talkie/mi2/monster.tbl`.

These files come from the original Ultimate Talkie Edition patch builders by
LogicDeLuxe and are used with permission. They are third-party patch data, not
MIT-licensed SCUMMKit source. Preserve the original patch credit and license
terms in `licenses/original_ute_builder.txt` and
`third_party/ultimate-talkie/README.md`.

The `--builder` option is optional. By default, SCUMMKit reads the bundled
patch/table data. If you pass `--builder`, SCUMMKit reads the same minimal data
from a local original builder folder for comparison or compatibility.

## Inspecting Resources

SCUMMKit can inspect generated MI1 SCUMM resources. This is useful when
debugging SBL injection or checking whether a sound resource is visible through
the resource index.

```bash
python3 -m scummkit inspect mi1 resources --game-dir /tmp/mi1-test
python3 -m scummkit inspect mi1 room --game-dir /tmp/mi1-test --room 41
python3 -m scummkit inspect mi1 resource --game-dir /tmp/mi1-test --room 41 --id 71
```

Dump one resource:

```bash
python3 -m scummkit inspect mi1 resource \
  --game-dir /tmp/mi1-test \
  --room 41 \
  --id 71 \
  --dump /tmp/sound-071.bin
```

Compare against a pre-SBL output:

```bash
python3 -m scummkit inspect mi1 resource \
  --game-dir /tmp/mi1-test \
  --compare /tmp/mi1-test/.work/sbl/pre-sbl \
  --room 41 \
  --id 71
```

## Using extractpak Directly

Build the C extractor:

```bash
clang extractpak.c -o extractpak
```

Common commands:

```bash
./extractpak --list ~/Downloads/MonkeyIsland/Monkey1.pak
./extractpak --list ~/Downloads/MonkeyIsland2/app/monkey2.pak

./extractpak ~/Downloads/MonkeyIsland/Monkey1.pak monkey1-extracted
./extractpak ~/Downloads/MonkeyIsland2/app/monkey2.pak monkey2-extracted

./extractpak --only classic/en ~/Downloads/MonkeyIsland/Monkey1.pak monkey1-classic
./extractpak --only classic/en ~/Downloads/MonkeyIsland2/app/monkey2.pak monkey2-classic

./extractpak --debug-classic ~/Downloads/MonkeyIsland/Monkey1.pak
./extractpak --debug-classic ~/Downloads/MonkeyIsland2/app/monkey2.pak
```

Expected classic outputs:

```text
classic/en/monkey1.000
classic/en/monkey1.001
classic/en/monkey2.000
classic/en/monkey2.001
```

Extraction notes:

- Full extraction also writes `.dds` files for `.dxt` assets.
- DDS generation is disabled when extracting `--only classic/en`.
- Archive entries that start with `/` are written as relative paths.
- Empty archive entry names are skipped.
- If an output file cannot be written, extraction continues and reports the
  failure count at the end.

## Reference: How It Works

SCUMMKit runs the build as a Python-driven pipeline around local game assets,
bundled Ultimate Talkie patch data, and common audio/resource tools.

MI1 pipeline:

```text
Special Edition assets
-> extractpak
-> XWB extraction
-> speech processing
-> monster archive generation
-> SBL generation
-> SBL injection
-> music conversion
-> final ScummVM game
```

MI2 pipeline:

```text
Special Edition assets
-> extractpak
-> XWB extraction
-> speech processing
-> monster archive generation
-> final ScummVM game
```

For MI1, the native builder extracts the classic SCUMM resource files from
`Monkey1.pak`, applies bundled Ultimate Talkie patch files with `bspatch`,
processes speech from `Speech.xwb`, packs `monkey.sog`, injects SBL
sound-effect resources, and generates the selected soundtrack set.

For MI2, it extracts the classic SCUMM resource files from `monkey2.pak`,
applies bundled Ultimate Talkie patch files, processes `Speech.xwb` and
`Patch.xwb`, and packs the ScummVM speech archive.

## Reference: Files and Formats

- `monkey.sog`: MI1 ScummVM compressed speech archive for Ogg Vorbis speech.
- `monkey2.sog`: MI2 ScummVM compressed speech archive for Ogg Vorbis speech.
- `monkey.sof` / `monkey2.sof`: FLAC variants of the compressed speech archive.
- `monkey.so3` / `monkey2.so3`: MP3 variants of the compressed speech archive.
- `monster.sou`: raw/WAV speech archive name used by classic SCUMM talkie
  games; native raw generation is not currently implemented.
- `monster.tbl`: table from the Ultimate Talkie builders mapping MONSTER/SOU
  speech IDs to speech sample names. SCUMMKit uses it to decide which processed
  samples belong in the ScummVM archive. The bundled table is third-party
  patch data used with permission.
- `SBL resources`: MI1 sound resources used for high-quality sound effects.
  The original builder generated them with `wav2sbl.exe` and injected them with
  `scummpacker.exe`; SCUMMKit implements that path natively.
- `patch10.000` / `patch10.001`: MI1 Ultimate Talkie binary patches for
  classic SCUMM resource files. The bundled copies are third-party patch data
  used with permission.
- `patch02.000` / `patch02.001`: MI2 Ultimate Talkie binary patches for
  classic SCUMM resource files. The bundled copies are third-party patch data
  used with permission.
- `Speech.xwb`: XACT wave bank containing spoken dialogue.
- `Patch.xwb`: MI2 XACT wave bank containing replacement or patch speech.
- `SFXNew.xwb`: MI1 Special Edition sound-effect bank used by the SBL path.
- `MusicOriginal.xwb`: MI1 classic CD soundtrack bank.
- `MusicNew.xwb`: MI1 Special Edition soundtrack bank.
- `Ambience.xwb`: MI1 Special Edition ambience bank. This includes the SCUMM
  Bar chatter ambience mixed into the SE soundtrack path.

## Testing

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/scummkit-pycache python3 -m py_compile scummkit/*.py scummkit/commands/*.py
python3 -m pytest
```

The tests cover CLI parsing, dry-run behavior, `monster.tbl` parsing, ScummVM
monster archive build and verification with tiny fake samples, XWB parser
behavior, and SBL conversion with generated WAV data.

For syntax-only validation:

```bash
PYTHONPYCACHEPREFIX=/tmp/scummkit-pycache python3 -m py_compile scummkit/*.py scummkit/commands/*.py
```

## Project History

This repository started as a modernization of `extractpak.c`, an old utility
for extracting Monkey Island Special Edition `.pak` archives. It grew into a
toolkit for building local Ultimate Talkie Edition folders and inspecting
classic LucasArts SCUMM resources.

## Known Limitations

- SCUMMKit uses bundled Ultimate Talkie patch/table data with permission from
  the original patch author. It does not fully regenerate those files.
- MI1 is currently validated for Ogg output. FLAC/MP3 may be added to the MI1
  orchestration once the same end-to-end testing is done.
- MI2 Ogg is the primary validated output. FLAC and MP3 use the same archive
  format support but are less heavily tested.
- Raw `monster.sou` generation is not implemented.
- The PAK parser is intentionally small and targets the two Monkey Island
  Special Edition archive layouts.
- `extractpak` assumes little-endian archive fields and does not fully sandbox
  archive paths beyond stripping leading `/` characters.
- Windows use is expected to work best through WSL or a Unix-like environment
  with the required tools on `PATH`.
- The build pipeline is fully Python-driven. No shell scripts are required for
  orchestration.

## Troubleshooting

### Missing External Tools

If the CLI reports a missing tool, install it and ensure it is on `PATH`.

Common examples:

- `bspatch`: needed for patch files.
- `ffmpeg`: needed for WMA/XWMA SFX decoding.
- `sox`: needed for audio trimming and mixing.
- `vgmstream-cli`: needed for MI1 music bank decoding.

### Speech Is Missing

Check that:

- The bundled `third_party/ultimate-talkie/<game>/monster.tbl` file exists, or
  the optional `--builder` folder contains the expected `tools/monster.tbl`.
- `Speech.xwb` exists under the Special Edition `audio/` directory.
- The output contains `monkey.sog` or `monkey2.sog`.
- ScummVM is pointed at the generated output folder, not the original Special
  Edition folder.

### Music Sounds Wrong

For MI1:

- Make sure `vgmstream-cli` is installed.
- Rebuild with `--verbose`.
- Inspect `music-root-map.txt` in the output folder.
- Try `--music cd`, `--music hybrid`, and `--music se`.
- `--music se` is the mode that includes the SCUMM Bar chatter mix.

For MI2, the native build focuses on the speech archive and patched ScummVM
resource files. Check the original builder documentation for music
expectations.

### ScummVM Does Not Detect the Game

Check that the output folder contains the expected classic resource files:

- MI1: `monkey.000`, `monkey.001`, and `monkey.sog`.
- MI2: `monkey2.000`, `monkey2.001`, and `monkey2.sog`.

If you used a non-Ogg mode, check for the matching archive extension:

- FLAC: `.sof`
- MP3: `.so3`

### Optional Builder Override

The native builders use the bundled patch/table data by default. `--builder`
can still point at a local original Ultimate Talkie builder folder when you
want to compare against or override the bundled files. The analysis notes in
`docs/` record the behavior currently implemented.

## Credits

- ScummVM, for preserving and documenting the runtime behavior these builds
  target.
- LogicDeLuxe and the Ultimate Talkie Edition contributors, for the original
  [Ultimate Talkie Edition builders](https://gratissaugen.de/ultimatetalkies/monkey1.html),
  authored patch data, and permission to include the minimal patch/table files
  used by SCUMMKit.
- vgmstream, for reliable game-audio bank decoding.
- FFmpeg, for broad audio decoding support.
- SoX, for precise audio processing.
- The original `extractpak.c` work in
  [timfel/monkey](https://github.com/timfel/monkey), which this repository
  builds on.

## Legal Notes

This project does not include, distribute, or generate copyrighted game assets
by itself.

You must provide:

- Your own legally owned copies of the Monkey Island Special Edition games.
- The `.pak` and `audio/` files extracted from those games.

SCUMMKit only automates the local build process. The bundled Ultimate Talkie
patch/table files are third-party data used with permission and are not
MIT-licensed SCUMMKit source. The generated output folder contains
LucasArts/Disney game assets derived from your installation and must not be
redistributed.

## Origin, Notice, and License

The `extractpak.c` utility is modified from the original `extractpak.c` in
[timfel/monkey](https://github.com/timfel/monkey), a small repository for
working with Monkey Island Special Edition `.pak` files.

This version keeps DDS generation behavior but adds arbitrary PAK filenames,
Monkey Island 2 support, output directories, list/debug modes, classic-only
extraction, safer path handling, and more robust filename table parsing.

License note: at the time this README was updated, the upstream
`timfel/monkey` repository did not show a `LICENSE` file in its root listing.
Because of that, the original upstream code should be treated as having no
explicit open-source license unless the upstream author publishes one. See
[NOTICE](NOTICE) for attribution and licensing notes.

This repository includes an MIT License for the local modifications and
documentation. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
