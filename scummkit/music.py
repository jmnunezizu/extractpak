from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .audio import count_files, sox_can_write
from .runner import BuildError, Runner, require_dir, require_file


@dataclass
class Mi1MusicOptions:
    audio_dir: Path
    out: Path
    work: Path
    audio: str
    dry_run: bool = False
    verbose: bool = False


CD_TRACKS: list[tuple[str, str, list[str]]] = [
    ("track2.wav", "track1.ogg", ["trim", "0.045", "118.503"]),
    ("track3.wav", "track2.ogg", ["trim", "0.032", "122.138"]),
    ("track4.wav", "track3.ogg", ["trim", "0.031", "121.770"]),
    ("track5.wav", "track4.ogg", ["trim", "0.036", "113.585"]),
    ("track6.wav", "track5.ogg", ["trim", "0.034", "125.445"]),
    ("track7.wav", "track6.ogg", ["trim", "0.034", "10.413"]),
    ("track8.wav", "track7.ogg", ["trim", "0.000", "67.936"]),
    ("track9.wav", "track8.ogg", ["trim", "0.035", "137.022"]),
    ("track10.wav", "track9.ogg", ["trim", "0.038", "121.996"]),
    ("track12.wav", "track11.ogg", ["trim", "0.032", "136.786"]),
    ("track13.wav", "track12.ogg", ["trim", "0.039", "120.944"]),
    ("track14.wav", "track13.ogg", ["trim", "0.037", "16.374"]),
    ("track15.wav", "track14.ogg", ["trim", "0.039", "156.310"]),
    ("track16.wav", "track15.ogg", ["trim", "0.031", "146.849"]),
    ("track17.wav", "track16.ogg", ["trim", "0.039", "219.942"]),
    ("track18.wav", "track17.ogg", ["trim", "1.000", "156.971", "pad", "3.000@95.270"]),
    ("track19.wav", "track18.ogg", ["trim", "0.035", "155.867"]),
    ("track20.wav", "track19.ogg", ["trim", "0.035", "16.295"]),
    ("track22.wav", "track21.ogg", ["trim", "0.032", "132.555"]),
    ("track23.wav", "track22.ogg", []),
    ("track24.wav", "track23.ogg", []),
    ("track25.wav", "track24.ogg", []),
]


SE_MUSIC_TRACKS: list[tuple[str, str, list[str]]] = [
    ("track2.wav", "track1.ogg", ["gain", "-6"]),
    ("track3.wav", "track2.ogg", ["gain", "-6"]),
    ("track4.wav", "track3.ogg", ["gain", "-6"]),
    ("track5.wav", "track4.ogg", ["gain", "-6"]),
    ("track6.wav", "track5.ogg", ["gain", "-6"]),
    ("track7.wav", "track6.ogg", ["gain", "-6", "trim", "0.034", "12.027"]),
    ("track8.wav", "track7.ogg", ["gain", "-6", "trim", "0.000", "69.445"]),
    ("track9.wav", "track8_no_sfx.ogg", ["gain", "-6"]),
    ("track10.wav", "track9.ogg", ["gain", "-6"]),
    ("track18c.wav", "track10.ogg", ["gain", "-6"]),
    ("track12.wav", "track11.ogg", ["gain", "-6"]),
    ("track13.wav", "track12.ogg", ["gain", "-6"]),
    ("track14.wav", "track13.ogg", ["gain", "-6"]),
    ("track15.wav", "track14.ogg", ["gain", "-6"]),
    ("track16.wav", "track15.ogg", ["gain", "-6", "trim", "0.000", "137.674"]),
    ("track17.wav", "track16.ogg", ["gain", "-6"]),
    ("track18b.wav", "track17.ogg", ["gain", "-4"]),
    ("track19.wav", "track18.ogg", ["gain", "-8"]),
    ("track20.wav", "track19.ogg", ["gain", "-6", "trim", "0.035", "14.952"]),
    ("track10a.wav", "track20.ogg", ["gain", "-8"]),
    ("track22.wav", "track21.ogg", ["gain", "-6"]),
]


SE_AMBIENCE_TRACKS: list[tuple[str, str, list[str]]] = [
    ("AMB_RiverJungle_01.wav", "track25.ogg", ["gain", "-10"]),
    ("AMB_TownNightClock_01.wav", "track26.ogg", ["gain", "-10"]),
    ("AMB_TownNight_01.wav", "track27.ogg", ["gain", "-10"]),
    ("AMB_Underwater_01.wav", "track28.ogg", ["gain", "-10"]),
    ("AMB_ShipDeck_01.wav", "track29.ogg", ["gain", "-7"]),
]


def plan_mi1_music(audio: str) -> list[str]:
    return [
        "Decode MusicOriginal.xwb with vgmstream-cli.",
        f"Write classic CD tracks to cd_music_{audio}/.",
        "Decode MusicNew.xwb and Ambience.xwb with vgmstream-cli.",
        f"Write Special Edition music and ambience tracks to se_music_{audio}/.",
    ]


def _decode_bank(runner: Runner, bank: Path, dst: Path, label: str) -> None:
    if runner.verbose:
        runner.log(f"decode {label} {bank} -> {dst}")
    runner.run(["vgmstream-cli", "-i", "-S", "0", "-o", str(dst / "?n.wav"), bank])


def _sox_track(runner: Runner, src_dir: Path, src: str, out_dir: Path, dst: str, effects: list[str], label: str) -> None:
    require_file(src_dir / src)
    if runner.verbose:
        runner.log(f"{label} {dst} <- {src}")
    runner.run(["sox", src_dir / src, "-V0", out_dir / dst, *effects])


def process_mi1_music(options: Mi1MusicOptions) -> None:
    runner = Runner(options.dry_run, options.verbose)
    audio_dir = options.audio_dir.expanduser()
    out = options.out.expanduser()
    work = options.work.expanduser()
    audio = options.audio
    if audio != "ogg":
        raise BuildError("MI1 music conversion currently supports --audio ogg only")
    require_dir(audio_dir)
    require_file(audio_dir / "MusicOriginal.xwb")
    require_file(audio_dir / "MusicNew.xwb")
    require_file(audio_dir / "Ambience.xwb")
    runner.require_tool("sox", "install SoX to reproduce cdaudio.bat transforms")
    runner.require_tool("vgmstream-cli", "install vgmstream to decode XACT WMA music banks correctly")
    if not sox_can_write("ogg"):
        raise BuildError("MI1 music conversion requires SoX with Ogg/Vorbis write support")

    original = work / "original-wav"
    new = work / "new-wav"
    ambience = work / "ambience-wav"
    cd_out = out / f"cd_music_{audio}"
    se_out = out / f"se_music_{audio}"

    if options.dry_run:
        runner.log("Planned MI1 music conversion:")
        for step in plan_mi1_music(audio):
            runner.log(f"  {step}")
        return

    runner.clean_dir(work)
    for directory in (original, new, ambience, cd_out, se_out):
        directory.mkdir(parents=True, exist_ok=True)

    _decode_bank(runner, audio_dir / "MusicOriginal.xwb", original, "classic CD music")
    for src, dst, effects in CD_TRACKS:
        _sox_track(runner, original, src, cd_out, dst, effects, "cd music")

    _decode_bank(runner, audio_dir / "MusicNew.xwb", new, "Special Edition music")
    _decode_bank(runner, audio_dir / "Ambience.xwb", ambience, "Special Edition ambience")
    for src, dst, effects in SE_MUSIC_TRACKS:
        _sox_track(runner, new, src, se_out, dst, effects, "se music")

    require_file(ambience / "AMB_ScummBar_01.wav")
    require_file(new / "track9.wav")
    runner.run(["sox", ambience / "AMB_ScummBar_01.wav", "-V0", work / "temp-scummbar.wav", "trim", "0.000", "89.687"])
    runner.run(["sox", work / "temp-scummbar.wav", new / "track9.wav", "-m", "-V0", work / "track9o.wav"])
    runner.run(["sox", work / "track9o.wav", "-V0", se_out / "track8.ogg"])

    for src, dst in [("track23.wav", "track22.ogg"), ("track24.wav", "track23.ogg"), ("track25.wav", "track24.ogg")]:
        _sox_track(runner, original, src, se_out, dst, ["compand", "0.0,0.5", "-5.3,-5.3,-0,-5.3", "5", "-99"], "se music")
    for src, dst, effects in SE_AMBIENCE_TRACKS:
        _sox_track(runner, ambience, src, se_out, dst, effects, "se ambience")

    runner.log("MI1 music conversion complete.")
    runner.log(f"  classic CD music: {count_files(cd_out, '*.ogg')} files in {cd_out}")
    runner.log(f"  Special Edition music: {count_files(se_out, '*.ogg')} files in {se_out}")
