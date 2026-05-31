# Monkey Island 1 Ultimate Talkie Builder Analysis

This note documents the Windows builder in:

```text
~/Downloads/MI1_Ultimate_Talkie_Edition_Builder
```

It is intended to guide a native macOS/Linux implementation. The current native support is deliberately partial and does not change the MI2 builder path.

## Builder Layout

Top-level entry points:

- `install.bat`: main builder, defaults to `wav 22050` when no mode is supplied.
- `install_ogg.bat`: calls `install.bat ogg`.
- `install_flac.bat`: calls `install.bat flac`.
- `extended_SE_tracks_to_game_folder.bat`: optional post-build move of five SE ambience/music tracks into the main output folder.

Tools and data under `tools/`:

- `extract_classic.exe`: extracts classic resources from `Monkey1.pak` into `monkey1.000` and `monkey1.001`.
- `BSPATCH.EXE`: applies binary patches.
- `patch10.000`, `patch10.001`: patch `monkey1.000` / `monkey1.001` to `monkey.000` / `monkey.001`.
- `patch05.ex_`, `patch05.im_`: DOS executable/driver patches used only for the raw WAV/DOS path.
- `voice.bat`: extracts and prepares speech/sound-effect samples.
- `sbl.bat`: injects high quality sound effects into SCUMM resources with `scummpacker.exe` and `wav2sbl.exe`.
- `cdaudio.bat`: extracts and converts CD music and Special Edition music/ambience tracks.
- `monster.tbl`: speech archive table.
- `build_monster.exe`: packs processed speech into `monster.sou`, `monkey.sof`, `monkey.sog`, or `monkey.so3`.
- Windows-only executables: `unxwb.exe`, `xWMAEncode.exe` (required but not bundled), `sox.exe`, `scummpacker.exe`, `wav2sbl.exe`, `build_monster.exe`, `7z.exe`, `fatecd.exe`, `dottcd.exe`.

## Expected Inputs

The Windows builder expects to be placed next to a Special Edition install:

```text
Monkey1.pak
audio/Speech.xwb
audio/SFXNew.xwb
audio/MusicOriginal.xwb
audio/MusicNew.xwb
audio/Ambience.xwb
MI1_Ultimate_Talkie_Edition_Builder/
```

It also requires `xWMAEncode.exe` in `tools/`; the readme says this is not bundled for legal reasons and comes from Microsoft's DirectX SDK.

For the native partial helper, the required inputs are:

```text
Monkey1.pak
audio/Speech.xwb
audio/SFXNew.xwb
tools/patch10.000
tools/patch10.001
```

The native music conversion additionally requires:

```text
audio/MusicOriginal.xwb
audio/MusicNew.xwb
audio/Ambience.xwb
```

## Expected Outputs

The Windows builder writes `MI1_Ultimate_Talkie_Edition/`.

Common ScummVM outputs:

- `monkey.000`
- `monkey.001`
- `readme.txt`
- one speech archive:
  - `monster.sou` for raw WAV mode
  - `monkey.sof` for FLAC mode
  - `monkey.sog` for Ogg mode
  - `monkey.so3` for MP3 mode

Music outputs:

- `cd_music_ogg/` or `cd_music_flac/` for classic CD music.
- `se_music_ogg/` or `se_music_flac/` for Special Edition music/ambience.
- The native CLI also copies a selected Ogg music set into the output root so
  the folder is directly usable in ScummVM. The default `--music hybrid` mode
  uses classic CD music tracks from `cd_music_ogg/`, plus Special Edition
  extended ambience tracks `25`-`29`.

DOS/raw-only outputs:

- `monkey.exe`
- patched `.ims` MIDI drivers copied from `fatecd.exe` / `dottcd.exe`.

The current native MI1 Ogg helper produces:

```text
monkey.000
monkey.001
monkey.sog
readme.txt
track*.ogg
cd_music_ogg/*.ogg
se_music_ogg/*.ogg
.work/speech-wav/*.wav
.work/sfxnew-wav/*.wav
.work/processed-voice/final-ogg/*.ogg
```

## Pipeline

### 1. Voice and Sample Extraction

`install.bat` calls `tools/voice.bat` before resource extraction/patching.

`voice.bat`:

1. Creates `samples/`.
2. Extracts:
   - `../../audio/SFXNew.xwb`
   - `../../audio/Speech.xwb`
3. Uses `unxwb.exe` to produce `.xwm` files.
4. Uses `xWMAEncode.exe` to convert every `.xwm` into `.wav`.
5. Moves all WAVs into the `tools/` working directory.
6. Copies `_cdt_silence` to `_cdt_silence.wav`.
7. Runs many SoX edits for special cases.

The special-case SoX pipeline includes:

- `trim` for Stan price fragments, Monkey Bride, door sounds, bubbles, hit sounds, and other one-off samples.
- `gain` for low-level or over-loud samples.
- `compand` after mixing some composite samples.
- `delay` before mixing `_cdt_rumjam`.
- `-m` mixing for composite lines/sound effects such as `_cdt_machine`, `_cdt_guykick1`, `_cdt_stankick`, `_cdt_jamrum`, and `_cdt_rumjam`.
- final replacement/renaming of some original samples:
  - `_cdt_eatya.wav` replaces `TRL_57_bridge_16_2.wav`
  - `_cdt_ht.wav` replaces `GUY_20_main-beach_71_3.wav`

Native status:

- `scummkit.xwb` can extract the PCM/ADPCM entries directly as WAV.
- For MI1, `python3 -m scummkit xwb --decode-wma` wraps XACT WMA payloads as RIFF/XWMA and decodes them with `ffmpeg`.
- `Speech.xwb` is fully PCM and extractable.
- `SFXNew.xwb` is mostly PCM but contains 55 WMA entries.
- 18 of those WMA entries are referenced by `monster.tbl`, so they are needed for a complete speech archive:
  - `04_sound_ADL_wood-machine`
  - `140_Fight_Stage_1_Intro`
  - `17_sound_SBL_explosion1`
  - `18_sound_SBL_explosion2`
  - `19_sound_SBL_explosion3`
  - `20_sound_SBL_explosion4`
  - `29_sound_SBL_cannon-noise`
  - `30_sound_ADL_fuse-noise`
  - `42_sound_SBL_dam-explosion`
  - `43_sound_SBL_vista-kaboom`
  - `45_sound_ADL_vista-whoosh`
  - `46_sound_SBL_vista-bloop`
  - `58_sound_SBL_ghost-cluck`
  - `58_sound_SBL_ghost-cluck_03`
  - `83_Chef-cry`
  - `83_Chef-cry_01`
  - `83_Chef-cry_02`
  - `83_Chef-cry_04`
- `scummkit.voices` ports the `voice.bat` SoX trim/mix/gain/compand/delay steps listed above.
- The native Ogg build encodes processed samples into `.work/processed-voice/final-ogg/`.

### 2. Classic Resource Extraction and Patching

`install.bat` extracts and patches resources:

```bat
extract_classic
bspatch monkey1.000 monkey.000 patch10.000
bspatch monkey1.001 monkey.001 patch10.001
```

Native equivalent:

```text
extractpak --only classic/en Monkey1.pak <work>
bspatch <work>/classic/en/monkey1.000 monkey.000 patch10.000
bspatch <work>/classic/en/monkey1.001 monkey.001 patch10.001
```

The native helper implements this part.

### 3. High Quality Sound-Effect Injection

After patching, `install.bat` calls:

```bat
call sbl 22050
copy Resource.000 ..\MI1_Ultimate_Talkie_Edition\monkey.000 /y
copy Resource.001 ..\MI1_Ultimate_Talkie_Edition\monkey.001 /y
```

`sbl.bat`:

1. Runs `scummpacker -e -g MI1` to unpack the patched SCUMM resources.
2. Uses SoX to convert/trim many sound effects to 8-bit mono WAV at the requested sample rate.
3. Uses `wav2sbl.exe` to convert each WAV into `000_SBL.dmp`.
4. Copies each `SBL.dmp` into specific extracted SCUMM resource paths.
5. Adds extra sound effects and subtitle logic.
6. Re-packs resources with `scummpacker`.

Command inventory from `tools/sbl.bat`:

- `scummpacker -e -g MI1`
- 71 SoX conversion commands using `-D -b 8 -c 1 -r %1 -t wav -V0 temp.wav`, usually with `trim`.
- 71 `wav2sbl temp.wav 000_SBL.dmp` conversions.
- 71 copies of `000_SBL.dmp` into `000_LECF/.../SOUN_.../000_SOU` paths.
- `scummpacker -p -g MI1`
- cleanup of `000_SBL.dmp`, `temp.wav`, `DOBJ.dmp`, `DROO.dmp`, `MAXS.dmp`, and `000_LECF/`.

The copied resources target existing sound chunks under rooms including `008_LFLF_sh-hull`, `010_LFLF_logo`, `011_LFLF_vista-1`, `014_LFLF_sh-galley`, `019_LFLF_sh-deck`, `025_LFLF_village`, `037_LFLF_meats-hou`, `041_LFLF_kitchen`, `045_LFLF_cu-church`, `053_LFLF_foyer`, `058_LFLF_damnfores`, `070_LFLF_hellcliff`, `075_LFLF_gh-hull`, and `088_LFLF_fighting`. The extra sound effects at the end of `sbl.bat` replace existing placeholder `SOUN` resources with IDs `170` through `178`.

Parsed `sbl.bat` commands:

- 01. `_cdt_bubble.wav` -> room `041`, sound `067` child 1; effects: `(none)`
- 02. `65_sound_SBL_hi-drip.wav` -> room `008`, sound `065` child 1; effects: `trim 0.002 0.557`
- 03. `63_sound_SBL_low-drip.wav` -> room `008`, sound `063` child 1; effects: `trim 0.011 0.376`
- 04. `64_sound_SBL_med-drip.wav` -> room `008`, sound `064` child 2; effects: `trim 0.119 0.961`
- 05. `_cdt_dooropen.wav` -> room `010`, sound `002`; effects: `(none)`
- 06. `_cdt_doorclose.wav` -> room `010`, sound `003`; effects: `(none)`

- 07. `1_sound_SBL_click.wav` -> room `010`, sound `001`; effects: `trim 0.000 0.017`
- 08. `43_sound_SBL_vista-kaboom.wav` -> room `011`, sound `043`; effects: `trim 0.000 1.680`
- 09. `44_sound_SBL_vista-rock-thud.wav` -> room `011`, sound `044`; effects: `trim 0.008 0.553`
- 10. `46_sound_SBL_vista-bloop.wav` -> room `011`, sound `046`; effects: `trim 0.000 2.000`
- 11. `28_sound_SBL_voodoo-bang.wav` -> room `014`, sound `028`; effects: `trim 0.000 1.566`
- 12. `31_sound_SBL_pot-splat.wav` -> room `014`, sound `031`; effects: `trim 0.014 0.547`
- 13. `42_sound_SBL_dam-explosion.wav` -> room `015`, sound `042`; effects: `trim 0.013 1.317`
- 14. `29_sound_SBL_cannon-noise.wav` -> room `019`, sound `029`; effects: `trim 0.000 2.000`
- 15. `30_sound_ADL_fuse-noise.wav` -> room `019`, sound `030`; effects: `trim 0.003 3.871`
- 16. `22_sound_SBL_whack.wav` -> room `025`, sound `022`; effects: `trim 0.000 0.212`
- 17. `77_sound_SBL_sound_77.wav` -> room `029`, sound `077`; effects: `trim 0.000 1.566`
- 18. `21_sound_SBL_bell.wav` -> room `030`, sound `021`; effects: `trim 0.000 1.164`
- 19. `47_sound_SBL_acid-bath.wav` -> room `031`, sound `047`; effects: `trim 0.050 1.870`
- 20. `8_sound_SBL_growl.wav` -> room `036`, sound `008`; effects: `trim 0.001 0.151`
- 21. `04_sound_ADL_wood-machine.wav` -> room `037`, sound `004`; effects: `trim 0.029 1.844`
- 22. `5_sound_ADL_cow-bell-1.wav` -> room `037`, sound `005`; effects: `trim 0.204 2.000`
- 23. `7_sound_SBL_door-squeek.wav` -> room `037`, sound `007`; effects: `trim 0.000 0.177`
- 24. `48_sound_ADL_running-water.wav` -> room `041`, sound `048`; effects: `trim 0.050 1.623`
- 25. `69_sound_SBL_plank-sound.wav` -> room `041`, sound `069`; effects: `trim 0.000 0.374`
- 26. `71_sound_SBL_seagull-cheep.wav` -> room `041`, sound `071`; effects: `trim 0.000 0.660`
- 27. `49_sound_SBL_door-knock.wav` -> room `043`, sound `049`; effects: `trim 0.000 0.170`
- 28. `17_sound_SBL_explosion1.wav` -> room `045`, sound `017` child 4; effects: `trim 0.000 1.613`
- 29. `18_sound_SBL_explosion2.wav` -> room `045`, sound `018` child 3; effects: `trim 0.004 1.735`
- 30. `19_sound_SBL_explosion3.wav` -> room `045`, sound `019` child 4; effects: `trim 0.006 0.735`
- 31. `20_sound_SBL_explosion4.wav` -> room `045`, sound `020` child 4; effects: `trim 0.007 1.828`
- 32. `9_sound_SBL_footstep_01.wav` -> room `048`, sound `009`; effects: `trim 0.000 0.089`
- 33. `10_sound_SBL_cable-noise.wav` -> room `048`, sound `010`; effects: `trim 0.000 4.141`
- 34. `12_sound_SBL_end-cable-noise.wav` -> room `048`, sound `012`; effects: `trim 0.001 0.222`
- 35. `61_sound_SBL_circus-explosion.wav` -> room `051`, sound `061`; effects: `trim 0.000 1.766`
- 36. `62_sound_SBL_circus-splat.wav` -> room `051`, sound `062`; effects: `trim 0.000 1.804`
- 37. `25_sound_SBL_zap_02.wav` -> room `053`, sound `025`; effects: `trim 0.000 0.216`
- 38. `26_sound_SBL_machine-gun.wav` -> room `053`, sound `026`; effects: `trim 0.025 0.824`
- 39. `13_sound_SBL_splat_02.wav` -> room `053`, sound `013`; effects: `trim 0.052 1.050`
- 40. `140_Fight_Stage_1_Intro.wav` -> room `053`, sound `033`; effects: `trim 0.044 4.756`
- 41. `34_sound_SBL_explosion5.wav` -> room `053`, sound `034`; effects: `trim 0.000 2.000`
- 42. `35_sound_SBL_forest-lever.wav` -> room `058`, sound `035`; effects: `trim 0.014 0.282`
- 43. `36_sound_ADL_forest-machine.wav` -> room `058`, sound `036`; effects: `trim 0.046 1.347`
- 44. `37_sound_SBL_forest-log-click.wav` -> room `058`, sound `037`; effects: `trim 0.000 0.873`
- 45. `23_sound_SBL_dummy-squeek.wav` -> room `060`, sound `023`; effects: `trim 0.013 0.211`
- 46. `59_sound_ADL_dig-noise.wav` -> room `064`, sound `059`; effects: `trim 0.007 0.639`
- 47. `60_sound_ADL_pat-dirt_03.wav` -> room `064`, sound `060`; effects: `trim 0.000 0.082`
- 48. `51_sound_SBL_snore-in.wav` -> room `071`, sound `051` child 0; effects: `trim 0.052 0.981`
- 49. `52_sound_SBL_snore-out.wav` -> room `071`, sound `052` child 0; effects: `trim 0.132 1.135`
- 50. `75_sound_SBL_sound_75_01.wav` -> room `072`, sound `075`; effects: `trim 0.008 1.472`
- 51. `54_sound_SBL_crate-1.wav` -> room `075`, sound `054`; effects: `trim 0.002 0.224`
- 52. `55_sound_SBL_crate-2.wav` -> room `075`, sound `055`; effects: `trim 0.003 0.728`
- 53. `56_sound_SBL_crate-3.wav` -> room `075`, sound `056`; effects: `trim 0.030 0.981`
- 54. `57_sound_SBL_crate-4.wav` -> room `075`, sound `057`; effects: `trim 0.000 0.921`
- 55. `58_sound_SBL_ghost-cluck.wav` -> room `075`, sound `058` child 2; effects: `trim 0.193 1.423`
- 56. `72_sound_SBL_sound_72_03.wav` -> room `077`, sound `072`; effects: `trim 0.006 0.744`
- 57. `15_sound_SBL_sputter.wav` -> room `083`, sound `015`; effects: `trim 0.001 1.944`
- 58. `16_sound_SBL_hit-water.wav` -> room `083`, sound `016`; effects: `trim 0.000 2.000`
- 59. `38_sound_SBL_sword-noise1.wav` -> room `088`, sound `038`; effects: `trim 0.000 0.272`
- 60. `39_sound_SBL_sword-noise2.wav` -> room `088`, sound `039`; effects: `trim 0.000 0.201`
- 61. `40_sound_SBL_sword-noise3.wav` -> room `088`, sound `040`; effects: `trim 0.000 0.277`
- 62. `41_sound_SBL_sword-noise4.wav` -> room `088`, sound `041`; effects: `trim 0.001 0.160`
- 63. `93_MetalDoorOpen.wav` -> room `010`, sound `175`; effects: `trim 0.014 0.544`
- 64. `94_MetalDoorClose.wav` -> room `010`, sound `176`; effects: `trim 0.007 0.614`
- 65. `97_Chest-open.wav` -> room `010`, sound `177`; effects: `trim 0.051 0.477`
- 66. `99_Chest-close.wav` -> room `010`, sound `178`; effects: `trim 0.005 0.568`
- 67. `80_Sword-draw.wav` -> room `088`, sound `171`; effects: `trim 0.011 0.710`
- 68. `81_Sword-disarm.wav` -> room `088`, sound `170`; effects: `trim 0.034 1.737`
- 69. `87_RootBeer-shake.wav` -> room `070`, sound `172`; effects: `(none)`
- 70. `88_RootBeer-Spray.wav` -> room `070`, sound `173`; effects: `trim 0.003 0.980`
- 71. `100_Ghost_Die.wav` -> room `059`, sound `174`; effects: `trim 0.010 1.255`

`wav2sbl.exe` findings:

- It is a small MinGW PE executable and contains the source filename string `wav2sbl.c`.
- Disassembly shows it ignores the requested output filename and always writes `000_SBL.dmp`.
- It skips the first 40 bytes of the WAV, reads a 24-bit little-endian data length from bytes 40-42, then copies the raw WAV data bytes after byte 44.
- It writes an `SBL ` chunk containing:
  - `AUhd`, payload size `3`, bytes `00 00 80`
  - `AUdt`, payload size `data_size + 7`, bytes `01`, a 24-bit `data_size + 2`, bytes `d2 00`, the raw 8-bit mono PCM data, and a trailing `00`
- `scummkit.sbl` implements this format natively for validated PCM WAV input. It intentionally validates the WAV format instead of accepting arbitrary files with the same loose assumptions as the Windows tool.

`scummpacker.exe` findings:

- It is a Windows executable that appears to be a frozen Python 2.5 application using `library.zip`.
- The bundled `library.zip` contains Python standard-library bytecode only; the app-specific bytecode is embedded in the executable.
- It unpacks `monkey.000` / `monkey.001` into a `000_LECF/` tree and repacks that tree into `Resource.000` / `Resource.001`.
- The native replacement avoids the extracted directory tree. It parses encrypted MI1 resources directly, replacing the targeted `SBL ` child inside each target `SOU ` chunk.
- `monkey.001` contains an encrypted `LECF` with `LOFF` and `LFLF` chunks. `LOFF` room offsets are updated when changed sound resources alter later room offsets.
- `monkey.000` contains encrypted directory chunks including `DSCR`, `DSOU`, `DCOS`, and `DCHR`. These offsets are updated after each room is rebuilt.
- The SBL path modifies both `monkey.000` and `monkey.001`: `monkey.001` receives larger sound chunks, and `monkey.000` receives updated resource directory offsets.

Native status:

- `python3 -m scummkit inject mi1 sbl` validates the builder files, requires `sox`, preserves pre-SBL copies under `.work/sbl/pre-sbl/`, and runs native SBL injection.
- `scummkit.mi1_sbl` parses `sbl.bat`, runs the same SoX conversions, creates SBL chunks through `scummkit.sbl`, injects 71 resources, updates resource offsets, verifies the rebuilt resource structure, and prints SHA256 values for pre/post `monkey.000` and `monkey.001`.
- This is the main difference from the MI2 pipeline. MI2 only patches `monkey2.000` / `monkey2.001`; MI1 also injects sound effects into the SCUMM resource tree.

### 4. Speech Archive Generation

The compression scripts are short:

```bat
build_monster wav
build_monster flac
build_monster ogg
build_monster mp3
```

Output names:

- `monster.sou` for WAV/raw.
- `monkey.sof` for FLAC.
- `monkey.sog` for Ogg.
- `monkey.so3` for MP3.

`monster.tbl` stats:

- MI1: 4393 lines, 4393 unique references.
- Each line is `8 hex digits` for the original VCTL offset followed by a sample basename.
- Example:

```text
00000008GUY_1_beach_1_1
00006accGUY_1_beach_1_2
00009a84GUY_1_beach_3_1
```

The native `scummkit.monster` packer applies to MI1 compressed modes as well because the table format and ScummVM compressed speech archive format match MI2.

### 5. CD and Special Edition Music

`cdaudio.bat` runs for non-WAV modes.

Classic CD music:

- Extracts `MusicOriginal.xwb`.
- Converts the extracted XWMA to WAV.
- Trims/remaps `track2.wav` through `track25.wav` into `cd_music_<mode>/track1.<mode>` through `track24.<mode>`.

Special Edition music/ambience:

- Extracts `MusicNew.xwb` and `Ambience.xwb`.
- Converts XWMA to WAV.
- Applies gain, trim, pad, compand, and mixing operations.
- Writes `se_music_<mode>/track1.<mode>` through `track29.<mode>`.

Native status:

- `scummkit.music` decodes `MusicOriginal.xwb`,
  `MusicNew.xwb`, and `Ambience.xwb` with `vgmstream-cli`.
- Earlier native builds used `python3 -m scummkit xwb --decode-wma`, which
  wrapped XACT WMA payloads as RIFF/XWMA and decoded them with `ffmpeg`. That
  produced structurally valid but audibly corrupt music for MI1 because the
  wrapper did not reproduce the Windows `unxwb.exe` plus `xWMAEncode` decode
  path correctly for these music banks.
- `scummkit.music` ports the Ogg path from `cdaudio.bat`.
- Classic CD output: `cd_music_ogg/track1.ogg` through `track24.ogg`, with `track10.ogg` intentionally absent to match the batch remapping.
- Special Edition output: `se_music_ogg/track1.ogg` through `track29.ogg`, plus `se_music_ogg/track8_no_sfx.ogg`.
- The Python CLI supports `--music cd|hybrid|se` for root `track*.ogg`
  selection:
  - `cd`: copy only `cd_music_ogg/track*.ogg` to the output root.
  - `hybrid`: copy `cd_music_ogg/track*.ogg`, then overlay
    `se_music_ogg/track25.ogg` through `track29.ogg`. This is the default and
    mirrors the Windows builder's optional
    `extended_SE_tracks_to_game_folder.bat` behavior.
  - `se`: copy `se_music_ogg/track*.ogg` to the output root.
- All modes keep `cd_music_ogg/` and `se_music_ogg/` for comparison or manual
  extra path selection.
- The music path is Ogg-only for now.

## MI1 Missing Ambience Investigation

The reported missing sounds are not all on the speech/SBL path.

| Sound | Source bank | Source filename | Duration | Room / resource | Type | Native destination |
| --- | --- | --- | ---: | --- | --- | --- |
| Opening / exterior waves | `Ambience.xwb` | `AMB_Beach_01` | 114.706576s | external ambience, likely beach/exterior rooms; no SCUMM `SOUN` id in the SBL table | ambience | extracted to `.work/music/ambience-wav/`; not mapped by original `cdaudio.bat` |
| Opening / exterior seagull chirp | `SFXNew.xwb` | `71_sound_SBL_seagull-cheep` | 0.741950s original, trimmed to 0.660s | room `041`, sound `071` (`000_LECF\041_LFLF_kitchen\008_SOUN_071`) | SFX/SBL | injected into `monkey.001`; reachable through `DSOU` |
| Opening / exterior seagull whoosh | `SFXNew.xwb` | `70_sound_ADL_seagull-whoosh` | 0.756939s | no `sbl.bat` target; not referenced by `monster.tbl` | SFX | extracted to `.work/sfxnew-wav/`; not injected by the Windows SBL script |
| SCUMM Bar pirate chatter / crowd | `Ambience.xwb` | `AMB_ScummBar_01` | 114.706576s, trimmed to 89.687s | external music track for SCUMM Bar; no SCUMM `SOUN` id | ambience/music | mixed with `MusicNew.xwb` `track9` to produce `se_music_ogg/track8.ogg` |

Evidence:

- `monster.tbl` contains SCUMM Bar and beach dialogue, but no entries for
  `AMB_ScummBar_01`, `AMB_Beach_01`, or the seagull SFX names. These are not
  speech archive samples.
- `sbl.bat` injects only `71_sound_SBL_seagull-cheep` for the seagull case,
  into room `041`, sound `071`. It does not inject SCUMM Bar crowd ambience or
  `70_sound_ADL_seagull-whoosh`.
- `cdaudio.bat` mixes `AMB_ScummBar_01` into `se_music_%1\track8.%1`.
- `cdaudio.bat` emits five standalone Special Edition ambience tracks:
  `track25` through `track29`.
- `extended_SE_tracks_to_game_folder.bat` moves only `track25` through
  `track29` from `se_music_ogg/` or `se_music_flac/` into the main game
  folder. The builder README says the user must add the output folder plus the
  extra path of the desired music version in ScummVM.

Ambience bank handling:

| Entry | Duration | Native output | Destination |
| --- | ---: | --- | --- |
| `AMB_Beach_01` | 114.706576s | `.work/music/ambience-wav/AMB_Beach_01.wav` | no `cdaudio.bat` mapping |
| `AMB_KitchenDocks_01` | 116.517732s | `.work/music/ambience-wav/AMB_KitchenDocks_01.wav` | no `cdaudio.bat` mapping |
| `AMB_ScummBar_01` | 114.706576s | temporary trimmed WAV | mixed into `se_music_ogg/track8.ogg`; kept in `se_music_ogg/` for optional extra-path use |
| `AMB_RiverJungle_01` | WMA bank entry | `.work/music/ambience-wav/AMB_RiverJungle_01.wav` | `se_music_ogg/track25.ogg`, now also copied to root |
| `AMB_TownNightClock_01` | WMA bank entry | `.work/music/ambience-wav/AMB_TownNightClock_01.wav` | `se_music_ogg/track26.ogg`, now also copied to root |
| `AMB_TownNight_01` | WMA bank entry | `.work/music/ambience-wav/AMB_TownNight_01.wav` | `se_music_ogg/track27.ogg`, now also copied to root |
| `AMB_Underwater_01` | WMA bank entry | `.work/music/ambience-wav/AMB_Underwater_01.wav` | `se_music_ogg/track28.ogg`, now also copied to root |
| `AMB_ShipDeck_01` | 75.836372s | `.work/music/ambience-wav/AMB_ShipDeck_01.wav` | `se_music_ogg/track29.ogg`, now also copied to root |

Pipeline traces:

- SCUMM Bar crowd:
  `Ambience.xwb/AMB_ScummBar_01` -> decoded WAV -> trimmed to 89.687s ->
  mixed with `MusicNew.xwb/track9` -> `se_music_ogg/track8.ogg`.
- SBL seagull chirp:
  `SFXNew.xwb/71_sound_SBL_seagull-cheep` -> decoded WAV -> SoX trim
  `0.000 0.660` -> native `wav2sbl` bytes -> room `041`, sound `071` in
  `monkey.001` -> indexed by `DSOU`.
- Exterior/beach waves:
  `Ambience.xwb/AMB_Beach_01` is decoded, but the original Windows
  `cdaudio.bat` does not assign it to a ScummVM track. This remains documented
  rather than guessed into an arbitrary track number.

The first root-track implementation copied the complete generated
`se_music_ogg/` track set into the output root. Runtime testing showed this made
ScummVM select the Special Edition music tracks as the main CD soundtrack, and
those tracks sounded like electronic noise in game. The default `hybrid` root
policy is now:

- `track1.ogg` through the available classic CD music tracks from
  `cd_music_ogg/`.
- `track25.ogg` through `track29.ogg` from `se_music_ogg/`, matching
  `extended_SE_tracks_to_game_folder.bat`.

This keeps the improved external ambience/SFX behavior without replacing the
classic CD music soundtrack with the full Special Edition music set.

`track1.ogg` trace from the full-SE-root-copy bad build:

| Stage | File | Codec | Rate/channels | Duration | Size |
| --- | --- | --- | --- | ---: | ---: |
| Source bank | `MusicNew.xwb` entry `track2` | XACT WMA/XWMA | 44100 Hz stereo | duration field 86.0067s | payload 1,043,406 bytes |
| Decoded WAV | `.work/music/new-wav/track2.wav` | PCM s16le | 44100 Hz stereo | 84.7528s | 14,950,478 bytes |
| SE Ogg | `se_music_ogg/track1.ogg` | Vorbis | 44100 Hz stereo | 84.7528s | about 1.0 MB |
| Bad root Ogg | `track1.ogg` | Vorbis | 44100 Hz stereo | 84.7528s | about 1.0 MB |
| Correct root Ogg | `cd_music_ogg/track1.ogg` copied to `track1.ogg` | Vorbis | 44100 Hz stereo | 118.503s after batch trim | about 1.2 MB |

`cd_music_ogg/track1.ogg` trace from the native-XWMA bad build:

| Stage | File | Codec | Rate/channels | Duration | Size |
| --- | --- | --- | --- | ---: | ---: |
| Source bank | `MusicOriginal.xwb` entry `track2` | XACT WMA/XWMA | 44100 Hz stereo | duration field 120.604s | payload 1,449,175 bytes |
| Bad decoded WAV | `.work/music/original-wav/track2.wav` from the ffmpeg wrapper path | PCM s16le | 44100 Hz stereo | 118.8397s | 20,963,406 bytes |
| Bad CD Ogg | `cd_music_ogg/track1.ogg` from the ffmpeg wrapper path | Vorbis | 44100 Hz stereo | 118.503s after batch trim | about 1.2 MB |
| Correct decoded WAV | `.work/music/original-wav/track2.wav` from `vgmstream-cli -i -S 0` | PCM s16le | 44100 Hz stereo | 120.6044s | 21,274,668 bytes |
| Correct CD Ogg | `cd_music_ogg/track1.ogg` from the vgmstream path | Vorbis | 44100 Hz stereo | 118.503s after batch trim | about 1.4 MB |

The XWB seek table for `MusicOriginal.xwb` confirms that the bank entries are
real CD music: `vgmstream-cli` reports `MusicOriginal.xwb` as a 25-stream XACT
bank containing Windows Media Audio 2 and PCM entries named `track2` through
`track25`, plus `silence`. The batch deliberately skips the CD data-track
numbering by converting `track2.wav` to ScummVM `track1.ogg`.

Wine comparison was not performed on this machine because `wine` is not
installed.

## XWB Findings

MI1 Special Edition audio banks inspected locally:

- `Speech.xwb`
  - XACT wave bank magic: `WBND`
  - tool version: 45
  - format version: 43
  - bank name: `Speech`
  - entries: 4551
  - observed format: PCM, usually 44100 Hz
  - native extraction works.
- `SFXNew.xwb`
  - XACT wave bank magic: `WBND`
  - tool version: 45
  - format version: 43
  - bank name: `SFXNew`
  - entries: 302
  - 247 PCM entries.
  - 55 WMA entries.
  - native Ogg build extracts all 302 entries when `ffmpeg` is available.

MI2 comparison:

- `Speech.xwb`
  - tool version: 46
  - format version: 44
  - entries: 7157
  - mostly ADPCM around 48 kHz.
- `Patch.xwb`
  - tool version: 46
  - format version: 44
  - entries: 30
  - ADPCM around 48 kHz.

## MI1 vs MI2

Similarities:

- Both builders patch classic SCUMM resources with `bspatch`.
- Both use `voice.bat` to extract XWB audio and prepare sample WAVs.
- Both use `monster.tbl` with `8 hex digits + sample basename`.
- Both call `build_monster` with `wav`, `flac`, `ogg`, or `mp3`.
- Both produce ScummVM compressed speech archives with the same container style for Ogg/FLAC/MP3.

Differences:

- MI1 input resource names are `classic/en/monkey1.000` and `classic/en/monkey1.001`; output names are `monkey.000` and `monkey.001`.
- MI2 input/output resource names are `monkey2.000` and `monkey2.001`.
- MI1 patch files are `patch10.000` and `patch10.001`.
- MI2 patch files are `patch02.000` and `patch02.001`.
- MI1 has no `Patch.xwb`; its voice pipeline also extracts `SFXNew.xwb`.
- MI2 uses `Patch.xwb` for additional speech lines.
- MI1 has a large `sbl.bat` step that injects sound effects into SCUMM resources with `scummpacker.exe` and `wav2sbl.exe`.
- MI2 does not have an equivalent SBL injection step in the native implementation.
- MI1 includes extensive CD/SE music conversion with `cdaudio.bat`.
- MI2 native work so far focuses on patched resources, speech extraction/processing, and the speech archive.
- MI1 archive names are `monkey.sog`, `monkey.sof`, `monkey.so3`; MI2 archive names are `monkey2.sog`, `monkey2.sof`, `monkey2.so3`.

## Native Implementation Status

Implemented in `python3 -m scummkit build mi1` and `scummkit build mi1`:

- validates inputs.
- creates a clean output directory.
- uses existing `extractpak` to extract `classic/en`.
- applies `patch10.000` / `patch10.001` with native `bspatch`.
- uses `scummkit.xwb` to extract:
  - `Speech.xwb` into `.work/speech-wav/`
  - `SFXNew.xwb` into `.work/sfxnew-wav/`, including WMA entries through `ffmpeg`
- uses `scummkit.voices` to apply `voice.bat` sample processing and encode Ogg samples.
- uses `scummkit.monster` to build `monkey.sog`.
- uses `scummkit.mi1_sbl` to inject the SBL sound effects natively.
- uses `scummkit.music` to convert CD and Special Edition music to Ogg.
- copies the builder readme.
- supports `--dry-run` and `--verbose`.
- supports `--skip-sbl` and `--skip-music`.

Observed native Ogg validation:

- extracted `4551` WAV files from `Speech.xwb`.
- extracted `302` WAV files from `SFXNew.xwb`.
- processed `4894` Ogg files.
- `monster.tbl` references: `4393`.
- `scummkit.monster` packed `4393` referenced samples.
- missing referenced samples: `0`.
- unreferenced processed samples: `501`.
- generated `monkey.sog` size: `100384453` bytes.
- generated `22` classic CD music Ogg files in `cd_music_ogg/`.
- generated `30` Special Edition music Ogg files in `se_music_ogg/`, including `track8_no_sfx.ogg`.
- generated and verified `71` SBL injections into `monkey.000` / `monkey.001`.

Remaining work for a complete native MI1 talkie build:

- Extend the MI1 native build beyond Ogg to FLAC/MP3 if needed.
- Investigate raw `monster.sou` if DOS/raw output is desired.

The Ogg path is now a full experimental native build: patched resources, speech archive, SBL sound-effect injection, classic CD music, and Special Edition music are generated without Wine. The SBL implementation has been validated structurally, but it has not yet been byte-for-byte compared against output produced by the original Windows builder.
