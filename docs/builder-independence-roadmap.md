# Builder Independence Roadmap

SCUMMKit no longer depends on the original Windows builder executables or batch
files for the validated native build paths. It includes the small authored
Ultimate Talkie patch/table data set with permission from the original builder
author. This note describes the dependency boundary, what has already been
replaced, and why full patch-data regeneration is not the immediate milestone.

## Current Position

The practical goal is now **native build independence from the Windows builder
package**, not complete reauthoring of every Ultimate Talkie patch-data file.

SCUMMKit can replace the builder's orchestration and several helper recipes
natively:

- native PAK extraction;
- native XWB inspection/extraction;
- native speech archive packing;
- native `_cdt_silence.wav` generation;
- generated `SCUMMKIT-BUILD.txt` output note instead of copying the builder
  readme;
- native MI1 SBL command data and injection.

SCUMMKit still uses the Ultimate Talkie patch data that changes the classic
SCUMM game resources and binds those resources to speech archive IDs. The
original author confirmed that `monster.tbl` was built with internal tools that
were not optimized for later changes. Replacing these files would require
reauthoring or faithfully reproducing a large set of SCUMM resource, script,
sound, and table changes.

## Current Builder Inputs

MI1 reads these files from `third_party/ultimate-talkie/mi1/` by default:

- `patch10.000`
- `patch10.001`
- `monster.tbl`

MI2 reads these files from `third_party/ultimate-talkie/mi2/` by default:

- `patch02.000`
- `patch02.001`
- `monster.tbl`

The Windows-only tools and batch scripts from the builders are not used by the
main Python build pipelines. `--builder` remains as an optional compatibility
input if a developer wants to use a local original builder folder instead of
the bundled third-party data. The remaining authored data is:

- binary patches for the extracted classic SCUMM resource files;
- `monster.tbl` speech archive maps;

The `scummkit builder-inputs mi1` and `scummkit builder-inputs mi2` commands
report the bundled/default data source, or a local original builder source when
`--builder` is supplied.

## Licensing And Redistribution

This section is based on a local audit of:

- `/Users/jmnunezizu/Downloads/MI1_Ultimate_Talkie_Edition_Builder`
- `/Users/jmnunezizu/Downloads/MI2_Ultimate_Talkie_Edition_Builder`

The MI1 Ultimate Talkie web page at
`https://gratissaugen.de/ultimatetalkies/monkey1.html` says the builder creates
a talkie version from the Special Edition, requires a legally installed PC copy,
and that `xWMAEncode.exe` is not included for legal reasons. The page also notes
that the DirectX SDK convenience download is subject to Microsoft's DirectX SDK
EULA.

The MI1 builder package also includes license text for files authored by
LogicDeLuxe. It lists these relevant files as created exclusively for the MI1
Ultimate Talkie Edition patch:

- `readme.txt`
- `tools/monster.tbl`
- `tools/patch10.000`
- `tools/patch10.001`
- `tools/sbl.bat`
- `tools/voice.bat`
- `tools/_cdt_silence`

The license text says the files are provided without warranty, may be
distributed free of charge for non-commercial purposes, and may not be separated
from the package without the author's agreement.

The MI1 readme also has a general license section for the patch:

```text
This patch is freeware and distributed with no warranty. You may use it at your
own risk. Non-commercial use only. You may re-distribute the patch, but not the
resulting game.
```

The readme credits third-party tools and notes their separate licenses,
including SoX under GPLv2, 7-Zip under LGPL, bsdiff under the BSD Protection
License, unxwb under GPLv2, public-domain scummpacker, LucasArts `fatecd.exe`
and `dottcd.exe` patches, and Microsoft's DirectX SDK `xWMAEncode.exe`, which
is not included for legal reasons.

The MI2 builder readme has a more explicit license section:

```text
This patch is freeware and distributed with no warranty. You may use it at your
own risk. Non-commercial use only. You may re-distribute the patch, but not the
resulting game.
```

That is useful, but it is not the same as an open-source license. The
non-commercial restriction is incompatible with treating the MI2 patch data as
ordinary MIT-licensed SCUMMKit source. If SCUMMKit ever redistributes MI2
builder-derived data, it should keep that data clearly separated from the MIT
code, preserve the upstream license/credits, and document that the redistributed
patch data is for non-commercial use only.

The original author has now granted permission to use the authored patch/table
files in SCUMMKit under the original package terms, with attribution to the
original patch and a note that the files are used with permission. SCUMMKit
therefore vendors only the minimal patch/table data set under
`third_party/ultimate-talkie/`, keeps the original package license text in
`licenses/original_ute_builder.txt`, and does not include generated game output
or any files from the commercial Special Edition games.

## Where `monster.tbl` Comes From

In the current native pipeline, `monster.tbl` comes from the vendored
third-party Ultimate Talkie patch data:

- MI1: `third_party/ultimate-talkie/mi1/monster.tbl`
- MI2: `third_party/ultimate-talkie/mi2/monster.tbl`

When `--builder` is supplied, SCUMMKit can still read the table from the
matching local original builder folder instead.

SCUMMKit does not generate these tables today. It parses them and uses them as
the speech archive manifest.

Each non-empty table row is interpreted as:

```text
8 lowercase hex digits for the original VCTL offset
sample basename without extension
```

The offset identifies the original script speech location expected by the
patched game resources. The sample basename points to a processed speech file
created from the Special Edition audio banks and builder-compatible voice
special cases. `scummkit.monster` then packs only referenced samples into the
ScummVM compressed speech archive.

Known observed table sizes:

- MI1: 4393 lines / 4393 unique references.
- MI2: 6808 lines / 6808 unique original offsets / 6808 unique sample basenames.

The upstream process used to create `monster.tbl` is not included in SCUMMKit.
The original author confirmed that the tables were built with internal tools
and that he would likely approach the tooling differently today. The tables are
part of the Ultimate Talkie builder's authored patch data: they bridge patched
SCUMM resource offsets to extracted Special Edition speech sample names.

The local builder audit found no batch script that generates `monster.tbl` or
the SCUMM binary patch files. The install scripts consume them as static files:

- MI1 `install.bat` extracts classic resources and applies `patch10.000` /
  `patch10.001` with `bspatch`.
- MI1 format scripts call `build_monster`, which consumes `monster.tbl`.
- MI2 `install.bat` extracts classic resources with `MI2_ResExtract` and applies
  `patch02.000` / `patch02.001` with `bspatch`.
- MI2 format scripts call `build_monster`, which consumes `monster.tbl`.

MI1 provenance is explicit: `licenses/This Package.txt` says `monster.tbl`,
`patch10.000`, `patch10.001`, and related batch files were written and/or
created by LogicDeLuxe exclusively for the MI1 Ultimate Talkie Edition patch.
MI2 provenance is less explicit in the local package: `readme.txt` licenses
redistribution of the patch as a whole for non-commercial use, and credits
third-party tools including `MI2_ResExtract` by bgbennyboy, but does not include
a separate file-level authorship list for `monster.tbl`, `patch02.000`, or
`patch02.001`.

## `monster.tbl` Generation Investigation

The current evidence says `monster.tbl` is not generated by the shipped builder
scripts during install. It is a pre-authored manifest consumed by the builder:

- `build_monster.exe` is identical in the audited MI1 and MI2 builders.
- `build_monster.exe` strings show it was built from `build_monster.c` and
  references `monster.tbl`, `VCTL`, WAV validation, and output archive names.
- The generated `.sog` archive index carries the `monster.tbl` offsets exactly:
  MI1 has 4393 archive index entries matching the 4393 table rows; MI2 has 6808
  archive index entries matching the 6808 table rows.
- Brute-force searching patched `monkey*.001` resource data for the 32-bit table
  offsets found only incidental hits, not a systematic copy of the table. The
  offsets are therefore not literal byte positions in the resource file.

The first column is best understood as the MONSTER/SOU speech ID, historically
called the "original offset" by ScummVM tooling. In ScummVM compressed speech
archives, that value is the lookup key used by game scripts/resources to find
the compressed payload.

ScummSpeaks v3 documentation describes the same model: a speech map contains
sound entries with an `ID/Original Offset`, the ID is exported into game
resources, and MONSTER resources use a unique number for that ID. ScummSpeaks
also uses ScummTr to extract and reinsert dialogue text, which is consistent
with how a table like `monster.tbl` would be authored: map script text lines to
speech files, assign MONSTER IDs, export patched game resources, and pack the
speech archive from the same map.

The local builders do not include a ScummSpeaks speech-map XML or equivalent
source project. They only include the exported table and binary patches.

### Special Edition Mapping Files

The Special Edition installs include source mapping data that can help replace
`monster.tbl`:

- MI1: `audio/speech.info`
- MI2: `audio/speech.info`
- MI2: `audio/SpeechCues.xsb`

These files come from the official Monkey Island Special Edition game installs,
not from the Ultimate Talkie builders. They are local game assets and should be
treated the same way as `Speech.xwb`, `SFXNew.xwb`, `Patch.xwb`, and the `.pak`
files: SCUMMKit may parse them from a user's legally owned install during a
local build, but should not redistribute their contents.

MI1 `speech.info` contains records with dialogue text and speech filenames. A
local parse found 4573 records and 4397 unique speech filenames. Of the 4393 MI1
`monster.tbl` sample names, 4281 are present in `speech.info`; 112 table names
are not in `speech.info`, and 116 `speech.info` names are not used by
`monster.tbl`. The differences are likely builder-authored special cases,
deleted/unused lines, split lines, or sound-effect/dialogue substitutions.

MI2 is different in the current extracted assets: the builder `monster.tbl` uses
numeric names such as `000016a7`, while `speech.info` contains descriptive
speech filenames. `Speech.xwb` entries are unnamed in the current XWB parser,
and `SpeechCues.xsb` contains descriptive cue names. Reproducing MI2's exact
table therefore likely requires parsing the XSB cue bank and/or reproducing the
old `unxwb` extraction naming scheme used by the original builder.

Recent ScummVM work is relevant but not a drop-in replacement. ScummVM now has a
direct remastered-audio path for MI1/MI2 Special Edition assets that maps speech
using room, script, local script offset, message index, text, and speech file
metadata. Those synthetic remastered-audio keys do not match the Ultimate
Talkie `monster.tbl` offsets, because they are for ScummVM's direct Special
Edition audio playback path rather than the classic MONSTER.SOU-compatible
patched-resource path.

### Can We Regenerate It?

Yes, but not by scanning audio files alone. A faithful generator needs both
sides of the map:

1. Which in-game dialogue/script event should play speech.
2. Which Special Edition speech file should be used for that event.
3. Which MONSTER/SOU ID should be embedded into the patched SCUMM resources.
4. The same ID/name pair must be written to the speech archive manifest.

There are two viable approaches:

- **Compatibility generator:** recover or reconstruct the original speech map
  from `speech.info`, XSB cue data, ScummTr-style script text extraction, and
  builder special cases, then generate a `monster.tbl` equivalent and native
  resource patches from that map.
- **New native speech system:** stop trying to preserve the original
  Ultimate Talkie MONSTER offsets. Generate fresh stable IDs, patch the SCUMM
  scripts/resources to use those IDs, and build the archive from the generated
  manifest. This still requires native script/resource patching, but it avoids
  needing to reproduce LogicDeLuxe's exact numeric offsets.

The second option is cleaner for SCUMMKit independence. It treats
`monster.tbl` as an implementation artifact: once SCUMMKit owns native resource
patching, the IDs can be generated deterministically from SCUMMKit's own speech
map instead of copied from the builder.

The generated SCUMMKit speech map should be stored as a local generated
manifest, preferably JSON for now because it is dependency-free and
deterministic. The manifest can carry richer metadata than `monster.tbl`, for
example:

```json
{
  "game": "mi1",
  "format": "scummkit-speech-manifest-v1",
  "entries": [
    {
      "speech_id": 8,
      "speech_id_hex": "00000008",
      "sample": "GUY_1_beach_1_1",
      "source": "speech.info",
      "room": 1,
      "script": null,
      "local_script_offset": null,
      "message_index": null,
      "text": "..."
    }
  ]
}
```

For validation, SCUMMKit can export a temporary `monster.tbl`-compatible view
from a generated manifest and compare it against the vendored
`third_party/ultimate-talkie/*/monster.tbl` files. If a generated view ever
matches, the build could use the manifest directly and stop requiring the
authored table.

## Replacement Strategy

### 1. Removed Easy Builder Data

Completed:

- SCUMMKit generates the silence sample in Python instead of copying
  `tools/_cdt_silence`.
- SCUMMKit writes `SCUMMKIT-BUILD.txt` instead of copying the builder readme.
- MI1 SBL commands are represented as native structured data in
  `scummkit/mi1_sbl_data.py`.

The MI1 injector can still compare native SBL data against a local builder
`tools/sbl.bat` for developer validation, but the build path no longer requires
that batch file.

### 2. Vendor The Minimal Patch/Table Data

Completed:

- `third_party/ultimate-talkie/mi1/` carries `patch10.000`, `patch10.001`, and
  `monster.tbl`.
- `third_party/ultimate-talkie/mi2/` carries `patch02.000`, `patch02.001`, and
  `monster.tbl`.
- `licenses/original_ute_builder.txt` preserves the original package license
  text.
- `--builder` remains optional and can still point at a local original builder
  folder for compatibility or comparison.

The current MI1 speech manifest prototype can generate a builder-coverage view
of sample names from Special Edition `speech.info` plus classified special
cases, but it does not replace the builder table's MONSTER/SOU IDs in the final
build. Those IDs must agree with the patched SCUMM resources, so replacing the
table independently is not enough.

Useful validation for this phase:

- table row count and uniqueness checks;
- archive entry count checks;
- comparison of generated archive indexes against builder-derived builds;
- no missing referenced samples after voice processing.

### 3. Treat Binary Patch Replacement As A Long-Term Spike

The binary patches are the hardest remaining dependency. They encode the
Ultimate Talkie changes to the classic SCUMM resource files:

- MI1: `patch10.000` and `patch10.001`
- MI2: `patch02.000` and `patch02.001`

To remove them, SCUMMKit needs a native patcher that can:

- parse the extracted `monkey*.000` resource index;
- read and rewrite resources in `monkey*.001`;
- apply the same script, room, sound, and resource changes encoded by the
  current patches;
- preserve offsets and indexes in a ScummVM-compatible layout;
- verify the rebuilt resources structurally after patching.

This should be done game by game. MI2 is the better first target because it has
no MI1 SBL injection and no MI1 music-root policy. Once MI2 has native resource
patching and native speech-table generation, the same approach can be applied to
MI1 with the extra SBL table work.

For MI1, current patch classification shows why this is not a small cleanup:
native SBL data accounts for 71 sound-resource patch entries, but the patch also
contains script changes, room/resource layout changes, music/rich sound changes,
SFX changes, control placeholders, and visual/costume fixes. Without the
original source map, replacing this data means building a new native patcher and
then proving behavioral parity.

## CLI Migration Plan

The long-term target user flow would be:

```bash
python3 -m scummkit build mi1 --pak ~/Downloads/MonkeyIsland/Monkey1.pak --out /tmp/mi1 --audio ogg
python3 -m scummkit build mi2 --pak ~/Downloads/MonkeyIsland2/app/monkey2.pak --out /tmp/mi2 --audio ogg
```

The current CLI already supports that flow by default. `--builder` remains as
an optional override:

```bash
python3 -m scummkit build mi2 --pak ... --out ... --audio ogg
python3 -m scummkit build mi2 --pak ... --builder ~/Downloads/MI2_Ultimate_Talkie_Edition_Builder --out ... --audio ogg
```

When supplied, `--builder` means "read local Ultimate Talkie patch data from
this folder", not "run the Windows builder".

## Recommended Next Work

1. Keep README and CLI diagnostics explicit that bundled Ultimate Talkie
   patch/table data is third-party data used with permission.
2. Add or tighten `monster.tbl` validation diagnostics so bad patch data inputs
   fail early with clear row-count, duplicate, and missing-sample messages.
3. Preserve the MI1 patch-diff and sound-plan tooling as developer analysis
   commands, not required build steps.
4. Optionally start a small MI2 native patching spike that compares patched
   output against the current `bspatch` output at the resource/index level.
5. Continue the speech-map extractor/generator as a research track:
   - parse MI1 `audio/speech.info`;
   - parse MI2 `audio/speech.info` and `SpeechCues.xsb`;
   - compare generated speech filenames against builder `monster.tbl`;
   - classify missing/extra entries as special cases or unused source lines.
6. Decide whether to preserve Ultimate Talkie MONSTER IDs or generate new stable
   IDs once native resource patching exists.
