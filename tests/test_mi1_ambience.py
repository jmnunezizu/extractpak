import struct
from pathlib import Path

from scummkit import mi1_ambience


def _write_tiny_xwb(path: Path) -> None:
    header = bytearray(0x100)
    header[:4] = b"WBND"
    struct.pack_into("<II", header, 4, 45, 43)
    bank_offset = 0x100
    metadata_offset = 0x180
    names_offset = 0x1C0
    wave_offset = 0x300
    segments = [
        (bank_offset, 0x5C),
        (metadata_offset, 48),
        (0, 0),
        (names_offset, 128),
        (wave_offset, 8),
    ]
    for index, (offset, length) in enumerate(segments):
        struct.pack_into("<II", header, 0x0C + index * 8, offset, length)

    bank = bytearray(0x5C)
    struct.pack_into("<II", bank, 0, 0, 2)
    bank[8:16] = b"Ambient"
    struct.pack_into("<IIII", bank, 72, 24, 64, 1, 0)
    format_value = 0 | (1 << 2) | (22050 << 5)
    metadata = (
        struct.pack("<IIIIII", 4 << 4, format_value, 0, 4, 0, 0)
        + struct.pack("<IIIIII", 4 << 4, format_value, 4, 4, 0, 0)
    )
    names = b"unused\0" + b"\0" * 57 + b"AMB_MeleeMap_01\0" + b"\0" * 49

    blob = bytes(header)
    blob += b"\0" * (bank_offset - len(blob)) + bytes(bank)
    blob += b"\0" * (metadata_offset - len(blob)) + metadata
    blob += b"\0" * (names_offset - len(blob)) + names
    blob += b"\0" * (wave_offset - len(blob)) + b"\x80\x81\x82\x83\x84\x85\x86\x87"
    path.write_bytes(blob)


def test_parse_mi1_ambience_cues_maps_cue_to_wave(tmp_path: Path) -> None:
    cues = tmp_path / "AmbienceCues.xsb"
    ambience = tmp_path / "Ambience.xwb"
    _write_tiny_xwb(ambience)

    data = bytearray(b"SDBK" + b"\0" * 0x240)
    sound_record = 0x40
    pointer_table = 0x100
    cue_table = 0x120
    string_start = 0x200
    data[sound_record : sound_record + 12] = b"\0\0\0\0\xff\x0c\x01\x00\x00\xff\0\0"
    data[pointer_table : pointer_table + 5] = b"\x04" + struct.pack("<I", sound_record)
    data[cue_table : cue_table + 6] = struct.pack("<HI", 0, string_start)
    data[cue_table + 6 : cue_table + 12] = struct.pack("<HI", 0xFFFF, string_start + 9)
    data[string_start : string_start + 9] = b"01_Beach\0"
    data[string_start + 9 : string_start + 20] = b"36_Mansion\0"
    cues.write_bytes(data)

    parsed = mi1_ambience.parse_mi1_ambience_cues(cues, ambience)

    assert parsed[0].name == "01_Beach"
    assert parsed[0].wave_index == 1
    assert parsed[0].wave_name == "AMB_MeleeMap_01"
    assert parsed[1].name == "36_Mansion"
    assert parsed[1].sound_index is None
