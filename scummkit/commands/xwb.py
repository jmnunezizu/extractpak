from __future__ import annotations

import argparse
from functools import partial
from pathlib import Path

from .. import xwb
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("xwb", help="inspect or extract an XACT wave bank")
    parser.add_argument("input", type=Path, help="input .xwb file")
    parser.add_argument("output_dir", type=Path, nargs="?", help="output directory")
    parser.add_argument("--list", action="store_true", help="list entries")
    parser.add_argument("--verbose", action="store_true", help="print extracted files")
    parser.add_argument(
        "--decode-wma",
        action="store_true",
        help="decode XACT WMA entries via ffmpeg after wrapping them as XWMA",
    )
    parser.set_defaults(func=partial(run, parser))


def run(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    try:
        bank = xwb.parse_xwb(args.input)
        print(
            f"{args.input}: XACT wave bank "
            f"tool={bank['tool_version']} format={bank['format_version']} "
            f"name={bank['bank_name']} entries={bank['entry_count']}"
        )
        if args.list:
            xwb.list_entries(bank)
        if args.output_dir is not None:
            extracted, skipped = xwb.extract_entries(
                args.input,
                args.output_dir,
                bank,
                verbose=args.verbose,
                decode_wma=args.decode_wma,
            )
            print(
                f"Extracted {extracted} WAV files from {args.input.name}"
                + (f" ({skipped} unsupported)" if skipped else "")
            )
        elif not args.list:
            parser.error("output_dir is required unless --list is used")
    except xwb.XwbError as error:
        raise BuildError(str(error)) from error
