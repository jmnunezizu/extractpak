from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from . import mi1_sbl, monster, sbl, xwb
from .audio import count_files, require_audio_tools
from .mi2 import archive_name
from .paths import EXTRACTPAK, REPO_ROOT
from .runner import BuildError, Runner, require_dir, require_file


@dataclass
class BuildOptions:
    pak: Path
    builder: Path
    out: Path
    audio: str
    dry_run: bool = False
    verbose: bool = False
    skip_sbl: bool = False
    skip_music: bool = False


def build(options: BuildOptions) -> None:
    runner = Runner(options.dry_run, options.verbose)
    if options.audio != "ogg":
        raise BuildError("MI1 native build currently supports --audio ogg only")

    pak = options.pak.expanduser()
    builder = options.builder.expanduser()
    out = options.out.expanduser()
    tools = builder / "tools"
    audio_dir = pak.parent / "audio"
    work = out / ".work"
    extracted = work / "extracted"
    speech_wav = work / "speech-wav"
    sfx_wav = work / "sfxnew-wav"
    processed = work / "processed-voice"
    sbl_work = work / "sbl"
    music_work = work / "music"

    require_file(pak)
    require_dir(builder)
    require_dir(tools)
    require_file(builder / "readme.txt")
    require_file(tools / "patch10.000")
    require_file(tools / "patch10.001")
    require_file(tools / "monster.tbl")
    require_file(audio_dir / "Speech.xwb")
    require_file(audio_dir / "SFXNew.xwb")
    require_file(EXTRACTPAK)
    runner.require_tool("bspatch", "install bsdiff/bspatch; macOS usually provides /usr/bin/bspatch")
    runner.require_tool("ffmpeg", "install ffmpeg; it is required to decode WMA entries from SFXNew.xwb")
    require_audio_tools(runner, options.audio)

    runner.log("Monkey Island 1 Ultimate Talkie native helper")
    runner.log(f"pak:     {pak}")
    runner.log(f"builder: {builder}")
    runner.log(f"out:     {out}")
    runner.log(f"audio:   {options.audio}")

    if options.dry_run:
        runner.log("")
        runner.log("Planned steps:")
        runner.log("1. Clean and recreate output directory.")
        runner.log("2. Extract classic/en from Monkey1.pak using extractpak.")
        runner.log("3. Patch monkey1.000 and monkey1.001 with bspatch.")
        runner.log("4. Extract Speech.xwb and SFXNew.xwb, decoding WMA entries with ffmpeg.")
        runner.log("5. Process voice.bat samples and build monkey.sog.")
        runner.log("6. Inject SBL sound effects unless --skip-sbl is set.")
        runner.log("7. Convert music unless --skip-music is set.")
        runner.clean_dir(out)
        return

    runner.clean_dir(out)
    extracted.mkdir(parents=True, exist_ok=True)
    runner.run([EXTRACTPAK, "--only", "classic/en", pak, extracted])
    src000 = extracted / "classic/en/monkey1.000"
    src001 = extracted / "classic/en/monkey1.001"
    require_file(src000)
    require_file(src001)
    runner.run(["bspatch", src000, out / "monkey.000", tools / "patch10.000"])
    runner.run(["bspatch", src001, out / "monkey.001", tools / "patch10.001"])

    speech_wav.mkdir(parents=True, exist_ok=True)
    sfx_wav.mkdir(parents=True, exist_ok=True)
    speech_bank = xwb.parse_xwb(audio_dir / "Speech.xwb")
    sfx_bank = xwb.parse_xwb(audio_dir / "SFXNew.xwb")
    xwb.extract_entries(audio_dir / "Speech.xwb", speech_wav, speech_bank, verbose=options.verbose)
    xwb.extract_entries(audio_dir / "SFXNew.xwb", sfx_wav, sfx_bank, verbose=options.verbose, decode_wma=True)

    process_voices = REPO_ROOT / "scripts/process-mi1-voices.sh"
    require_file(process_voices)
    voice_cmd = [
        process_voices,
        "--builder",
        builder,
        "--speech-wav",
        speech_wav,
        "--sfx-wav",
        sfx_wav,
        "--out",
        processed,
        "--audio",
        options.audio,
    ]
    if options.verbose:
        voice_cmd.append("--verbose")
    runner.run(voice_cmd)

    monster.build_monster_archive(
        tools / "monster.tbl",
        processed / f"final-{options.audio}",
        out / archive_name(options.audio).replace("monkey2", "monkey"),
        options.audio,
        verbose=options.verbose,
    )

    if not options.skip_sbl:
        try:
            mi1_sbl.inject_mi1_sbl(
                builder,
                processed / "samples-wav",
                out / "monkey.000",
                out / "monkey.001",
                sbl_work,
                verbose=options.verbose,
            )
        except (OSError, mi1_sbl.InjectError, sbl.SblError) as error:
            raise BuildError(str(error)) from error

    if not options.skip_music:
        process_music = REPO_ROOT / "scripts/process-mi1-music.sh"
        require_file(process_music)
        music_cmd = [process_music, "--audio-dir", audio_dir, "--out", out, "--work", music_work, "--audio", options.audio]
        if options.verbose:
            music_cmd.append("--verbose")
        runner.run(music_cmd)

    shutil.copy2(builder / "readme.txt", out / "readme.txt")
    runner.log("")
    runner.log("Native MI1 experimental Ogg build complete.")
    runner.log("Generated:")
    for name in ("monkey.000", "monkey.001", "monkey.sog", "readme.txt"):
        runner.log(f"  {out / name}")
    runner.log(f"  {out / 'cd_music_ogg'}/* ({count_files(out / 'cd_music_ogg', '*.ogg')})")
    runner.log(f"  {out / 'se_music_ogg'}/* ({count_files(out / 'se_music_ogg', '*.ogg')})")
