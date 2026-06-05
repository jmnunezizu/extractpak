from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from . import monster, voices, xwb
from .audio import count_files, require_audio_tools
from .builder_inputs import format_dependency_report, write_build_note
from .paths import EXTRACTPAK
from .progress import BuildProgress
from .runner import BuildError, Runner, require_dir, require_file
from .summary import BuildSummary, print_build_summary


@dataclass
class BuildOptions:
    pak: Path
    builder: Path
    out: Path
    audio: str
    dry_run: bool = False
    verbose: bool = False
    quiet: bool = False


def archive_name(audio: str) -> str:
    try:
        return {"ogg": "monkey2.sog", "flac": "monkey2.sof", "mp3": "monkey2.so3", "raw": "monster.sou"}[audio]
    except KeyError as error:
        raise BuildError("unsupported MI2 audio format: use --audio ogg, flac, mp3, or raw") from error


def _stage(runner: Runner, progress: BuildProgress, index: int, total: int, label: str) -> None:
    if progress.enabled:
        progress.start(label)
    else:
        runner.log(f"[{index}/{total}] {label}...")


def _stage_done(progress: BuildProgress, label: str) -> None:
    progress.done(label)


def _bank_progress(runner: Runner, label: str):
    def report(done: int, total: int) -> None:
        if not runner.quiet:
            return
        runner.progress(f"{label} extracted", done, total)

    return report


def build(options: BuildOptions) -> None:
    started = time.monotonic()
    runner = Runner(options.dry_run, options.verbose, options.quiet)
    progress = BuildProgress(5, enabled=options.quiet)
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

    require_file(pak, "MI2 PAK file")
    require_dir(builder, "MI2 Ultimate Talkie builder directory")
    require_dir(tools, "MI2 builder tools directory")
    require_file(tools / "patch02.000", "MI2 patch file")
    require_file(tools / "patch02.001", "MI2 patch file")
    require_file(tools / "monster.tbl", "MI2 monster table")
    require_file(audio_dir / "Speech.xwb", "MI2 Special Edition Speech.xwb")
    require_file(audio_dir / "Patch.xwb", "MI2 Special Edition Patch.xwb")
    require_file(EXTRACTPAK, "compiled extractpak helper")
    runner.require_tool("bspatch", "install bsdiff/bspatch; macOS usually provides /usr/bin/bspatch")
    require_audio_tools(runner, options.audio)

    runner.log("Monkey Island 2 Ultimate Talkie native helper")
    runner.log(f"pak:     {pak}")
    runner.log(f"builder patch data: {builder}")
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
        runner.log("7. Write SCUMMKit build note.")
        runner.log("")
        runner.log(format_dependency_report("mi2", builder))
        runner.clean_dir(out)
        return

    try:
        monster.validate_table_for_game(tools / "monster.tbl", "mi2")
    except monster.MonsterError as error:
        raise BuildError(f"invalid MI2 monster table: {error}") from error

    runner.clean_dir(out)
    extracted.mkdir(parents=True, exist_ok=True)
    _stage(runner, progress, 1, 5, "Extracting PAK assets")
    runner.run([EXTRACTPAK, "--only", "classic/en", pak, extracted])
    src000 = extracted / "classic/en/monkey2.000"
    src001 = extracted / "classic/en/monkey2.001"
    require_file(src000, "extracted MI2 classic resource")
    require_file(src001, "extracted MI2 classic resource")
    _stage_done(progress, "Extracting PAK assets")
    _stage(runner, progress, 2, 5, "Applying Ultimate Talkie patches")
    runner.run(["bspatch", src000, out / "monkey2.000", tools / "patch02.000"])
    runner.run(["bspatch", src001, out / "monkey2.001", tools / "patch02.001"])
    _stage_done(progress, "Applying Ultimate Talkie patches")

    speech_wav.mkdir(parents=True, exist_ok=True)
    patch_wav.mkdir(parents=True, exist_ok=True)
    _stage(runner, progress, 3, 5, "Extracting XWB audio banks")
    try:
        speech_bank = xwb.parse_xwb(audio_dir / "Speech.xwb")
        patch_bank = xwb.parse_xwb(audio_dir / "Patch.xwb")
        if options.quiet:
            runner.status(
                f"  audio banks: Speech.xwb {len(speech_bank['entries'])} entries; "
                f"Patch.xwb {len(patch_bank['entries'])} entries"
            )
        xwb.extract_entries(
            audio_dir / "Speech.xwb",
            speech_wav,
            speech_bank,
            verbose=options.verbose,
            progress=_bank_progress(runner, "Speech.xwb"),
        )
        xwb.extract_entries(
            audio_dir / "Patch.xwb",
            patch_wav,
            patch_bank,
            verbose=options.verbose,
            progress=_bank_progress(runner, "Patch.xwb"),
        )
    except xwb.XwbError as error:
        raise BuildError(f"failed to extract MI2 Special Edition XWB audio: {error}") from error
    _stage_done(progress, "Extracting XWB audio banks")

    _stage(runner, progress, 4, 5, "Extracting and encoding voices")
    voices.process_mi2_voices(
        voices.Mi2VoiceOptions(
            builder=builder,
            speech_wav=speech_wav,
            patch_wav=patch_wav,
            out=processed,
            audio=options.audio,
            verbose=options.verbose,
            quiet=options.quiet,
        )
    )
    _stage_done(progress, "Extracting and encoding voices")

    if options.audio == "raw":
        raise BuildError("raw monster.sou generation is not implemented yet; use ogg, flac, or mp3")
    archive = out / archive_name(options.audio)
    _stage(runner, progress, 5, 5, "Building speech archive")
    try:
        monster_summary = monster.build_monster_archive(
            tools / "monster.tbl",
            processed / f"final-{options.audio}",
            archive,
            options.audio,
            verbose=options.verbose,
            quiet=options.quiet,
        )
    except monster.MonsterError as error:
        raise BuildError(f"failed to build MI2 speech archive: {error}") from error
    _stage_done(progress, "Building speech archive")
    build_note = write_build_note(game="mi2", out=out, pak=pak, builder=builder, audio=options.audio)

    print_build_summary(
        BuildSummary(
            game="Monkey Island 2: LeChuck's Revenge",
            out=out,
            generated_files=[out / "monkey2.000", out / "monkey2.001", archive, build_note],
            speech_archive_entries=monster_summary.packed,
            missing_samples=monster_summary.missing,
            audio=options.audio,
            elapsed_seconds=time.monotonic() - started,
        )
    )
