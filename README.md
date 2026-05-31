# SCUMMKit

Native toolkit for building, inspecting and modifying classic LucasArts SCUMM
game resources.

SCUMMKit is an extraction, inspection, patching, and talkie generation toolkit
for LucasArts SCUMM games. Its current native build pipeline replaces the
Windows-only Ultimate Talkie Edition toolchains for the Monkey Island Special
Edition games.

It builds ScummVM-compatible Talkie Editions from assets that you already own.
No game data is shipped in this repository. The project automates extraction,
patching, audio processing, resource inspection, and resource packing with
native command line tools and a Python CLI.

Supported games:

- The Secret of Monkey Island: Special Edition
- Monkey Island 2 Special Edition: LeChuck's Revenge

The original `extractpak` utility is still included for inspecting and
extracting Special Edition `.pak` archives directly.

## Why SCUMMKit?

The project started as a Monkey Island PAK extraction experiment and evolved
into a complete toolkit for building and inspecting SCUMM resources.

The name reflects the broader scope beyond Talkie Edition generation:
SCUMMKit is intended to be useful for extraction, inspection, patching, and
resource-building workflows around classic LucasArts SCUMM games.

## Features

- Native PAK extraction for `Monkey1.pak` and `monkey2.pak`
- Native XACT wave bank (`.xwb`) inspection and extraction
- Native ScummVM speech archive generation
- SCUMM resource inspection commands
- Native replacements for `build_monster.exe`, MI1 `wav2sbl.exe`, and the MI1
  `scummpacker.exe` SBL injection flow
- Native MI1 music conversion using `vgmstream-cli` and SoX
- Native MI1 SBL sound-effect injection
- Python CLI: `python3 -m scummkit`
- Automated pytest coverage for CLI parsing, monster archive packing, XWB
  parsing, and SBL generation
- Compatibility shell scripts retained under `scripts/`

## Legal Notes

This project does not include, distribute, or generate copyrighted game assets
by itself.

You must provide:

- Your own legally owned copies of the Monkey Island Special Edition games.
- The `.pak` and `audio/` files extracted from those games.
- The original Ultimate Talkie Edition builder files for the game you want to
  build.

SCUMMKit only automates the local build process. The generated output
folder contains LucasArts/Disney game assets derived from your installation and
must not be redistributed.

## Quick Start

Build Monkey Island 1:

```bash
python3 -m scummkit build mi1 \
  --pak ~/Downloads/MonkeyIsland/Monkey1.pak \
  --builder ~/Downloads/MI1_Ultimate_Talkie_Edition_Builder \
  --out ~/Downloads/ScummVM/MI1_Ultimate_Talkie_Edition \
  --audio ogg \
  --music hybrid \
  --verbose
```

Build Monkey Island 2:

```bash
python3 -m scummkit build mi2 \
  --pak ~/Downloads/MonkeyIsland2/app/monkey2.pak \
  --builder ~/Downloads/MI2_Ultimate_Talkie_Edition_Builder \
  --out ~/Downloads/ScummVM/MI2_Ultimate_Talkie_Edition \
  --audio ogg \
  --verbose
```

Add the generated output folder to ScummVM, not the original Special Edition
installation folder.

## Setup

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

4. Verify the Python package:

   ```bash
   python3 -m py_compile scummkit/*.py
   python3 -m pytest
   ```

### Tool Requirements

- Python 3.9 or newer: runs the `scummkit` package and tests.
- `bspatch`: applies the Ultimate Talkie binary patch files.
- `ffmpeg`: decodes WMA/XWMA sound-effect entries where needed.
- `sox`: performs the trim, mix, gain, pad, and audio conversion operations
  ported from the builder batch files.
- `vgmstream-cli`: decodes MI1 XACT music banks correctly.
- `clang`: optional but recommended; used to compile `extractpak.c`.

Audio encoder support:

- Ogg Vorbis: SoX with Ogg support, `oggenc`, or `ffmpeg`.
- FLAC: `flac` or `ffmpeg`.
- MP3: `lame` or `ffmpeg`.

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

Extract Monkey Island 2 Special Edition:

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

## Supported Games

| Game | Status | Notes |
| --- | --- | --- |
| The Secret of Monkey Island | Complete | Speech, music, SBL, ambience, and root soundtrack selection. Ogg is the validated native output mode. |
| Monkey Island 2: LeChuck's Revenge | Complete | Speech and music/resource support through the patched ScummVM game output. Ogg is the primary validated speech archive output; FLAC/MP3 use the same compressed archive path when encoders are available. |

## Building Monkey Island 1

```bash
python3 -m scummkit build mi1 \
  --pak ~/Downloads/MonkeyIsland/Monkey1.pak \
  --builder ~/Downloads/MI1_Ultimate_Talkie_Edition_Builder \
  --out ~/Downloads/ScummVM/MI1_Ultimate_Talkie_Edition \
  --audio ogg \
  --music hybrid \
  --verbose
```

Required inputs:

- `Monkey1.pak`
- `audio/Speech.xwb`
- `audio/SFXNew.xwb`
- `audio/MusicOriginal.xwb`
- `audio/MusicNew.xwb`
- `audio/Ambience.xwb`
- `MI1_Ultimate_Talkie_Edition_Builder/tools/patch10.000`
- `MI1_Ultimate_Talkie_Edition_Builder/tools/patch10.001`
- `MI1_Ultimate_Talkie_Edition_Builder/tools/monster.tbl`

Options:

- `--pak PATH`: path to `Monkey1.pak`.
- `--builder PATH`: path to the extracted MI1 Ultimate Talkie builder folder.
- `--out PATH`: output folder to create.
- `--audio ogg|flac|mp3`: target compressed speech format. MI1 is validated
  for `ogg`.
- `--music cd|hybrid|se`: root soundtrack selection. Default: `hybrid`.
- `--skip-sbl`: skip native SBL sound-effect injection.
- `--skip-music`: skip music conversion and root soundtrack copying.
- `--dry-run`: print planned steps without writing final output.
- `--verbose`: print detailed processing and root soundtrack mapping output.

Expected output:

```text
monkey.000
monkey.001
monkey.sog
readme.txt
track*.ogg
cd_music_ogg/*.ogg
se_music_ogg/*.ogg
music-root-map.txt
.work/
```

### MI1 Music Modes

`--music cd`

- Root `track*.ogg` files come only from `cd_music_ogg/`.
- This is the classic CD soundtrack path.

`--music hybrid` default

- Root `track*.ogg` files start from `cd_music_ogg/`.
- `se_music_ogg/track25.ogg` through `track29.ogg` are copied over the root
  output.
- This preserves the current default behavior and mirrors the original
  builder's optional extended-environment root-track workflow.

`--music se`

- Root `track*.ogg` files come from `se_music_ogg/`.
- This uses the full Special Edition soundtrack.
- This includes the SCUMM Bar chatter ambience, because the chatter is mixed
  into the SE `track8.ogg`.

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
  --builder ~/Downloads/MI2_Ultimate_Talkie_Edition_Builder \
  --out ~/Downloads/ScummVM/MI2_Ultimate_Talkie_Edition \
  --audio ogg \
  --verbose
```

Required inputs:

- `monkey2.pak`
- `audio/Speech.xwb`
- `audio/Patch.xwb`
- `MI2_Ultimate_Talkie_Edition_Builder/tools/patch02.000`
- `MI2_Ultimate_Talkie_Edition_Builder/tools/patch02.001`
- `MI2_Ultimate_Talkie_Edition_Builder/tools/monster.tbl`

Options:

- `--pak PATH`: path to `monkey2.pak`.
- `--builder PATH`: path to the extracted MI2 Ultimate Talkie builder folder.
- `--out PATH`: output folder to create.
- `--audio ogg|flac|mp3`: target compressed speech format. Ogg is the primary
  validated target.
- `--dry-run`: print planned steps without writing final output.
- `--verbose`: print detailed processing output.

Expected output:

```text
monkey2.000
monkey2.001
monkey2.sog
readme.txt
.work/
```

For FLAC or MP3, the speech archive is named `monkey2.sof` or `monkey2.so3`.

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

SCUMMKit replaces a chain of Windows batch files and Windows executables
with native code and common command line tools.

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
`Monkey1.pak`, applies Ultimate Talkie patches with `bspatch`, processes speech
from `Speech.xwb`, packs `monkey.sog`, injects SBL sound-effect resources, and
generates the selected soundtrack set.

For MI2, it extracts the classic SCUMM resource files from `monkey2.pak`,
applies the Ultimate Talkie patches, processes `Speech.xwb` and `Patch.xwb`,
and packs the ScummVM speech archive.

## Reference: Files and Formats

- `monkey.sog`: MI1 ScummVM compressed speech archive for Ogg Vorbis speech.
- `monkey2.sog`: MI2 ScummVM compressed speech archive for Ogg Vorbis speech.
- `monkey.sof` / `monkey2.sof`: FLAC variants of the compressed speech archive.
- `monkey.so3` / `monkey2.so3`: MP3 variants of the compressed speech archive.
- `monster.sou`: raw/WAV speech archive name used by classic SCUMM talkie
  games; native raw generation is not currently implemented.
- `monster.tbl`: table from the Ultimate Talkie builders mapping original
  script offsets to speech sample names. SCUMMKit uses it to decide which
  processed samples belong in the ScummVM archive.
- `SBL resources`: MI1 sound resources used for high-quality sound effects.
  The original builder generated them with `wav2sbl.exe` and injected them with
  `scummpacker.exe`; SCUMMKit implements that path natively.
- `patch10.000` / `patch10.001`: MI1 binary patches for classic SCUMM resource
  files.
- `patch02.000` / `patch02.001`: MI2 binary patches for classic SCUMM resource
  files.
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
python3 -m pytest
```

The tests cover CLI parsing, dry-run behavior, `monster.tbl` parsing, ScummVM
monster archive build and verification with tiny fake samples, XWB parser
behavior, and SBL conversion with generated WAV data.

For syntax-only validation:

```bash
python3 -m py_compile scummkit/*.py
```

## Project History

This repository started as a modernization of `extractpak.c`, an old utility
for extracting Monkey Island Special Edition `.pak` archives. It grew into a
native Python toolchain for building local Ultimate Talkie Edition folders
without Wine, Windows batch files, or opaque Windows-only executables.

## Known Limitations

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
- The shell scripts remain for compatibility, but new orchestration should use
  `python3 -m scummkit`.

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

- The correct Ultimate Talkie builder folder was passed with `--builder`.
- `monster.tbl` exists under the builder `tools/` directory.
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

### Unsupported Builder Files

The native builders expect the known Ultimate Talkie builder layouts and patch
file names. If a future builder release changes file names, patch versions, or
batch logic, SCUMMKit may need updates. The analysis notes in `docs/`
record the behavior currently implemented.

## Credits

- ScummVM, for preserving and documenting the runtime behavior these builds
  target.
- The Ultimate Talkie Edition authors, for the original builder logic and
  patches.
- vgmstream, for reliable game-audio bank decoding.
- FFmpeg, for broad audio decoding support.
- SoX, for precise audio processing.
- The original `extractpak.c` work in
  [timfel/monkey](https://github.com/timfel/monkey), which this repository
  builds on.

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
