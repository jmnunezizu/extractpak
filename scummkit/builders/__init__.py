from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class BuildSpec:
    game: str
    title: str
    help: str
    add_arguments: Callable[[argparse.ArgumentParser], None]
    build_options: Callable[[argparse.Namespace], Any]
    run: Callable[[Any], None]


def resolve_quiet(args: argparse.Namespace) -> bool:
    return (args.quiet if args.quiet is not None else True) and not args.verbose


def all_builders() -> list[BuildSpec]:
    from . import mi1, mi2

    return [mi1.SPEC, mi2.SPEC]
