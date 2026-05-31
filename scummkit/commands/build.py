from __future__ import annotations

import argparse
from pathlib import Path

from .. import mi1, mi2
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    build = sub.add_parser("build", help="build an Ultimate Talkie output folder")
    games = build.add_subparsers(dest="game", required=True)

    def add_common(game_parser: argparse.ArgumentParser) -> None:
        game_parser.add_argument("--pak", type=Path, required=True)
        game_parser.add_argument("--builder", type=Path, required=True)
        game_parser.add_argument("--out", type=Path, required=True)
        game_parser.add_argument("--audio", choices=["ogg", "flac", "mp3", "raw"], required=True)
        game_parser.add_argument("--dry-run", action="store_true")
        game_parser.add_argument("--verbose", action="store_true")
        game_parser.add_argument(
            "--quiet",
            action="store_true",
            help="suppress external-tool chatter and show stage progress only",
        )

    mi1_parser = games.add_parser("mi1", help="build The Secret of Monkey Island Ultimate Talkie")
    add_common(mi1_parser)
    mi1_parser.add_argument(
        "--music",
        choices=["cd", "hybrid", "se"],
        default="hybrid",
        help="root soundtrack set for MI1; default: hybrid",
    )
    mi1_parser.add_argument("--skip-sbl", action="store_true")
    mi1_parser.add_argument("--skip-music", action="store_true")

    mi2_parser = games.add_parser("mi2", help="build Monkey Island 2 Ultimate Talkie")
    add_common(mi2_parser)


def run(args: argparse.Namespace) -> None:
    if args.quiet and args.verbose:
        raise BuildError("use either --quiet or --verbose, not both")
    if args.game == "mi1":
        mi1.build(
            mi1.BuildOptions(
                pak=args.pak,
                builder=args.builder,
                out=args.out,
                audio=args.audio,
                music=args.music,
                dry_run=args.dry_run,
                verbose=args.verbose,
                quiet=args.quiet,
                skip_sbl=args.skip_sbl,
                skip_music=args.skip_music,
            )
        )
    elif args.game == "mi2":
        mi2.build(
            mi2.BuildOptions(
                pak=args.pak,
                builder=args.builder,
                out=args.out,
                audio=args.audio,
                dry_run=args.dry_run,
                verbose=args.verbose,
                quiet=args.quiet,
            )
        )
    else:
        raise ValueError("unsupported build game")
