from __future__ import annotations

import argparse

from .. import mi2
from . import BuildSpec, resolve_quiet


def add_arguments(parser: argparse.ArgumentParser) -> None:
    pass


def build_options(args: argparse.Namespace) -> mi2.BuildOptions:
    return mi2.BuildOptions(
        pak=args.pak,
        builder=args.builder,
        out=args.out,
        audio=args.audio,
        dry_run=args.dry_run,
        verbose=args.verbose,
        quiet=resolve_quiet(args),
    )


def run(options: mi2.BuildOptions) -> None:
    mi2.build(options)


SPEC = BuildSpec(
    game="mi2",
    title="Monkey Island 2 Ultimate Talkie",
    help="build Monkey Island 2 Ultimate Talkie",
    add_arguments=add_arguments,
    build_options=build_options,
    run=run,
)
