from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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


def _copy_default_music_to_root(out: Path, audio: str, verbose: bool) -> int:
    """Expose the Windows builder's ScummVM-friendly default music set."""
    se_dir = out / f"se_music_{audio}"
    cd_dir = out / f"cd_music_{audio}"
    map_path = out / "music-root-map.txt"
    preview_dir = out / ".work" / "music" / "root-preview-wav"
    copied = 0
    mappings: list[tuple[Path, Path, str]] = []

    if cd_dir.is_dir():
        for source in sorted(cd_dir.glob(f"track*.{audio}")):
            target = out / source.name
            shutil.copy2(source, target)
            copied += 1
            mappings.append((target, source, "classic CD music"))
            if verbose:
                print(f"default music {source} -> {target}")

    if se_dir.is_dir():
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


def _root_music_policy(audio: str) -> str:
    return (
        f"available cd_music_{audio}/track*.{audio} plus "
        f"se_music_{audio}/track25-track29"
    )


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


def _print_audio_diagnostics(out: Path, audio: str, injected: list[dict[str, object]] | None) -> None:
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
        f"  root music policy: {_root_music_policy(audio)}",
        f"  root track8.{audio}: {_path_exists(out / f'track8.{audio}')}",
        f"  SE track8.{audio}: {_path_exists(se_music / f'track8.{audio}')} (kept in se_music_{audio}/)",
        f"  pre-SBL comparison folder: {pre_sbl if pre_sbl.exists() else 'missing'}",
    ]
    for line in runner_lines:
        print(line)


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
    if not options.skip_music:
        runner.require_tool("vgmstream-cli", "install vgmstream; it is required to decode MI1 XACT music banks")
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

    injected = None
    if not options.skip_sbl:
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

    if not options.skip_music:
        process_music = REPO_ROOT / "scripts/process-mi1-music.sh"
        require_file(process_music)
        music_cmd = [process_music, "--audio-dir", audio_dir, "--out", out, "--work", music_work, "--audio", options.audio]
        if options.verbose:
            music_cmd.append("--verbose")
        runner.run(music_cmd)
        copied = _copy_default_music_to_root(out, options.audio, options.verbose)
        runner.log(f"Default root music tracks: {copied} files ({_root_music_policy(options.audio)})")

    shutil.copy2(builder / "readme.txt", out / "readme.txt")
    _print_audio_diagnostics(out, options.audio, injected)
    runner.log("")
    runner.log("Native MI1 experimental Ogg build complete.")
    runner.log("Generated:")
    for name in ("monkey.000", "monkey.001", "monkey.sog", "readme.txt"):
        runner.log(f"  {out / name}")
    runner.log(f"  {out / 'cd_music_ogg'}/* ({count_files(out / 'cd_music_ogg', '*.ogg')})")
    runner.log(f"  {out / 'se_music_ogg'}/* ({count_files(out / 'se_music_ogg', '*.ogg')})")
    runner.log(f"  {out / 'track*.ogg'} ({_count_root_files(out, '*.ogg')})")
    runner.log(f"  {out / 'music-root-map.txt'}")
