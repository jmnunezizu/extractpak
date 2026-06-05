from __future__ import annotations

import argparse
from pathlib import Path

from .. import bsdiff
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("bsdiff-inspect", help="inspect a BSDIFF40 patch file")
    parser.add_argument("patch", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--limit", type=int, default=20)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    try:
        summary, controls = bsdiff.parse_patch(args.patch.expanduser())
    except (OSError, bsdiff.BsdiffError) as error:
        raise BuildError(str(error)) from error

    print(f"BSDIFF patch: {args.patch}")
    print(f"  patch size: {summary.patch_size}")
    print(f"  new size: {summary.new_size}")
    print(f"  controls: {summary.control_count}")
    print(
        "  compressed blocks: "
        f"control={summary.control_block_compressed_size} "
        f"diff={summary.diff_block_compressed_size} "
        f"extra={summary.extra_block_compressed_size}"
    )
    print(
        "  raw blocks: "
        f"control={summary.control_block_size} "
        f"diff={summary.diff_block_size} "
        f"extra={summary.extra_block_size}"
    )
    print(f"  largest extra segment: {summary.largest_extra_len}")
    extras = sorted((item for item in controls if item.extra_len), key=lambda item: item.extra_len, reverse=True)
    if extras:
        print("  largest extra controls:")
        for item in extras[: args.limit]:
            print(
                f"    control={item.index} extra={item.extra_len} "
                f"new={item.new_diff_end}->{item.new_extra_end} old_after_diff={item.old_end}"
            )
    if args.json_out is not None:
        out = args.json_out.expanduser()
        bsdiff.write_report(out, summary, controls, args.limit)
        print(f"json: {out}")
