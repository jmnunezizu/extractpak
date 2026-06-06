from __future__ import annotations

import argparse

from .. import mi1
from . import BuildSpec, resolve_quiet


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--music",
        choices=["cd", "hybrid", "se"],
        default="hybrid",
        help="root soundtrack set for MI1; default: hybrid",
    )
    parser.add_argument("--skip-sbl", action="store_true")
    parser.add_argument("--skip-music", action="store_true")


def build_options(args: argparse.Namespace) -> mi1.BuildOptions:
    return mi1.BuildOptions(
        pak=args.pak,
        builder=args.builder,
        out=args.out,
        audio=args.audio,
        music=args.music,
        dry_run=args.dry_run,
        verbose=args.verbose,
        quiet=resolve_quiet(args),
        skip_sbl=args.skip_sbl,
        skip_music=args.skip_music,
    )


def run(options: mi1.BuildOptions) -> None:
    mi1.build(options)


SPEC = BuildSpec(
    game="mi1",
    title="The Secret of Monkey Island Ultimate Talkie",
    help="build The Secret of Monkey Island Ultimate Talkie",
    audio_choices=mi1.SUPPORTED_AUDIO,
    add_arguments=add_arguments,
    build_options=build_options,
    run=run,
)
