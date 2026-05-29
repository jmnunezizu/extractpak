#!/usr/bin/env python3
"""Extract PCM/ADPCM entries from Microsoft XACT wave banks."""

import argparse
import os
import re
import struct
import sys
from pathlib import Path


SEGMENT_COUNT = 5
ENTRY_NAME_LENGTH = 64
ENTRY_FULL_SIZE = 24

FORMAT_PCM = 0
FORMAT_XMA = 1
FORMAT_ADPCM = 2
FORMAT_WMA = 3

class XwbError(Exception):
    pass


def read_u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def decode_format(value):
    tag = value & 0x3
    channels = (value >> 2) & 0x7
    sample_rate = (value >> 5) & 0x3FFFF
    block_align = (value >> 23) & 0xFF
    bits_per_sample_flag = (value >> 31) & 0x1

    if tag == FORMAT_PCM:
        bits_per_sample = 16 if bits_per_sample_flag else 8
        block_align = channels * bits_per_sample // 8
    elif tag == FORMAT_ADPCM:
        bits_per_sample = 4
    else:
        bits_per_sample = 16 if bits_per_sample_flag else 8

    return {
        "tag": tag,
        "channels": channels,
        "sample_rate": sample_rate,
        "block_align": block_align,
        "bits_per_sample": bits_per_sample,
    }


def format_name(tag):
    return {
        FORMAT_PCM: "pcm",
        FORMAT_XMA: "xma",
        FORMAT_ADPCM: "adpcm",
        FORMAT_WMA: "wma",
    }.get(tag, f"unknown-{tag}")


def safe_name(name, index):
    if not name:
        return f"{index:08x}.wav"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    if not name:
        name = f"{index:08x}"
    return f"{name}.wav"


def riff_chunk(chunk_id, payload):
    if len(chunk_id) != 4:
        raise ValueError("chunk id must be 4 bytes")
    padding = b"\0" if len(payload) % 2 else b""
    return chunk_id + struct.pack("<I", len(payload)) + payload + padding


def wav_header(entry, payload_size):
    fmt = entry["format"]
    channels = fmt["channels"]
    sample_rate = fmt["sample_rate"]
    block_align = fmt["block_align"]
    bits_per_sample = fmt["bits_per_sample"]
    duration = entry["duration"]

    if fmt["tag"] == FORMAT_PCM:
        avg_bytes = sample_rate * block_align
        fmt_payload = struct.pack(
            "<HHIIHH",
            0x0001,
            channels,
            sample_rate,
            avg_bytes,
            block_align,
            bits_per_sample,
        )
    elif fmt["tag"] == FORMAT_ADPCM:
        if channels < 1 or block_align == 0:
            raise XwbError(
                f"invalid ADPCM format: channels={channels} block_align={block_align}"
            )
        samples_per_block = block_align * 2 + 32
        wav_block_align = (block_align + 22) * channels
        avg_bytes = sample_rate * wav_block_align // samples_per_block
        coeff_payload = b"".join(
            struct.pack("<hh", coef1, coef2)
            for coef1, coef2 in (
                (256, 0),
                (512, -256),
                (0, 0),
                (192, 64),
                (240, 0),
                (460, -208),
                (392, -232),
            )
        )
        fmt_payload = (
            struct.pack(
                "<HHIIHHHH",
                0x0002,
                channels,
                sample_rate,
                avg_bytes,
                wav_block_align,
                bits_per_sample,
                32,
                samples_per_block,
            )
            + struct.pack("<H", 7)
            + coeff_payload
        )
    else:
        raise XwbError(f"unsupported codec: {format_name(fmt['tag'])}")

    fact_payload = struct.pack("<I", duration)
    data_header = b"data" + struct.pack("<I", payload_size)
    body_size = (
        4
        + len(riff_chunk(b"fmt ", fmt_payload))
        + len(riff_chunk(b"fact", fact_payload))
        + len(data_header)
        + payload_size
        + (payload_size % 2)
    )
    return (
        b"RIFF"
        + struct.pack("<I", body_size)
        + b"WAVE"
        + riff_chunk(b"fmt ", fmt_payload)
        + riff_chunk(b"fact", fact_payload)
        + data_header
    )


def parse_xwb(path):
    with path.open("rb") as f:
        header = f.read(0x100)
    if len(header) < 0x34 or header[:4] != b"WBND":
        raise XwbError(f"{path} is not an XACT wave bank")

    tool_version = read_u32(header, 4)
    format_version = read_u32(header, 8)
    segments = []
    for i in range(SEGMENT_COUNT):
        offset, length = struct.unpack_from("<II", header, 0x0C + i * 8)
        segments.append({"offset": offset, "length": length})

    bank_segment = segments[0]
    with path.open("rb") as f:
        f.seek(bank_segment["offset"])
        bank_data = f.read(bank_segment["length"])

    if len(bank_data) < 0x5C:
        raise XwbError("bank data segment is too small")

    flags = read_u32(bank_data, 0)
    entry_count = read_u32(bank_data, 4)
    bank_name = bank_data[8:72].split(b"\0", 1)[0].decode("ascii", "replace")
    entry_meta_size = read_u32(bank_data, 72)
    entry_name_size = read_u32(bank_data, 76)
    alignment = read_u32(bank_data, 80)
    compact_format = read_u32(bank_data, 84)

    if entry_meta_size != ENTRY_FULL_SIZE:
        raise XwbError(
            f"unsupported entry metadata size {entry_meta_size}; expected {ENTRY_FULL_SIZE}"
        )

    metadata_segment = segments[1]
    expected_metadata = entry_count * entry_meta_size
    if metadata_segment["length"] < expected_metadata:
        raise XwbError("entry metadata segment is shorter than entry count requires")

    with path.open("rb") as f:
        f.seek(metadata_segment["offset"])
        metadata = f.read(expected_metadata)

    names = []
    names_segment = segments[3]
    if names_segment["length"] and entry_name_size:
        with path.open("rb") as f:
            f.seek(names_segment["offset"])
            names_data = f.read(names_segment["length"])
        for i in range(entry_count):
            start = i * entry_name_size
            raw = names_data[start:start + entry_name_size]
            names.append(raw.split(b"\0", 1)[0].decode("ascii", "replace"))

    entries = []
    for i in range(entry_count):
        base = i * entry_meta_size
        flags_duration, format_value, play_offset, play_length, loop_start, loop_length = (
            struct.unpack_from("<IIIIII", metadata, base)
        )
        entries.append(
            {
                "index": i,
                "name": names[i] if i < len(names) else "",
                "flags": flags_duration & 0xF,
                "duration": flags_duration >> 4,
                "format_value": format_value,
                "format": decode_format(format_value),
                "play_offset": play_offset,
                "play_length": play_length,
                "loop_start": loop_start,
                "loop_length": loop_length,
            }
        )

    return {
        "tool_version": tool_version,
        "format_version": format_version,
        "segments": segments,
        "flags": flags,
        "entry_count": entry_count,
        "bank_name": bank_name,
        "entry_meta_size": entry_meta_size,
        "entry_name_size": entry_name_size,
        "alignment": alignment,
        "compact_format": compact_format,
        "entries": entries,
    }


def list_entries(bank):
    for entry in bank["entries"]:
        fmt = entry["format"]
        print(
            f"{entry['index']:08x} "
            f"name={entry['name'] or '-'} "
            f"format={format_name(fmt['tag'])} "
            f"channels={fmt['channels']} "
            f"rate={fmt['sample_rate']} "
            f"block_align={fmt['block_align']} "
            f"offset={entry['play_offset']} "
            f"size={entry['play_length']}"
        )


def extract_entries(path, out_dir, bank, verbose=False):
    wave_segment = bank["segments"][4]
    if wave_segment["length"] == 0:
        raise XwbError("wave data segment is empty")

    out_dir.mkdir(parents=True, exist_ok=True)
    extracted = 0
    skipped = 0

    with path.open("rb") as source:
        for entry in bank["entries"]:
            fmt = entry["format"]
            if fmt["tag"] not in (FORMAT_PCM, FORMAT_ADPCM):
                skipped += 1
                print(
                    f"unsupported: {entry['index']:08x} "
                    f"{entry['name'] or '-'} codec={format_name(fmt['tag'])}",
                    file=sys.stderr,
                )
                continue

            data_offset = wave_segment["offset"] + entry["play_offset"]
            data_size = entry["play_length"]
            if data_offset + data_size > wave_segment["offset"] + wave_segment["length"]:
                raise XwbError(f"entry {entry['index']:08x} extends past wave data")

            filename = safe_name(entry["name"], entry["index"])
            destination = out_dir / filename
            header = wav_header(entry, data_size)

            source.seek(data_offset)
            with destination.open("wb") as target:
                target.write(header)
                remaining = data_size
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise XwbError(f"unexpected EOF reading entry {entry['index']:08x}")
                    target.write(chunk)
                    remaining -= len(chunk)
                if data_size % 2:
                    target.write(b"\0")

            extracted += 1
            if verbose:
                print(
                    f"extracted {destination} "
                    f"codec={format_name(fmt['tag'])} "
                    f"channels={fmt['channels']} "
                    f"rate={fmt['sample_rate']} "
                    f"bytes={destination.stat().st_size}"
                )

    return extracted, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="input .xwb file")
    parser.add_argument("output_dir", type=Path, nargs="?", help="output directory")
    parser.add_argument("--list", action="store_true", help="list entries")
    parser.add_argument("--verbose", action="store_true", help="print extracted files")
    args = parser.parse_args()

    try:
        bank = parse_xwb(args.input)
        print(
            f"{args.input}: XACT wave bank "
            f"tool={bank['tool_version']} format={bank['format_version']} "
            f"name={bank['bank_name']} entries={bank['entry_count']}"
        )

        if args.list:
            list_entries(bank)

        if args.output_dir is not None:
            extracted, skipped = extract_entries(
                args.input, args.output_dir, bank, verbose=args.verbose
            )
            print(
                f"Extracted {extracted} WAV files from {args.input.name}"
                + (f" ({skipped} unsupported)" if skipped else "")
            )
        elif not args.list:
            parser.error("output_dir is required unless --list is used")
    except XwbError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
