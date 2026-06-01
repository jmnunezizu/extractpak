from __future__ import annotations

import argparse

from .commands import build, doctor, inspect, monster, sbl, xwb
from .runner import BuildError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scummkit")
    sub = parser.add_subparsers(dest="command", required=True)
    build.register(sub)
    doctor.register(sub)
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
        handler = getattr(args, "func", None)
        if handler is None:
            parser.error("unsupported command")
        handler(args)
        return 0
    except BuildError as error:
        parser.exit(1, f"error: {error}\n")
