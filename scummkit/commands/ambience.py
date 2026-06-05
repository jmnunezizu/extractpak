from __future__ import annotations

import argparse
from pathlib import Path

from .. import mi1_ambience
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("ambience-report", help="inspect Special Edition ambience cue mappings")
    games = parser.add_subparsers(dest="game", required=True)

    mi1 = games.add_parser("mi1", help="map MI1 AmbienceCues.xsb cues to Ambience.xwb entries")
    mi1.add_argument("--audio-dir", type=Path, required=True, help="MI1 Special Edition audio directory")
    mi1.add_argument("--json-out", type=Path, help="optional JSON report path")
    mi1.add_argument("--filter", help="case-insensitive cue-name filter")
    mi1.set_defaults(func=run_mi1)


def run_mi1(args: argparse.Namespace) -> None:
    audio_dir = args.audio_dir.expanduser()
    cues_path = audio_dir / "AmbienceCues.xsb"
    ambience_xwb = audio_dir / "Ambience.xwb"
    try:
        cues = mi1_ambience.parse_mi1_ambience_cues(cues_path, ambience_xwb)
    except (OSError, mi1_ambience.AmbienceCueError) as error:
        raise BuildError(str(error)) from error

    shown = cues
    if args.filter:
        needle = args.filter.lower()
        shown = [cue for cue in cues if needle in cue.name.lower()]

    summary = mi1_ambience.payload(cues)["summary"]
    print("MI1 ambience cues:")
    print(f"  total: {summary['total']}")
    print(f"  mapped: {summary['mapped']}")
    print(f"  unmapped: {summary['unmapped']}")
    for cue in shown:
        source = cue.wave_name if cue.wave_name is not None else "unmapped"
        sound = "-" if cue.sound_index is None else str(cue.sound_index)
        wave = "-" if cue.wave_index is None else str(cue.wave_index)
        print(f"  {cue.name:<24} sound={sound:<3} wave={wave:<3} source={source}")

    if args.json_out is not None:
        out = args.json_out.expanduser()
        mi1_ambience.write_report(out, cues)
        print(f"json: {out}")
