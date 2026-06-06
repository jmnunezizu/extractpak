from __future__ import annotations

import argparse

from . import __version__
from .commands import ambience, build, bsdiff_inspect, builder_inputs, doctor, inspect, monster, patch_diff, room_audio, sbl, script_refs, speech_manifest, xwb
from .runner import BuildError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scummkit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    ambience.register(sub)
    bsdiff_inspect.register(sub)
    build.register(sub)
    builder_inputs.register(sub)
    doctor.register(sub)
    patch_diff.register(sub)
    room_audio.register(sub)
    script_refs.register(sub)
    xwb.register(sub)
    monster.register(sub)
    speech_manifest.register(sub)
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
