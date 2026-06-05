from __future__ import annotations

import argparse
from pathlib import Path

from ..builders import BuildSpec, all_builders
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    build = sub.add_parser("build", help="build an Ultimate Talkie output folder")
    games = build.add_subparsers(dest="game", required=True)

    def add_common(game_parser: argparse.ArgumentParser) -> None:
        game_parser.add_argument("--pak", type=Path, required=True)
        game_parser.add_argument(
            "--builder",
            type=Path,
            help="optional original Ultimate Talkie builder folder; defaults to bundled patch/table data",
        )
        game_parser.add_argument("--out", type=Path, required=True)
        game_parser.add_argument("--audio", choices=["ogg", "flac", "mp3", "raw"], required=True)
        game_parser.add_argument("--dry-run", action="store_true")
        game_parser.add_argument("--verbose", action="store_true")
        progress = game_parser.add_mutually_exclusive_group()
        progress.add_argument(
            "--quiet",
            dest="quiet",
            action="store_true",
            default=None,
            help="show progress-oriented output; this is the default",
        )
        progress.add_argument(
            "--no-progress",
            dest="quiet",
            action="store_false",
            help="use plain stage output instead of progress-oriented output",
        )

    for spec in all_builders():
        game_parser = games.add_parser(spec.game, help=spec.help)
        add_common(game_parser)
        spec.add_arguments(game_parser)
        game_parser.set_defaults(func=run, build_spec=spec)


def run(args: argparse.Namespace) -> None:
    if args.quiet and args.verbose:
        raise BuildError("use either --quiet or --verbose, not both")
    spec: BuildSpec = args.build_spec
    spec.run(spec.build_options(args))
