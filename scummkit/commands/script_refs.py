from __future__ import annotations

import argparse
from pathlib import Path

from .. import mi1_script_refs
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("script-reference-report", help="scan MI1 scripts for candidate byte references")
    games = parser.add_subparsers(dest="game", required=True)

    mi1 = games.add_parser("mi1", help="scan MI1 script resources for room/sound/track byte references")
    mi1.add_argument("--game-dir", type=Path, required=True, help="generated MI1 output directory")
    mi1.add_argument("--rooms", required=True, help="comma-separated room ids to scan for")
    mi1.add_argument("--sounds", default="", help="comma-separated sound ids to scan for")
    mi1.add_argument("--tracks", default="", help="comma-separated root track ids to scan for")
    mi1.add_argument("--offset-limit", type=int, default=12, help="offsets to keep per value; default: 12")
    mi1.add_argument("--limit", type=int, default=40, help="scripts to print; default: 40")
    mi1.add_argument("--json-out", type=Path, help="optional JSON report path")
    mi1.set_defaults(func=run_mi1)


def _parse_ids(text: str) -> list[int]:
    if not text:
        return []
    values: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            values.append(int(part, 0))
        except ValueError as error:
            raise BuildError(f"invalid numeric id: {part!r}") from error
    return values


def _format_refs(refs: list[mi1_script_refs.ByteReference]) -> str:
    if not refs:
        return "-"
    parts = []
    for ref in refs:
        offsets = ",".join(str(offset) for offset in ref.offsets)
        suffix = f"+{ref.count - len(ref.offsets)}" if ref.count > len(ref.offsets) else ""
        parts.append(f"{ref.value}@[{offsets}{suffix}]")
    return " ".join(parts)


def run_mi1(args: argparse.Namespace) -> None:
    try:
        report = mi1_script_refs.build_report(
            game_dir=args.game_dir.expanduser(),
            rooms=_parse_ids(args.rooms),
            sounds=_parse_ids(args.sounds),
            tracks=_parse_ids(args.tracks),
            offset_limit=args.offset_limit,
        )
    except (OSError, mi1_script_refs.mi1_resources.BuildError) as error:
        raise BuildError(str(error)) from error

    print("MI1 script reference report:")
    print(f"  rooms: {report.rooms}")
    print(f"  sounds: {report.sounds}")
    print(f"  tracks: {report.tracks}")
    print(f"  matching scripts: {len(report.scripts)}")
    for script in report.scripts[: args.limit]:
        print(
            f"  room={script.room_id:03d} script={script.script_id:03d} size={script.size} "
            f"rooms={_format_refs(script.room_refs)} "
            f"sounds={_format_refs(script.sound_refs)} "
            f"tracks={_format_refs(script.track_refs)}"
        )
    if len(report.scripts) > args.limit:
        print(f"  ... {len(report.scripts) - args.limit} more")

    if args.json_out is not None:
        out = args.json_out.expanduser()
        mi1_script_refs.write_report(out, report)
        print(f"json: {out}")
