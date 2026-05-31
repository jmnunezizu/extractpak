from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from . import monster, voices, xwb
from .audio import count_files, require_audio_tools
from .paths import EXTRACTPAK
from .runner import BuildError, Runner, require_dir, require_file


@dataclass
class BuildOptions:
    pak: Path
    builder: Path
    out: Path
    audio: str
    dry_run: bool = False
    verbose: bool = False


def archive_name(audio: str) -> str:
    return {"ogg": "monkey2.sog", "flac": "monkey2.sof", "mp3": "monkey2.so3", "raw": "monster.sou"}[audio]


def build(options: BuildOptions) -> None:
    runner = Runner(options.dry_run, options.verbose)
    pak = options.pak.expanduser()
    builder = options.builder.expanduser()
    out = options.out.expanduser()
    tools = builder / "tools"
    audio_dir = pak.parent / "audio"
    work = out / ".work"
    extracted = work / "extracted"
    speech_wav = work / "speech-wav"
    patch_wav = work / "patch-wav"
    processed = work / "processed-voice"

    require_file(pak)
    require_dir(builder)
    require_dir(tools)
    require_file(builder / "readme.txt")
    require_file(tools / "patch02.000")
    require_file(tools / "patch02.001")
    require_file(tools / "monster.tbl")
    require_file(audio_dir / "Speech.xwb")
    require_file(audio_dir / "Patch.xwb")
    require_file(EXTRACTPAK)
    runner.require_tool("bspatch", "install bsdiff/bspatch; macOS usually provides /usr/bin/bspatch")
    require_audio_tools(runner, options.audio)

    runner.log("Monkey Island 2 Ultimate Talkie native helper")
    runner.log(f"pak:     {pak}")
    runner.log(f"builder: {builder}")
    runner.log(f"out:     {out}")
    runner.log(f"audio:   {options.audio}")

    if options.dry_run:
        runner.log("")
        runner.log("Planned steps:")
        runner.log("1. Clean and recreate output directory.")
        runner.log("2. Extract classic/en from monkey2.pak using extractpak.")
        runner.log("3. Patch monkey2.000 and monkey2.001 with bspatch.")
        runner.log("4. Extract WAV files from Speech.xwb and Patch.xwb.")
        runner.log("5. Process voice.bat samples and encode audio.")
        runner.log("6. Build the ScummVM speech archive.")
        runner.log("7. Copy builder readme.")
        runner.clean_dir(out)
        return

    runner.clean_dir(out)
    extracted.mkdir(parents=True, exist_ok=True)
    runner.run([EXTRACTPAK, "--only", "classic/en", pak, extracted])
    src000 = extracted / "classic/en/monkey2.000"
    src001 = extracted / "classic/en/monkey2.001"
    require_file(src000)
    require_file(src001)
    runner.run(["bspatch", src000, out / "monkey2.000", tools / "patch02.000"])
    runner.run(["bspatch", src001, out / "monkey2.001", tools / "patch02.001"])

    speech_wav.mkdir(parents=True, exist_ok=True)
    patch_wav.mkdir(parents=True, exist_ok=True)
    speech_bank = xwb.parse_xwb(audio_dir / "Speech.xwb")
    patch_bank = xwb.parse_xwb(audio_dir / "Patch.xwb")
    xwb.extract_entries(audio_dir / "Speech.xwb", speech_wav, speech_bank, verbose=options.verbose)
    xwb.extract_entries(audio_dir / "Patch.xwb", patch_wav, patch_bank, verbose=options.verbose)

    voices.process_mi2_voices(
        voices.Mi2VoiceOptions(
            builder=builder,
            speech_wav=speech_wav,
            patch_wav=patch_wav,
            out=processed,
            audio=options.audio,
            verbose=options.verbose,
        )
    )

    if options.audio == "raw":
        raise BuildError("raw monster.sou generation is not implemented yet; use ogg, flac, or mp3")
    monster.build_monster_archive(
        tools / "monster.tbl",
        processed / f"final-{options.audio}",
        out / archive_name(options.audio),
        options.audio,
        verbose=options.verbose,
    )
    shutil.copy2(builder / "readme.txt", out / "readme.txt")

    runner.log("")
    runner.log("Native experimental build complete.")
    runner.log("Generated:")
    runner.log(f"  {out / 'monkey2.000'}")
    runner.log(f"  {out / 'monkey2.001'}")
    runner.log(f"  {out / archive_name(options.audio)}")
    runner.log(f"  {out / 'readme.txt'}")
    runner.log(f"  {speech_wav}/*.wav ({count_files(speech_wav, '*.wav')})")
    runner.log(f"  {patch_wav}/*.wav ({count_files(patch_wav, '*.wav')})")
