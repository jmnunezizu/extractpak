from __future__ import annotations

import argparse
from pathlib import Path

from .. import monster
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("monster", help="build or verify a ScummVM speech archive")
    parser.add_argument("--table", help="monster.tbl path")
    parser.add_argument("--samples", help="processed sample directory")
    parser.add_argument("--out", help="output archive path")
    parser.add_argument("--format", choices=sorted(monster.FORMATS), help="archive audio format")
    parser.add_argument("--dry-run", action="store_true", help="print planned work without writing output")
    parser.add_argument("--verbose", action="store_true", help="print every packed file")
    parser.add_argument("--verify", help="verify an existing archive instead of building")


def run(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.verify:
        monster.verify_archive(Path(args.verify))
        return
    missing_args = [name for name in ("table", "samples", "out", "format") if getattr(args, name) is None]
    if missing_args:
        parser.error("missing required arguments: " + ", ".join("--" + name for name in missing_args))
    try:
        monster.build_archive(args)
    except monster.MonsterError as error:
        raise BuildError(str(error)) from error
