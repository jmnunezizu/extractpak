from __future__ import annotations

import argparse

from .commands import build, inspect, monster, sbl, xwb
from .runner import BuildError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scummkit")
    sub = parser.add_subparsers(dest="command", required=True)
    build.register(sub)
    xwb.register(sub)
    monster.register(sub)
    sbl.register_wav2sbl(sub)
    sbl.register_inject(sub)
    inspect.register(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            build.run(args)
        elif args.command == "inspect":
            inspect.run(args)
        elif args.command == "xwb":
            xwb.run(parser, args)
        elif args.command == "monster":
            monster.run(parser, args)
        elif args.command == "wav2sbl":
            sbl.run_wav2sbl(parser, args)
        elif args.command == "inject" and args.game == "mi1" and args.inject_action == "sbl":
            sbl.run_inject_mi1_sbl(args)
        else:
            parser.error("unsupported command")
        return 0
    except BuildError as error:
        parser.exit(1, f"error: {error}\n")
