from __future__ import annotations

import argparse
from pathlib import Path

from .. import mi1_sbl, sbl
from ..runner import BuildError


def register_wav2sbl(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("wav2sbl", help="convert 8-bit mono PCM WAV to MI1 SBL chunk")
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--verify", type=Path, help="dump information about an existing SBL file")


def register_inject(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    inject = sub.add_parser("inject", help="inject generated resources")
    inject_games = inject.add_subparsers(dest="game", required=True)
    inject_mi1 = inject_games.add_parser("mi1", help="MI1 injection helpers")
    inject_mi1_sub = inject_mi1.add_subparsers(dest="inject_action", required=True)
    inject_sbl = inject_mi1_sub.add_parser("sbl", help="inject MI1 SBL sound effects")
    inject_sbl.add_argument("--builder", required=True, type=Path)
    inject_sbl.add_argument("--samples-wav", required=True, type=Path)
    inject_sbl.add_argument("--monkey000", required=True, type=Path)
    inject_sbl.add_argument("--monkey001", required=True, type=Path)
    inject_sbl.add_argument("--work", required=True, type=Path)
    inject_sbl.add_argument("--sample-rate", type=int, default=22050)
    inject_sbl.add_argument("--dry-run", action="store_true")
    inject_sbl.add_argument("--verbose", action="store_true")


def run_wav2sbl(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    try:
        if args.verify:
            sbl.dump_info(args.verify)
            return
        if not args.input or not args.output:
            parser.error("input and output are required unless --verify is used")
        args.output.write_bytes(sbl.wav_to_sbl_bytes(args.input))
    except sbl.SblError as error:
        raise BuildError(str(error)) from error


def run_inject_mi1_sbl(args: argparse.Namespace) -> None:
    try:
        sbl_bat = args.builder / "tools" / "sbl.bat"
        if not sbl_bat.exists():
            raise mi1_sbl.InjectError(f"missing {sbl_bat}")
        if not args.samples_wav.is_dir():
            raise mi1_sbl.InjectError(f"missing samples WAV directory: {args.samples_wav}")
        commands = mi1_sbl.parse_sbl_bat(sbl_bat)
        print(f"Parsed {len(commands)} SBL injection commands from {sbl_bat}")
        if args.dry_run:
            for command in commands:
                print(
                    f"[dry-run] sound {command.sound_id:03d} room {command.room_id:03d} "
                    f"{command.source} effects={' '.join(command.effects) or '(none)'}"
                )
            return
        mi1_sbl.inject_mi1_sbl(
            args.builder,
            args.samples_wav,
            args.monkey000,
            args.monkey001,
            args.work,
            sample_rate=args.sample_rate,
            verbose=args.verbose,
        )
    except (OSError, mi1_sbl.InjectError, sbl.SblError) as error:
        raise BuildError(str(error)) from error
