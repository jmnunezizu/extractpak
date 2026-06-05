from __future__ import annotations

import argparse
from pathlib import Path

from .. import mi1_room_audio
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("room-audio-report", help="inspect room-level MI1 audio wiring")
    games = parser.add_subparsers(dest="game", required=True)

    mi1 = games.add_parser("mi1", help="summarise MI1 room sounds, scripts, ambience cues, and root tracks")
    mi1.add_argument("--game-dir", type=Path, required=True, help="generated MI1 output directory")
    mi1.add_argument("--room", type=int, required=True, help="room id to inspect")
    mi1.add_argument("--audio-dir", type=Path, help="optional MI1 Special Edition audio directory")
    mi1.add_argument("--audio", default="ogg", help="root track extension; default: ogg")
    mi1.add_argument("--json-out", type=Path, help="optional JSON report path")
    mi1.set_defaults(func=run_mi1)


def _format_opcodes(opcodes: list[mi1_room_audio.RoomAudioOpcode]) -> str:
    if not opcodes:
        return "-"
    return " ".join(f"{item.name}({item.argument if item.argument_kind == 'direct' else item.argument_kind})@{item.offset}" for item in opcodes)


def _format_decode_issues(issues: list[mi1_room_audio.RoomAudioDecodeIssue]) -> str:
    if not issues:
        return "-"
    return " ".join(
        f"0x{item.opcode:02x}@{item.offset}:{item.reason}" if item.opcode is not None else f"eof@{item.offset}:{item.reason}"
        for item in issues
    )


def run_mi1(args: argparse.Namespace) -> None:
    try:
        report = mi1_room_audio.build_report(
            game_dir=args.game_dir.expanduser(),
            audio_dir=args.audio_dir.expanduser() if args.audio_dir is not None else None,
            room_id=args.room,
            audio=args.audio,
        )
    except Exception as error:
        raise BuildError(str(error)) from error

    print(f"MI1 room audio report: room {report.room_id}")
    if report.ambience_cue_name is None:
        print("  ambience cue: none")
    else:
        source = report.ambience_wave_name if report.ambience_wave_name is not None else "unmapped"
        print(f"  ambience cue: {report.ambience_cue_name} -> {source}")

    print("  sounds:")
    if report.sounds:
        for sound in report.sounds:
            tags = ",".join(sound.child_tags) if sound.child_tags else "-"
            sbl = sound.native_sbl_source if sound.native_sbl_source is not None else "-"
            print(f"    SOUN {sound.sound_id:03d} size={sound.size} tags={tags} native_sbl={sbl}")
    else:
        print("    none")

    print("  scripts:")
    if report.scripts:
        for script in report.scripts:
            print(
                f"    SCRP {script.script_id:03d} size={script.size} "
                f"sound-byte-refs={script.referenced_sound_ids} "
                f"track-byte-refs={script.referenced_root_tracks} "
                f"audio-opcodes={_format_opcodes(script.audio_opcodes)} "
                f"decode-issues={_format_decode_issues(script.decode_issues)}"
            )
    else:
        print("    none")

    print("  embedded room scripts:")
    if report.embedded_scripts:
        for script in report.embedded_scripts:
            print(
                f"    {script.tag}#{script.index} offset={script.offset} size={script.size} "
                f"sound-byte-refs={script.referenced_sound_ids} "
                f"track-byte-refs={script.referenced_root_tracks} "
                f"audio-opcodes={_format_opcodes(script.audio_opcodes)} "
                f"decode-issues={_format_decode_issues(script.decode_issues)}"
            )
    else:
        print("    none")

    print("  root tracks:")
    print(f"    present: {len(report.root_tracks)}")

    if args.json_out is not None:
        out = args.json_out.expanduser()
        mi1_room_audio.write_report(out, report)
        print(f"json: {out}")
