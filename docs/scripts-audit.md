# scripts/ audit

SCUMMKit no longer requires shell scripts for the native build pipeline. The
remaining processing logic was moved into importable Python modules so it can be
tested and called directly by `python3 -m scummkit` and the `scummkit` console
script.

| File | Referenced | Called by CLI | Safe to Delete | Reason |
| --- | --- | --- | --- | --- |
| `scripts/build-mi1-talkie.sh` | No | No | Yes | Removed; users run `python3 -m scummkit build mi1` or `scummkit build mi1` directly. |
| `scripts/build-mi2-talkie.sh` | No | No | Yes | Removed; users run `python3 -m scummkit build mi2` or `scummkit build mi2` directly. |
| `scripts/build-monster.py` | No | Yes, through `scummkit monster` | Yes | Removed; archive packing and verification are implemented by `scummkit.monster`. |
| `scripts/extract-xwb.py` | No | Yes, through `scummkit xwb` | Yes | Removed; XWB parsing and extraction are implemented by `scummkit.xwb`. |
| `scripts/inject-mi1-sbl.py` | No | Yes, through `scummkit inject mi1 sbl` | Yes | Removed; MI1 SBL parsing, conversion, injection, and verification are implemented by `scummkit.mi1_sbl`. |
| `scripts/process-mi1-music.sh` | No | Yes, through `scummkit build mi1` | Yes | Removed; MI1 `cdaudio.bat` music decoding and SoX transforms are implemented by `scummkit.music`. |
| `scripts/process-mi1-sbl.sh` | No | Yes, through `scummkit inject mi1 sbl` | Yes | Removed; the compatibility wrapper is no longer needed. |
| `scripts/process-mi1-voices.sh` | No | Yes, through `scummkit build mi1` | Yes | Removed; MI1 `voice.bat` normalization, special cases, and encoding are implemented by `scummkit.voices`. |
| `scripts/process-mi2-voices.sh` | No | Yes, through `scummkit build mi2` | Yes | Removed; MI2 `voice.bat` normalization, `_cdt_*` special cases, and encoding are implemented by `scummkit.voices`. |
| `scripts/wav2sbl.py` | No | Yes, through `scummkit wav2sbl` | Yes | Removed; WAV-to-SBL conversion is implemented by `scummkit.sbl`. |
