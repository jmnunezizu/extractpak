from __future__ import annotations

import argparse
from pathlib import Path

from . import mi1, mi2
from .runner import BuildError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="talkiebuilder")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build an Ultimate Talkie output folder")
    games = build.add_subparsers(dest="game", required=True)

    def add_common(game_parser: argparse.ArgumentParser) -> None:
        game_parser.add_argument("--pak", type=Path, required=True)
        game_parser.add_argument("--builder", type=Path, required=True)
        game_parser.add_argument("--out", type=Path, required=True)
        game_parser.add_argument("--audio", choices=["ogg", "flac", "mp3", "raw"], required=True)
        game_parser.add_argument("--dry-run", action="store_true")
        game_parser.add_argument("--verbose", action="store_true")

    mi1_parser = games.add_parser("mi1", help="build The Secret of Monkey Island Ultimate Talkie")
    add_common(mi1_parser)
    mi1_parser.add_argument("--skip-sbl", action="store_true")
    mi1_parser.add_argument("--skip-music", action="store_true")

    mi2_parser = games.add_parser("mi2", help="build Monkey Island 2 Ultimate Talkie")
    add_common(mi2_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build" and args.game == "mi1":
            mi1.build(
                mi1.BuildOptions(
                    pak=args.pak,
                    builder=args.builder,
                    out=args.out,
                    audio=args.audio,
                    dry_run=args.dry_run,
                    verbose=args.verbose,
                    skip_sbl=args.skip_sbl,
                    skip_music=args.skip_music,
                )
            )
        elif args.command == "build" and args.game == "mi2":
            mi2.build(
                mi2.BuildOptions(
                    pak=args.pak,
                    builder=args.builder,
                    out=args.out,
                    audio=args.audio,
                    dry_run=args.dry_run,
                    verbose=args.verbose,
                )
            )
        else:
            parser.error("unsupported command")
        return 0
    except BuildError as error:
        parser.exit(1, f"error: {error}\n")
