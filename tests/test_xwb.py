import struct
from pathlib import Path

from talkiebuilder import xwb


def test_decode_format_pcm() -> None:
    value = 0 | (1 << 2) | (22050 << 5) | (0 << 31)
    assert xwb.decode_format(value) == {
        "tag": xwb.FORMAT_PCM,
        "channels": 1,
        "sample_rate": 22050,
        "block_align": 1,
        "bits_per_sample": 8,
    }


def test_safe_name_falls_back_for_empty() -> None:
    assert xwb.safe_name("", 7) == "00000007.wav"


def test_parse_minimal_xwb(tmp_path: Path) -> None:
    path = tmp_path / "tiny.xwb"
    header = bytearray(0x100)
    header[:4] = b"WBND"
    struct.pack_into("<II", header, 4, 45, 43)
    bank_offset = 0x100
    metadata_offset = 0x180
    names_offset = 0x1A0
    wave_offset = 0x200
    segments = [
        (bank_offset, 0x5C),
        (metadata_offset, 24),
        (0, 0),
        (names_offset, 64),
        (wave_offset, 4),
    ]
    for i, (offset, length) in enumerate(segments):
        struct.pack_into("<II", header, 0x0C + i * 8, offset, length)

    bank = bytearray(0x5C)
    struct.pack_into("<II", bank, 0, 0, 1)
    bank[8:12] = b"Test"
    struct.pack_into("<IIII", bank, 72, 24, 64, 1, 0)
    format_value = 0 | (1 << 2) | (22050 << 5)
    metadata = struct.pack("<IIIIII", 4 << 4, format_value, 0, 4, 0, 0)
    name = b"sample" + b"\0" * 58
    blob = bytes(header)
    blob += b"\0" * (bank_offset - len(blob)) + bytes(bank)
    blob += b"\0" * (metadata_offset - len(blob)) + metadata
    blob += b"\0" * (names_offset - len(blob)) + name
    blob += b"\0" * (wave_offset - len(blob)) + b"\x80\x81\x82\x83"
    path.write_bytes(blob)

    parsed = xwb.parse_xwb(path)

    assert parsed["bank_name"] == "Test"
    assert parsed["entries"][0]["name"] == "sample"
