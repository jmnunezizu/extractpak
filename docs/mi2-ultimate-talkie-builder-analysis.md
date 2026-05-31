# Monkey Island 2 Ultimate Talkie Builder Analysis

Source inspected:

```text
~/Downloads/MI2_Ultimate_Talkie_Edition_Builder
```

The Windows builder is a batch-driven pipeline for creating "Monkey Island 2:
LeChuck's Revenge - Ultimate Talkie Edition" from a legally installed Monkey
Island 2 Special Edition. It does not modify the original Special Edition files.

## Expected Inputs

The builder expects to live next to the Special Edition install data:

```text
monkey2.pak
audio/Patch.xwb
audio/Speech.xwb
```

In this native tooling, `monkey2.pak` is passed explicitly with `--pak`, and the
audio directory is inferred from the pak's parent directory.

The builder folder must contain:

```text
install.bat
install_flac.bat
install_ogg.bat
readme.txt
tools/
```

Important files under `tools/`:

```text
MI2_ResExtract.exe
BSPATCH.EXE
build_monster.exe
unxwb.exe
ffmpeg.exe
sox.exe
7z.exe
fatecd.exe
dottcd.exe
patch01.ex_
patch02.000
patch02.001
patch05.im_
monster.tbl
_cdt_silence
voice.bat
wav.bat
flac.bat
ogg.bat
mp3.bat
```

## Expected Outputs

The Windows builder writes:

```text
MI2_Ultimate_Talkie_Edition/readme.txt
MI2_Ultimate_Talkie_Edition/monkey2.000
MI2_Ultimate_Talkie_Edition/monkey2.001
MI2_Ultimate_Talkie_Edition/monkey2.sof  # FLAC ScummVM speech resource
MI2_Ultimate_Talkie_Edition/monkey2.sog  # Ogg Vorbis ScummVM speech resource
MI2_Ultimate_Talkie_Edition/monkey2.so3  # MP3 ScummVM speech resource
MI2_Ultimate_Talkie_Edition/monster.sou  # uncompressed DOS speech resource
MI2_Ultimate_Talkie_Edition/monkey2.exe  # patched DOS executable
MI2_Ultimate_Talkie_Edition/*.ims        # DOS audio drivers
```

For ScummVM, the key outputs are the patched `monkey2.000`,
`monkey2.001`, and one speech resource matching the selected audio mode:
`monkey2.sof`, `monkey2.sog`, `monkey2.so3`, or `monster.sou`.

## Batch Workflow

The main entry point is `install.bat`. `install_flac.bat` calls:

```bat
install.bat flac
```

`install_ogg.bat` calls:

```bat
install.bat ogg
```

`install.bat` then:

1. Checks that `..\monkey2.pak` exists.
2. Checks that `..\audio\Patch.xwb` exists.
3. Creates `MI2_Ultimate_Talkie_Edition`.
4. Copies `readme.txt` into the output folder.
5. Calls `tools\voice.bat`.
6. Extracts classic resources from the Special Edition and patches them:
   - `MI2_ResExtract ..\..\ .`
   - `bspatch Monkey2.000 monkey2t.000 patch02.000`
   - `bspatch Monkey2.001 monkey2t.001 patch02.001`
   - copies patched files as `monkey2.000` and `monkey2.001`
7. Calls the selected audio mode batch file:
   - `wav.bat 22050`
   - `flac.bat 22050`
   - `ogg.bat 22050`
   - `mp3.bat 22050`
8. Copies the generated speech resource to the output folder.
9. Builds DOS support files by extracting and patching files from `fatecd.exe`
   and `dottcd.exe`.

## Extraction Steps

The original builder uses `MI2_ResExtract.exe` to produce:

```text
Monkey2.000
Monkey2.001
```

The native repo already has `extractpak`, which can extract the same Special
Edition classic files from `monkey2.pak`:

```text
classic/en/monkey2.000
classic/en/monkey2.001
```

The native helper uses this existing extractor instead of rewriting archive
parsing.

## Voice Processing and Audio Conversion Steps

`voice.bat` does the voice sample preparation:

1. Creates `tools\samples`.
2. Runs `unxwb.exe` on:
   - `..\..\audio\Speech.xwb`
   - `..\..\audio\Patch.xwb`
3. Re-encodes each extracted WAV with `ffmpeg.exe` into `samples\`.
4. Uses `sox.exe` to trim and combine special case samples.
5. Copies `_cdt_silence` as `_cdt_silence.wav`.

The exact special-case SoX pipeline is:

```bat
sox -r 42777 000003d5.wav -D -c 1 -t wav -V0 temp1.wav trim 2.866 1.230
sox temp1.wav -r 48016 -D -c 1 -t wav -V0 temp2.wav
sox 000003d5.wav -D -c 1 -t wav -V0 temp1.wav trim 0.000 2.553
sox temp1.wav temp2.wav _cdt_parlay.wav
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_arm_con1.wav trim 71.881 2.073
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_hea_con1.wav trim 10.943 2.059
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_hip_con1.wav trim 31.281 2.020
sox vx112_DemBones_SE_nl_2.wav -D -c 1 -t wav -V0 _cdt_leg_con1.wav trim 31.257 2.075
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_rip_con1.wav trim 79.304 2.056
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_arm_bone.wav trim 33.536 1.098
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_hea_bone.wav trim 74.208 1.178
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_hip_bone.wav trim 20.673 1.184
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_leg_bone.wav trim 53.883 1.245
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_rip_bone.wav trim 40.999 1.161
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_arm_con2.wav trim 34.994 2.068
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_hea_con2.wav trim 75.610 2.099
sox vx112_DemBones_SE_nl_2.wav -D -c 1 -t wav -V0 _cdt_hip_con2.wav trim 35.005 2.051
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_leg_con2.wav trim 55.252 2.110
sox vx112_DemBones_SE_nl_1.wav -D -c 1 -t wav -V0 _cdt_rip_con2.wav trim 14.655 2.009
copy ..\_cdt_silence _cdt_silence.wav
```

Observed operation types:

- trim: all `_cdt_*` derived voice fragments use `trim start length`.
- combine: `_cdt_parlay.wav` is created by passing `temp1.wav` and
  `temp2.wav` as inputs to `sox`.
- sample-rate override/conversion: `_cdt_parlay.wav` first treats
  `000003d5.wav` as 42777 Hz for one segment, then writes a 48016 Hz temporary
  file before combining.
- channel conversion: all special SoX outputs request mono with `-c 1`.
- file copy/rename: `_cdt_silence` is copied to `_cdt_silence.wav`.
- cleanup: `temp1.wav` and `temp2.wav` are deleted after use.

No pad, gain, or volume operations appear in `voice.bat`.

The generated special samples are:

```text
_cdt_parlay.wav
_cdt_arm_con1.wav
_cdt_hea_con1.wav
_cdt_hip_con1.wav
_cdt_leg_con1.wav
_cdt_rip_con1.wav
_cdt_arm_bone.wav
_cdt_hea_bone.wav
_cdt_hip_bone.wav
_cdt_leg_bone.wav
_cdt_rip_bone.wav
_cdt_arm_con2.wav
_cdt_hea_con2.wav
_cdt_hip_con2.wav
_cdt_leg_con2.wav
_cdt_rip_con2.wav
_cdt_silence.wav
```

The selected output mode then converts `samples\*.wav`:

- `wav.bat`: `sox` to 22050 Hz, 8-bit, mono WAV, then `build_monster wav`.
- `flac.bat`: `sox` to FLAC, then `build_monster flac`.
- `ogg.bat`: `sox` to Ogg Vorbis, then `build_monster ogg`.
- `mp3.bat`: `sox` to MP3, then `build_monster mp3`.

The native `scummkit.voices` module now reproduces the `voice.bat` sample
normalisation, the special-case SoX commands above, and the selected sample
conversion step. It writes processed files under:

```text
.work/processed-voice/final-raw/
.work/processed-voice/final-flac/
.work/processed-voice/final-ogg/
.work/processed-voice/final-mp3/
```

These files are the inputs that a future native `build_monster` replacement
will need to pack into `monster.sou`, `monkey2.sof`, `monkey2.sog`, or
`monkey2.so3`.

## build_monster Inputs and Outputs

The Windows batch files invoke `build_monster.exe` with one positional argument:

```bat
build_monster wav
build_monster flac
build_monster ogg
build_monster mp3
```

`install.bat` expects these intermediate files from `build_monster.exe`:

```text
monster.sou  -> MI2_Ultimate_Talkie_Edition/monster.sou
monkey.sof   -> MI2_Ultimate_Talkie_Edition/monkey2.sof
monkey.sog   -> MI2_Ultimate_Talkie_Edition/monkey2.sog
monkey.so3   -> MI2_Ultimate_Talkie_Edition/monkey2.so3
```

`monster.tbl` is an ASCII CRLF table. Each non-empty line is:

```text
8 lowercase hex digits for the original VCTL offset
sample basename without extension
```

Example:

```text
00000008000016a7
0005b444_cdt_silence
```

The inspected table has 6808 lines, 6808 unique original offsets, and 6808
unique sample basenames. The processed sample folder currently contains 7204
files, so `build_monster.exe` appears to pack only samples referenced by
`monster.tbl` and ignore extra generated files.

## ScummVM Compressed Speech Archive Format

ScummVM's `compress_scumm_sou` tool and SCUMM engine source describe the
compressed `.so3`, `.sog`, and `.sof` container used for classic SCUMM speech.
The format is:

```text
uint32be index_size
index entries, index_size bytes total
packed data bytes
```

Each index entry is 16 bytes:

```text
uint32be original_vctl_offset
uint32be data_offset_relative_to_packed_data_start
uint32be mouth_sync_tag_byte_count
uint32be compressed_audio_byte_count
```

The packed data region stores, for each index entry:

```text
mouth_sync tag bytes
compressed audio payload
```

At runtime ScummVM reads `index_size`, loads `index_size / 16` entries, binary
searches by `original_vctl_offset`, adds `index_size + 4` to the relative data
offset, skips `mouth_sync_tag_byte_count` bytes, and decodes
`compressed_audio_byte_count` bytes using the archive mode:

```text
.sog -> Ogg Vorbis
.sof -> FLAC
.so3 -> MP3
```

`monster.tbl` does not include mouth-sync tag bytes. The native packer therefore
writes `mouth_sync_tag_byte_count = 0` for every entry. ScummVM may warn if the
patched game resource provides a non-zero VCTL length for a line, but it will use
the tag count from the compressed archive entry.

Native status:

- `scummkit.monster` implements deterministic `.sog`, `.sof`, and
  `.so3` packing from `monster.tbl` plus processed samples.
- It packs only referenced samples, warns for missing referenced samples, warns
  for unreferenced sample files, and validates archive offsets.
- Raw `monster.sou` generation is not implemented yet. That requires creating
  an uncompressed SOU/VCTL/VTLK stream, not the compressed ScummVM index format.

## XWB Format Findings

`Speech.xwb` and `Patch.xwb` both start with the `WBND` signature and use
Microsoft XACT wave bank layout:

```text
Speech.xwb:
  magic: WBND
  tool version: 46
  format version: 44
  bank name: Speech
  entries: 7157
  entry metadata size: 24
  entry name size: 64
  alignment: 2048
  names segment: absent

Patch.xwb:
  magic: WBND
  tool version: 46
  format version: 44
  bank name: Patch
  entries: 30
  entry metadata size: 24
  entry name size: 64
  alignment: 2048
  names segment: present
```

The 24-byte entry records match XACT full entry metadata:

```text
flags + duration
mini wave format
play region offset
play region length
loop start
loop length
```

The mini wave formats in the inspected files are ADPCM (`tag = 2`). The raw
payloads are Microsoft ADPCM (`WAVE_FORMAT_ADPCM`, format code `0x0002`), but
the XACT mini-format block-align value must be expanded before writing the RIFF
WAV header:

```text
samples_per_block = xact_block_align * 2 + 32
wav_block_align   = (xact_block_align + 22) * channels
```

`Patch.xwb` has fixed-width entry names such as:

```text
mx112_SE_DemBones_nl
vx112_DemBones_SE_nl_1
CHF_97_jungleb_4_3
```

`Speech.xwb` has no names segment. The native extractor therefore writes
builder-compatible numeric names such as:

```text
00000000.wav
000003d5.wav
```

## Patching and Resource Generation

Native-equivalent step:

- `BSPATCH.EXE` can be replaced by `/usr/bin/bspatch` on macOS or the
  `bspatch` package on Linux.

Still Windows-only in the original builder:

- `MI2_ResExtract.exe`: replaced for classic file extraction by this repo's
  existing `extractpak`.
- `unxwb.exe`: replaced by `scummkit.xwb` for these XACT wave banks.
- `voice.bat`: replaced through processed sample generation by
  `scummkit.voices`.
- `build_monster.exe`: packs numbered speech samples into SCUMM speech
  resources (`monster.sou`, `monkey.sof`, `monkey.sog`, `monkey.so3`). A native
  replacement is still required.
- `7z.exe`: extracts files from `fatecd.exe` and `dottcd.exe` for DOS support.
  Native `7z` can likely replace this part.

## File Formats

- `monkey2.pak`: Special Edition archive.
- `monkey2.000`, `monkey2.001`: classic SCUMM game resource files.
- `Speech.xwb`, `Patch.xwb`: Special Edition XACT wave banks.
- `.wav`: intermediate decoded voice samples.
- `.flac`, `.ogg`, `.mp3`: encoded voice sample intermediates.
- `monster.sou`: uncompressed SCUMM speech resource.
- `monkey2.sof`: FLAC-compressed ScummVM speech resource.
- `monkey2.sog`: Ogg Vorbis-compressed ScummVM speech resource.
- `monkey2.so3`: MP3-compressed ScummVM speech resource.
- `.ims`: DOS sound drivers.

## Current Native Status

Implemented natively:

- Validate `monkey2.pak`, builder directory, patch files, and Special Edition
  audio inputs.
- Extract `classic/en/monkey2.000` and `classic/en/monkey2.001` with
  `extractpak`.
- Patch `monkey2.000` and `monkey2.001` with native `bspatch`.
- Extract ADPCM WAV files from `Speech.xwb` and `Patch.xwb` with
  `scummkit.xwb`.
- Copy builder `readme.txt` into the output directory.

Not yet implemented natively:

- SoX trimming/mixing of special case samples.
- Packing `monster.sou`, `monkey2.sof`, `monkey2.sog`, or `monkey2.so3`.
- DOS executable and `.ims` generation.
