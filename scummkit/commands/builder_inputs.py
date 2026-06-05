from __future__ import annotations

import argparse
from pathlib import Path

from ..builder_inputs import format_dependency_report


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("builder-inputs", help="report Ultimate Talkie patch/table data sources")
    parser.add_argument("game", choices=["mi1", "mi2"])
    parser.add_argument("--builder", type=Path, help="optional original builder directory to check instead of bundled data")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    builder = args.builder.expanduser() if args.builder is not None else None
    print(format_dependency_report(args.game, builder))
