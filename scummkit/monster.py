#!/usr/bin/env python3
"""Build and verify ScummVM compressed MONSTER speech archives."""

from __future__ import annotations

import argparse
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


FORMATS = {
    "ogg": {
        "ext": ".ogg",
        "magic": b"OggS",
        "default_name": "monkey2.sog",
    },
    "flac": {
        "ext": ".flac",
        "magic": b"fLaC",
        "default_name": "monkey2.sof",
    },
    "mp3": {
        "ext": ".mp3",
        "magic": None,
        "default_name": "monkey2.so3",
    },
    "raw": {
        "ext": ".wav",
        "magic": None,
        "default_name": "monster.sou",
    },
}


class MonsterError(RuntimeError):
    pass


@dataclass(frozen=True)
class MonsterSummary:
    referenced: int
    packed: int
    missing: int
    unreferenced: int
    size: int


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_table(path: Path) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    with path.open("r", encoding="ascii", newline=None) as f:
        for line_no, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            if len(line) < 9:
                die(f"{path}:{line_no}: table line is too short: {line!r}")
            offset_text = line[:8]
            try:
                offset = int(offset_text, 16)
            except ValueError:
                die(f"{path}:{line_no}: invalid hex offset: {offset_text!r}")
            name = line[8:]
            if "/" in name or "\\" in name:
                die(f"{path}:{line_no}: sample name must be a basename: {name!r}")
            entries.append((offset, name))

    if not entries:
        die(f"{path}: no monster table entries found")

    offsets = [offset for offset, _name in entries]
    if offsets != sorted(offsets):
        print("warning: monster table offsets are not sorted; output will preserve table order", file=sys.stderr)
    if len(offsets) != len(set(offsets)):
        print("warning: monster table contains duplicate original offsets", file=sys.stderr)

    return entries


def parse_table_or_raise(path: Path) -> list[tuple[int, str]]:
    try:
        return parse_table(path)
    except SystemExit as error:
        raise MonsterError(f"failed to parse monster table: {path}") from error


def sample_files(samples: Path, ext: str) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(samples.glob(f"*{ext}")):
        if path.is_file():
            files[path.stem] = path
    return files


def validate_payload(path: Path, fmt: str) -> None:
    magic = FORMATS[fmt]["magic"]
    if magic is None:
        return
    with path.open("rb") as f:
        head = f.read(len(magic))
    if head != magic:
        print(f"warning: {path} does not start with expected {fmt} magic", file=sys.stderr)


def _build_archive(
    table: Path,
    samples: Path,
    out: Path,
    fmt: str,
    dry_run: bool = False,
    verbose: bool = False,
    quiet: bool = False,
) -> MonsterSummary:
    if fmt == "raw":
        raise MonsterError("raw monster.sou generation is not implemented yet; use ogg, flac, or mp3")
    if fmt not in FORMATS:
        raise MonsterError(f"unsupported archive audio format: {fmt}; use one of: {', '.join(sorted(FORMATS))}")
    ext = FORMATS[fmt]["ext"]

    if not table.is_file():
        raise MonsterError(f"missing monster table: {table}")
    if not samples.is_dir():
        raise MonsterError(f"missing samples directory: {samples}")

    entries = parse_table_or_raise(table)
    available = sample_files(samples, ext)

    referenced_names = {name for _offset, name in entries}
    missing = [(offset, name) for offset, name in entries if name not in available]
    unreferenced = sorted(set(available) - referenced_names)
    packed_entries = [(offset, name, available[name]) for offset, name in entries if name in available]

    if missing:
        for offset, name in missing[:20]:
            print(f"warning: missing referenced sample {name}{ext} for offset 0x{offset:08x}", file=sys.stderr)
        if len(missing) > 20:
            print(f"warning: {len(missing) - 20} additional referenced samples are missing", file=sys.stderr)

    if unreferenced:
        for name in unreferenced[:20]:
            print(f"warning: unreferenced sample {name}{ext}", file=sys.stderr)
        if len(unreferenced) > 20:
            print(f"warning: {len(unreferenced) - 20} additional sample files are unreferenced", file=sys.stderr)

    if not packed_entries:
        raise MonsterError(
            f"no referenced samples are available to pack from {samples}; "
            f"expected files named by {table} with extension {ext}"
        )

    index_size = len(packed_entries) * 16
    data = bytearray()
    index = bytearray()

    if dry_run:
        final_size = 4 + index_size + sum(path.stat().st_size for _offset, _name, path in packed_entries)
        summary = MonsterSummary(len(entries), len(packed_entries), len(missing), len(unreferenced), final_size)
        if not quiet:
            print_summary(summary)
            print(f"[dry-run] would write {out}")
        return summary

    out.parent.mkdir(parents=True, exist_ok=True)

    if quiet:
        print(f"  monster: packing {len(packed_entries)} referenced sample(s)")

    for index_no, (offset, name, path) in enumerate(packed_entries, 1):
        validate_payload(path, fmt)
        payload = path.read_bytes()
        if not payload:
            print(f"warning: referenced sample is empty: {path}", file=sys.stderr)
        if verbose:
            print(f"pack 0x{offset:08x} {name}{ext} bytes={len(payload)}")
        index.extend(struct.pack(">IIII", offset, len(data), 0, len(payload)))
        data.extend(payload)
        if quiet and (index_no == len(packed_entries) or index_no % 500 == 0):
            print(
                f"\r\033[K  monster: packed {index_no}/{len(packed_entries)} sample(s)",
                end="\n" if index_no == len(packed_entries) else "",
                flush=True,
            )

    tmp = out.with_suffix(out.suffix + ".tmp")
    with tmp.open("wb") as f:
        f.write(struct.pack(">I", index_size))
        f.write(index)
        f.write(data)
    os.replace(tmp, out)

    verify_archive(out, quiet=True)
    summary = MonsterSummary(len(entries), len(packed_entries), len(missing), len(unreferenced), out.stat().st_size)
    if not quiet:
        print_summary(summary)
        print(f"archive: {out}")
    return summary


def build_archive(args: argparse.Namespace) -> MonsterSummary:
    return _build_archive(
        Path(args.table),
        Path(args.samples),
        Path(args.out),
        args.format,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def build_monster_archive(
    table: Path,
    samples: Path,
    out: Path,
    fmt: str,
    dry_run: bool = False,
    verbose: bool = False,
    quiet: bool = False,
) -> MonsterSummary:
    return _build_archive(table, samples, out, fmt, dry_run=dry_run, verbose=verbose, quiet=quiet)


def print_summary(summary: MonsterSummary) -> None:
    print(f"referenced count: {summary.referenced}")
    print(f"packed count: {summary.packed}")
    print(f"missing count: {summary.missing}")
    print(f"unreferenced count: {summary.unreferenced}")
    print(f"final archive size: {summary.size}")


def verify_archive(path: Path, quiet: bool = False) -> None:
    if not path.is_file():
        die(f"missing archive: {path}")
    blob = path.read_bytes()
    if len(blob) < 4:
        die(f"{path}: archive is too small")
    index_size = struct.unpack_from(">I", blob, 0)[0]
    if index_size % 16 != 0:
        die(f"{path}: index size {index_size} is not a multiple of 16")
    index_start = 4
    data_start = index_start + index_size
    if data_start > len(blob):
        die(f"{path}: index extends beyond end of file")

    entries = []
    for pos in range(index_start, data_start, 16):
        org_offset, rel_offset, num_tags, payload_size = struct.unpack_from(">IIII", blob, pos)
        abs_offset = data_start + rel_offset
        payload_offset = abs_offset + num_tags
        payload_end = payload_offset + payload_size
        if payload_end > len(blob):
            die(f"{path}: entry 0x{org_offset:08x} extends beyond end of file")
        if payload_size == 0:
            print(f"warning: entry 0x{org_offset:08x} has zero-length payload", file=sys.stderr)
        entries.append((org_offset, rel_offset, num_tags, payload_size, abs_offset, payload_end))

    org_offsets = [entry[0] for entry in entries]
    rel_offsets = [entry[1] for entry in entries]
    if org_offsets != sorted(org_offsets):
        print("warning: original offsets are not sorted; ScummVM uses binary search on this table", file=sys.stderr)
    if rel_offsets != sorted(rel_offsets):
        die(f"{path}: data offsets are not sorted")

    for prev, cur in zip(entries, entries[1:]):
        if prev[5] > cur[4]:
            die(f"{path}: overlapping entries near 0x{prev[0]:08x}")

    if not quiet:
        print(f"archive: {path}")
        print(f"index size: {index_size}")
        print(f"entries: {len(entries)}")
        print(f"data bytes: {len(blob) - data_start}")
        print(f"archive size: {len(blob)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", help="monster.tbl path")
    parser.add_argument("--samples", help="processed sample directory")
    parser.add_argument("--out", help="output archive path")
    parser.add_argument("--format", choices=sorted(FORMATS), help="archive audio format")
    parser.add_argument("--dry-run", action="store_true", help="print planned work without writing output")
    parser.add_argument("--verbose", action="store_true", help="print every packed file")
    parser.add_argument("--verify", help="verify an existing archive instead of building")
    args = parser.parse_args()

    if args.verify:
        verify_archive(Path(args.verify))
        return

    missing_args = [name for name in ("table", "samples", "out", "format") if getattr(args, name) is None]
    if missing_args:
        die("missing required arguments: " + ", ".join("--" + name for name in missing_args))

    try:
        build_archive(args)
    except MonsterError as error:
        die(str(error))


if __name__ == "__main__":
    main()
