from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import mi1_sbl, monster, music as mi1_music, sbl, voices, xwb
from .audio import count_files, require_audio_tools
from .mi2 import archive_name
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
    music: str = "hybrid"
    dry_run: bool = False
    verbose: bool = False
    quiet: bool = False
    skip_sbl: bool = False
    skip_music: bool = False


def _copy_default_music_to_root(out: Path, audio: str, music: str, verbose: bool) -> int:
    """Expose the selected ScummVM root soundtrack set."""
    se_dir = out / f"se_music_{audio}"
    cd_dir = out / f"cd_music_{audio}"
    map_path = out / "music-root-map.txt"
    preview_dir = out / ".work" / "music" / "root-preview-wav"
    copied = 0
    mappings: list[tuple[Path, Path, str]] = []

    if music not in ("cd", "hybrid", "se"):
        raise BuildError(f"unsupported MI1 music mode: {music}")

    if music in ("cd", "hybrid") and cd_dir.is_dir():
        for source in sorted(cd_dir.glob(f"track*.{audio}")):
            target = out / source.name
            shutil.copy2(source, target)
            copied += 1
            mappings.append((target, source, "classic CD music"))
            if verbose:
                print(f"default music {source} -> {target}")

    if music == "hybrid" and se_dir.is_dir():
        for track in range(25, 30):
            source = se_dir / f"track{track}.{audio}"
            if not source.exists():
                continue
            target = out / source.name
            shutil.copy2(source, target)
            copied += 1
            mappings.append((target, source, "SE extended ambience"))
            if verbose:
                print(f"default extended ambience {source} -> {target}")

    if music == "se" and se_dir.is_dir():
        for source in sorted(se_dir.glob(f"track*.{audio}")):
            target = out / source.name
            shutil.copy2(source, target)
            copied += 1
            mappings.append((target, source, "Special Edition music"))
            if verbose:
                print(f"default SE music {source} -> {target}")

    if mappings:
        lines = []
        preview_dir.mkdir(parents=True, exist_ok=True)
        for target, source, label in sorted(mappings, key=lambda item: item[0].name):
            duration = _audio_duration(target)
            lines.append(
                f"{target.name} <- {source.relative_to(out)} [{label}]"
                + (f" duration={duration:.3f}s" if duration is not None else "")
            )
            preview = preview_dir / f"{target.stem}-first10.wav"
            _write_preview_wav(target, preview)
        map_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if verbose:
            print(f"root music map: {map_path}")
            print(f"root music previews: {preview_dir}")

    return copied


def _root_music_policy(audio: str, music: str) -> str:
    if music == "cd":
        return f"available cd_music_{audio}/track*.{audio}"
    if music == "hybrid":
        return (
            f"available cd_music_{audio}/track*.{audio} plus "
            f"se_music_{audio}/track25-track29"
        )
    if music == "se":
        return f"available se_music_{audio}/track*.{audio}"
    return f"unknown music mode: {music}"


def _audio_duration(path: Path) -> Optional[float]:
    try:
        result = subprocess.run(
            ["soxi", "-D", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def _write_preview_wav(source: Path, destination: Path) -> None:
    try:
        subprocess.run(
            ["sox", str(source), str(destination), "trim", "0", "10"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return


def _path_exists(path: Path) -> str:
    return "yes" if path.exists() else "no"


def _count_root_files(path: Path, pattern: str) -> int:
    return sum(1 for item in path.glob(pattern) if item.is_file()) if path.exists() else 0


def _stage(runner: Runner, progress: BuildProgress, index: int, total: int, label: str) -> None:
    if progress.enabled:
        progress.start(label)
    else:
        runner.log(f"[{index}/{total}] {label}...")


def _stage_done(progress: BuildProgress, label: str) -> None:
    progress.done(label)


def _bank_progress(runner: Runner, label: str):
    last_reported = {"done": 0}

    def report(done: int, total: int) -> None:
        if not runner.quiet:
            return
        if done == total or done - last_reported["done"] >= 500:
            last_reported["done"] = done
            runner.status(f"  {label}: extracted {done}/{total} entries", inline=True, done=done == total)

    return report


def _print_audio_diagnostics(out: Path, audio: str, music: str, injected: list[dict[str, object]] | None) -> None:
    se_music = out / f"se_music_{audio}"
    sbl_ids = {(int(item["room_id"]), int(item["sound_id"])) for item in injected or []}
    seagull_injected = (41, 71) in sbl_ids
    pre_sbl = out / ".work" / "sbl" / "pre-sbl"

    runner_lines = [
        "",
        "MI1 audio diagnostics:",
        f"  opening waves source found: {_path_exists(out / '.work/music/ambience-wav/AMB_Beach_01.wav')}",
        f"  opening waves injected: no (external SE ambience track)",
        f"  opening waves reachable via resource index: no (external music track)",
        f"  opening seagulls resource found: {_path_exists(out / '.work/processed-voice/samples-wav/71_sound_SBL_seagull-cheep.wav')}",
        f"  opening seagulls injected: {'yes' if seagull_injected else 'no'}",
        f"  opening seagulls reachable via resource index: {'yes' if seagull_injected else 'no'}",
        f"  SCUMM Bar chatter source found: {_path_exists(out / '.work/music/ambience-wav/AMB_ScummBar_01.wav')}",
        f"  SCUMM Bar chatter injected: no (mixed into optional SE music track 8)",
        f"  SCUMM Bar chatter reachable via resource index: no (optional external music track)",
        f"  root music mode: {music}",
        f"  root music policy: {_root_music_policy(audio, music)}",
        f"  root track8.{audio}: {_path_exists(out / f'track8.{audio}')}",
        f"  SE track8.{audio}: {_path_exists(se_music / f'track8.{audio}')} (kept in se_music_{audio}/)",
        f"  pre-SBL comparison folder: {pre_sbl if pre_sbl.exists() else 'missing'}",
    ]
    for line in runner_lines:
        print(line)


def build(options: BuildOptions) -> None:
    started = time.monotonic()
    runner = Runner(options.dry_run, options.verbose, options.quiet)
    progress = BuildProgress(7, enabled=options.quiet)
    if options.audio != "ogg":
        raise BuildError("unsupported MI1 audio format: use --audio ogg; FLAC/MP3/raw are not validated for MI1 yet")
    if options.music not in ("cd", "hybrid", "se"):
        raise BuildError("unsupported MI1 music mode: use --music cd, --music hybrid, or --music se")

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

    require_file(pak, "MI1 PAK file")
    require_dir(builder, "MI1 Ultimate Talkie builder directory")
    require_dir(tools, "MI1 builder tools directory")
    require_file(builder / "readme.txt", "MI1 builder readme")
    require_file(tools / "patch10.000", "MI1 patch file")
    require_file(tools / "patch10.001", "MI1 patch file")
    require_file(tools / "monster.tbl", "MI1 monster table")
    require_file(audio_dir / "Speech.xwb", "MI1 Special Edition Speech.xwb")
    require_file(audio_dir / "SFXNew.xwb", "MI1 Special Edition SFXNew.xwb")
    require_file(EXTRACTPAK, "compiled extractpak helper")
    runner.require_tool("bspatch", "install bsdiff/bspatch; macOS usually provides /usr/bin/bspatch")
    runner.require_tool("ffmpeg", "install ffmpeg; it is required to decode WMA entries from SFXNew.xwb")
    if not options.skip_music:
        runner.require_tool("vgmstream-cli", "install vgmstream; it is required to decode MI1 XACT music banks")
    require_audio_tools(runner, options.audio)

    runner.log("Monkey Island 1 Ultimate Talkie native helper")
    runner.log(f"pak:     {pak}")
    runner.log(f"builder: {builder}")
    runner.log(f"out:     {out}")
    runner.log(f"audio:   {options.audio}")
    runner.log(f"music:   {options.music}")

    if options.dry_run:
        runner.log("")
        runner.log("Planned steps:")
        runner.log("1. Clean and recreate output directory.")
        runner.log("2. Extract classic/en from Monkey1.pak using extractpak.")
        runner.log("3. Patch monkey1.000 and monkey1.001 with bspatch.")
        runner.log("4. Extract Speech.xwb and SFXNew.xwb, decoding WMA entries with ffmpeg.")
        runner.log("5. Process voice.bat samples and build monkey.sog.")
        runner.log("6. Inject SBL sound effects unless --skip-sbl is set.")
        runner.log(f"7. Convert music unless --skip-music is set; root mode: {options.music}.")
        runner.clean_dir(out)
        return

    runner.clean_dir(out)
    extracted.mkdir(parents=True, exist_ok=True)
    _stage(runner, progress, 1, 7, "Extracting PAK assets")
    runner.run([EXTRACTPAK, "--only", "classic/en", pak, extracted])
    src000 = extracted / "classic/en/monkey1.000"
    src001 = extracted / "classic/en/monkey1.001"
    require_file(src000, "extracted MI1 classic resource")
    require_file(src001, "extracted MI1 classic resource")
    _stage_done(progress, "Extracting PAK assets")
    _stage(runner, progress, 2, 7, "Applying Ultimate Talkie patches")
    runner.run(["bspatch", src000, out / "monkey.000", tools / "patch10.000"])
    runner.run(["bspatch", src001, out / "monkey.001", tools / "patch10.001"])
    _stage_done(progress, "Applying Ultimate Talkie patches")

    speech_wav.mkdir(parents=True, exist_ok=True)
    sfx_wav.mkdir(parents=True, exist_ok=True)
    _stage(runner, progress, 3, 7, "Extracting XWB audio banks")
    try:
        speech_bank = xwb.parse_xwb(audio_dir / "Speech.xwb")
        sfx_bank = xwb.parse_xwb(audio_dir / "SFXNew.xwb")
        if options.quiet:
            runner.status(
                f"  audio banks: Speech.xwb {len(speech_bank['entries'])} entries; "
                f"SFXNew.xwb {len(sfx_bank['entries'])} entries"
            )
        xwb.extract_entries(
            audio_dir / "Speech.xwb",
            speech_wav,
            speech_bank,
            verbose=options.verbose,
            progress=_bank_progress(runner, "Speech.xwb"),
        )
        xwb.extract_entries(
            audio_dir / "SFXNew.xwb",
            sfx_wav,
            sfx_bank,
            verbose=options.verbose,
            decode_wma=True,
            progress=_bank_progress(runner, "SFXNew.xwb"),
        )
    except xwb.XwbError as error:
        raise BuildError(f"failed to extract MI1 Special Edition XWB audio: {error}") from error
    _stage_done(progress, "Extracting XWB audio banks")

    _stage(runner, progress, 4, 7, "Extracting and encoding voices")
    voices.process_mi1_voices(
        voices.Mi1VoiceOptions(
            builder=builder,
            speech_wav=speech_wav,
            sfx_wav=sfx_wav,
            out=processed,
            audio=options.audio,
            verbose=options.verbose,
            quiet=options.quiet,
        )
    )
    _stage_done(progress, "Extracting and encoding voices")

    archive = out / archive_name(options.audio).replace("monkey2", "monkey")
    _stage(runner, progress, 5, 7, "Building speech archive")
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
        raise BuildError(f"failed to build MI1 speech archive: {error}") from error
    _stage_done(progress, "Building speech archive")

    injected = None
    if not options.skip_sbl:
        _stage(runner, progress, 6, 7, "Injecting SBL resources")
        try:
            injected = mi1_sbl.inject_mi1_sbl(
                builder,
                processed / "samples-wav",
                out / "monkey.000",
                out / "monkey.001",
                sbl_work,
                verbose=options.verbose,
            )
        except (OSError, mi1_sbl.InjectError, sbl.SblError) as error:
            raise BuildError(str(error)) from error
        _stage_done(progress, "Injecting SBL resources")
    else:
        _stage(runner, progress, 6, 7, "Skipping SBL resource injection")
        _stage_done(progress, "Skipping SBL resource injection")

    if not options.skip_music:
        _stage(runner, progress, 7, 7, "Converting music")
        mi1_music.process_mi1_music(
            mi1_music.Mi1MusicOptions(
                audio_dir=audio_dir,
                out=out,
                work=music_work,
                audio=options.audio,
                verbose=options.verbose,
                quiet=options.quiet,
            )
        )
        copied = _copy_default_music_to_root(out, options.audio, options.music, options.verbose)
        runner.log(
            f"Default root music tracks: {copied} files "
            f"({_root_music_policy(options.audio, options.music)})"
        )
        _stage_done(progress, "Converting music")
    else:
        _stage(runner, progress, 7, 7, "Skipping music conversion")
        _stage_done(progress, "Skipping music conversion")

    shutil.copy2(builder / "readme.txt", out / "readme.txt")
    if not options.quiet:
        _print_audio_diagnostics(out, options.audio, options.music, injected)
    generated = [out / name for name in ("monkey.000", "monkey.001", archive.name, "readme.txt")]
    if not options.skip_music:
        generated.append(out / "music-root-map.txt")
    print_build_summary(
        BuildSummary(
            game="The Secret of Monkey Island",
            out=out,
            generated_files=generated,
            speech_archive_entries=monster_summary.packed,
            missing_samples=monster_summary.missing,
            audio=options.audio,
            music=options.music,
            elapsed_seconds=time.monotonic() - started,
        )
    )
