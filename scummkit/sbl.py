#!/usr/bin/env python3
import argparse
import struct
import sys
import wave
from pathlib import Path


class SblError(Exception):
    pass


def be24(value):
    if value < 0 or value > 0xFFFFFF:
        raise SblError(f"value does not fit in 24 bits: {value}")
    return bytes([(value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])


def read_pcm_u8_mono(path):
    if not path.is_file():
        raise SblError(f"missing WAV file: {path}")
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        frames = wav.getnframes()
        rate = wav.getframerate()
        compression = wav.getcomptype()
        if compression != "NONE":
            raise SblError(f"unsupported WAV compression: {compression}")
        if channels != 1:
            raise SblError(f"unsupported WAV channel count: {channels}; expected mono")
        if sample_width != 1:
            raise SblError(f"unsupported WAV sample width: {sample_width * 8}; expected 8-bit")
        data = wav.readframes(frames)
    return rate, data


def wav_to_sbl_bytes(path):
    _rate, data = read_pcm_u8_mono(path)
    data_size = len(data)
    if data_size > 0xFFFFFD:
        raise SblError(f"WAV data is too large for wav2sbl-compatible SBL: {data_size}")

    # This mirrors the original wav2sbl.exe byte layout:
    # SBL size = payload bytes after the SBL size field.
    # AUhd/AUdt sizes are payload sizes, not chunk-total sizes.
    sbl_payload_size = data_size + 0x1A
    audt_payload_size = data_size + 0x07
    data_size_plus_two = data_size + 0x02

    return b"".join(
        [
            b"SBL ",
            b"\x00" + be24(sbl_payload_size),
            b"AUhd",
            b"\x00\x00\x00\x03",
            b"\x00\x00\x80",
            b"AUdt",
            b"\x00" + be24(audt_payload_size),
            b"\x01",
            be24(data_size_plus_two)[::-1],
            b"\xD2\x00",
            data,
            b"\x00",
        ]
    )


def dump_info(path):
    if not path.is_file():
        raise SblError(f"missing SBL file: {path}")
    data = path.read_bytes()
    if len(data) < 33 or data[:4] != b"SBL ":
        raise SblError("not an SBL file")
    sbl_size = int.from_bytes(data[4:8], "big")
    audt_offset = data.find(b"AUdt")
    if audt_offset < 0:
        raise SblError("SBL file has no AUdt chunk")
    audt_size = int.from_bytes(data[audt_offset + 4 : audt_offset + 8], "big")
    print(f"path: {path}")
    print(f"sbl payload size: {sbl_size}")
    print(f"file size: {len(data)}")
    print(f"audt payload size: {audt_size}")
    print(f"sample bytes: {max(audt_size - 7, 0)}")


def main():
    parser = argparse.ArgumentParser(description="Convert 8-bit mono PCM WAV to MI1 SBL chunk")
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--verify", type=Path, help="dump information about an existing SBL file")
    args = parser.parse_args()

    try:
        if args.verify:
            dump_info(args.verify)
            return 0
        if not args.input or not args.output:
            parser.error("input and output are required unless --verify is used")
        args.output.write_bytes(wav_to_sbl_bytes(args.input))
        return 0
    except (OSError, wave.Error, SblError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
