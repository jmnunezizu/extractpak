# extractpak

`extractpak` extracts files from the `.pak` archives used by the Monkey Island
Special Edition releases.

Tested with:

- [The Secret of Monkey Island(TM): Special Edition](https://www.gog.com/en/game/the_secret_of_monkey_island_special_edition)
- [Monkey Island(TM) 2 Special Edition: LeChuck's Revenge(TM)](https://www.gog.com/en/game/monkey_island_2_special_edition_lechucks_revenge)

## Build

On macOS or Linux with Clang installed:

```bash
clang extractpak.c -o extractpak
```

## Extract the GOG Installers First

If you downloaded the Windows installers from GOG, extract the installer contents
with `innoextract` before running `extractpak`.

Install `innoextract` on macOS with Homebrew:

```bash
brew install innoextract
```

Extract The Secret of Monkey Island: Special Edition installer:

```bash
innoextract -d MonkeyIsland setup_the_secret_of_monkey_islandtm_special_edition_1.0_\(18587\).exe
```

Extract Monkey Island 2 Special Edition: LeChuck's Revenge installer:

```bash
innoextract -d MonkeyIsland2 setup_monkey_island2_se_2.0.0.10.exe
```

After extraction, the `.pak` files are typically available at:

```text
MonkeyIsland/Monkey1.pak
MonkeyIsland2/app/monkey2.pak
```

## Usage

List archive entries without extracting:

```bash
./extractpak --list <pak file>
```

Extract the full archive into the current directory:

```bash
./extractpak <pak file>
```

Extract the full archive into a specific output directory:

```bash
./extractpak <pak file> <output_dir>
```

Extract only matching entries:

```bash
./extractpak --only <text> <pak file> [output_dir]
```

Show parser diagnostics for classic game data entries:

```bash
./extractpak --debug-classic <pak file>
```

## The Secret of Monkey Island: Special Edition

Example GOG archive path:

```bash
~/Downloads/MonkeyIsland/Monkey1.pak
```

List files:

```bash
./extractpak --list ~/Downloads/MonkeyIsland/Monkey1.pak
```

Extract everything:

```bash
./extractpak ~/Downloads/MonkeyIsland/Monkey1.pak monkey1-extracted
```

Extract only the classic SCUMM data files:

```bash
./extractpak --only classic/en ~/Downloads/MonkeyIsland/Monkey1.pak monkey1-classic
```

This should extract:

```text
classic/en/monkey1.000
classic/en/monkey1.001
```

## Monkey Island 2 Special Edition: LeChuck's Revenge

Example GOG archive path:

```bash
~/Downloads/MonkeyIsland2/app/monkey2.pak
```

List files:

```bash
./extractpak --list ~/Downloads/MonkeyIsland2/app/monkey2.pak
```

Extract everything:

```bash
./extractpak ~/Downloads/MonkeyIsland2/app/monkey2.pak monkey2-extracted
```

Extract only the classic SCUMM data files:

```bash
./extractpak --only classic/en ~/Downloads/MonkeyIsland2/app/monkey2.pak monkey2-classic
```

This should extract:

```text
classic/en/monkey2.000
classic/en/monkey2.001
```

## Building Monkey Island 2 Ultimate Talkie Edition on macOS/Linux

This repo includes an experimental native helper for inspecting and reproducing
the Windows Monkey Island 2 Ultimate Talkie Edition builder without
Wine or `.bat` execution.

The helper is intentionally conservative. It currently performs the native
steps that are understood and testable:

- validates the Special Edition and builder inputs
- extracts `classic/en/monkey2.000` and `classic/en/monkey2.001` from
  `monkey2.pak` with `extractpak`
- patches those SCUMM resource files with native `bspatch`
- extracts WAV files from `Speech.xwb` and `Patch.xwb`
- processes the `voice.bat` SoX trim/mix steps and converts samples for the
  selected audio mode
- builds an experimental ScummVM compressed speech archive for Ogg, FLAC, or MP3
- copies the builder README into the output folder

Analysis of the Windows builder is documented in
[docs/mi2-ultimate-talkie-builder-analysis.md](docs/mi2-ultimate-talkie-builder-analysis.md).

Prerequisites:

- `clang`, to build `extractpak`
- `bspatch`; macOS includes `/usr/bin/bspatch`
- `python3`, for the native XWB extractor
- `sox`, for `voice.bat` trim/mix and sample conversion
- the Monkey Island 2 Special Edition install, including:
  - `monkey2.pak`
  - `audio/Speech.xwb`
  - `audio/Patch.xwb`
- the extracted `MI2_Ultimate_Talkie_Edition_Builder` folder

Audio mode tools:

- `raw`: `sox`; archive packing is still TODO
- `ogg`: `sox` with Ogg support, `oggenc`, or `ffmpeg`
- `flac`: `flac` or `ffmpeg`
- `mp3`: `lame` or `ffmpeg`

Ogg is the first validated target. FLAC and MP3 use the same compressed ScummVM
container layout, but have not been tested as thoroughly. Raw `monster.sou`
generation is still TODO.

Build `extractpak` first:

```bash
clang extractpak.c -o extractpak
```

Preferred Python CLI:

```bash
python3 -m talkiebuilder build mi2 \
  --pak ~/Downloads/MonkeyIsland2/app/monkey2.pak \
  --builder ~/Downloads/MI2_Ultimate_Talkie_Edition_Builder \
  --out ~/Downloads/ScummVM/MI2_Ultimate_Talkie_Edition \
  --audio ogg \
  --verbose
```

Preview the native build steps without writing output:

```bash
python3 -m talkiebuilder build mi2 \
  --pak ~/Downloads/MonkeyIsland2/app/monkey2.pak \
  --builder ~/Downloads/MI2_Ultimate_Talkie_Edition_Builder \
  --out ~/Downloads/ScummVM/MI2_Ultimate_Talkie_Edition \
  --audio ogg \
  --dry-run \
  --verbose
```

The older shell entry point is still kept for compatibility:

```bash
scripts/build-mi2-talkie.sh \
  --pak ~/Downloads/MonkeyIsland2/app/monkey2.pak \
  --builder ~/Downloads/MI2_Ultimate_Talkie_Edition_Builder \
  --out ~/Downloads/ScummVM/MI2_Ultimate_Talkie_Edition \
  --audio ogg \
  --verbose
```

Expected current output:

```text
monkey2.000
monkey2.001
readme.txt
.work/speech-wav/*.wav
.work/patch-wav/*.wav
.work/processed-voice/final-ogg/*.ogg
monkey2.sog
```

The complete talkie build needs one generated speech resource:

```text
monkey2.sof  # FLAC
monkey2.sog  # Ogg Vorbis, experimental native support
monkey2.so3  # MP3
monster.sou  # raw DOS speech
```

The native helper currently generates the compressed ScummVM archive directly
from `monster.tbl` and the processed samples. It packs only samples referenced by
`monster.tbl` and warns about extra generated sample files.

ScummVM instructions:

Add the output folder in ScummVM as the game directory.

Legal note: you must own Monkey Island 2 Special Edition and provide your own
game files. This repository does not distribute LucasArts game assets or built
Ultimate Talkie output files.

## Building Monkey Island 1 Ultimate Talkie Edition on macOS/Linux

This repo also includes a full experimental native Ogg helper for The Secret of
Monkey Island Ultimate Talkie Edition.

Current status:

- extracts and patches `classic/en/monkey1.000` / `monkey1.001` into `monkey.000` / `monkey.001`
- extracts `Speech.xwb` and `SFXNew.xwb`, including WMA entries through `ffmpeg`
- processes the MI1 `voice.bat` sample edits
- builds `monkey.sog`
- converts classic CD music and Special Edition music/ambience to Ogg
- injects the `sbl.bat` high quality sound effects natively
- preserves a pre-SBL backup under `.work/sbl/pre-sbl`

Analysis is documented in
[docs/mi1-ultimate-talkie-builder-analysis.md](docs/mi1-ultimate-talkie-builder-analysis.md).

Prerequisites:

- `clang`, to build `extractpak`
- `bspatch`; macOS includes `/usr/bin/bspatch`
- `python3`
- `sox` with Ogg/Vorbis write support
- `ffmpeg`, for WMA/XWMA SFX decoding
- `vgmstream-cli`, for MI1 XACT music-bank decoding
- the Monkey Island Special Edition install, including `Monkey1.pak` and the `audio/` XWB files
- the extracted `MI1_Ultimate_Talkie_Edition_Builder` folder

Preferred Python CLI:

```bash
python3 -m talkiebuilder build mi1 \
  --pak ~/Downloads/MonkeyIsland/Monkey1.pak \
  --builder ~/Downloads/MI1_Ultimate_Talkie_Edition_Builder \
  --out ~/Downloads/ScummVM/MI1_Ultimate_Talkie_Edition \
  --audio ogg \
  --verbose
```

The older shell entry point is still kept for compatibility:

```bash
scripts/build-mi1-talkie.sh \
  --pak ~/Downloads/MonkeyIsland/Monkey1.pak \
  --builder ~/Downloads/MI1_Ultimate_Talkie_Edition_Builder \
  --out ~/Downloads/ScummVM/MI1_Ultimate_Talkie_Edition \
  --audio ogg \
  --verbose
```

Expected output:

```text
monkey.000
monkey.001
monkey.sog
track*.ogg
readme.txt
cd_music_ogg/*.ogg
se_music_ogg/*.ogg
```

Optional flags:

- `--skip-sbl`: skip native SBL sound-effect injection.
- `--skip-music`: skip CD/SE music conversion.

The Ogg path now runs without Wine: patched resources, speech archive, native
SBL injection, and music are generated locally. The SBL injector verifies the
rebuilt SCUMM resource structure and reports SHA256 values for the pre/post
resource files. For a directly usable ScummVM folder, the root `track*.ogg`
files use classic CD music tracks plus the Special Edition extended ambience
tracks `25`-`29`, matching the Windows builder's optional root-track workflow.
The `cd_music_ogg/` and `se_music_ogg/` folders are still kept for comparison
or manual music selection through ScummVM extra paths.

Resource inspection helpers:

```bash
python3 -m talkiebuilder inspect mi1 resources --game-dir /tmp/mi1-test
python3 -m talkiebuilder inspect mi1 room --game-dir /tmp/mi1-test --room 41
python3 -m talkiebuilder inspect mi1 resource --game-dir /tmp/mi1-test --room 41 --id 71
```

ScummVM instructions:

Add the output folder in ScummVM as the game directory.

Legal note: you must own The Secret of Monkey Island Special Edition and provide
your own game files. This repository does not distribute LucasArts game assets
or built Ultimate Talkie output files.

## Notes

- Full extraction also writes `.dds` files for `.dxt` assets.
- DDS generation is disabled when extracting `--only classic/en`, because the
  classic `.000` and `.001` files are not DXT texture assets.
- Archive entries that start with `/` are written as relative paths.
- Empty archive entry names are skipped.
- If an output file cannot be written, extraction continues and reports the
  failure count at the end.

At the end of extraction, the tool prints:

```text
Extracted X files
Skipped Y entries
Failed Z files
```

## Parser Limitations

The parser is intentionally small and assumes the archive format used by these
two Special Edition releases:

- It assumes little-endian archive fields.
- It assumes file entries are stored uncompressed when `flags/type` is `0`.
- It does not validate every archive offset and size against the physical file
  length before reading.
- It strips leading `/` characters, but it does not otherwise sandbox paths such
  as entries containing `..`.

## Origin and Attribution

This utility is modified from the original `extractpak.c` in
[timfel/monkey](https://github.com/timfel/monkey), a small GitHub repository for
working with Monkey Island Special Edition `.pak` files.

The upstream repository README describes:

- `extractpak`, for extracting files from `Monkey1.pak`
- `packpak`, for replacing files in `Monkey1.pak`
- DDS output for extracted `.dxt` texture assets

This version keeps the DDS generation behavior but adds support for arbitrary
pak filenames, Monkey Island 2 Special Edition, output directories, list/debug
modes, classic-only extraction, safer path handling, and more robust filename
table parsing.

License note: at the time this README was updated, the upstream
`timfel/monkey` repository did not show a `LICENSE` file in its root listing.
Because of that, the original upstream code should be treated as having no
explicit open-source license unless the upstream author publishes one. See
[NOTICE](NOTICE) for attribution and licensing notes.

## License

This repository includes an MIT License for the local modifications and
documentation. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
