import bz2
from pathlib import Path

from scummkit import bsdiff


def _offtout(value: int) -> bytes:
    negative = value < 0
    value = abs(value)
    data = bytearray(8)
    for index in range(8):
        data[index] = value & 0xFF
        value >>= 8
    if negative:
        data[7] |= 0x80
    return bytes(data)


def test_parse_tiny_bsdiff_patch(tmp_path: Path) -> None:
    patch = tmp_path / "tiny.bsdiff"
    control = _offtout(3) + _offtout(2) + _offtout(-1)
    diff = b"abc"
    extra = b"xy"
    control_z = bz2.compress(control)
    diff_z = bz2.compress(diff)
    extra_z = bz2.compress(extra)
    patch.write_bytes(b"BSDIFF40" + _offtout(len(control_z)) + _offtout(len(diff_z)) + _offtout(5) + control_z + diff_z + extra_z)

    summary, controls = bsdiff.parse_patch(patch)

    assert summary.new_size == 5
    assert summary.control_count == 1
    assert summary.total_diff_bytes == 3
    assert summary.total_extra_bytes == 2
    assert summary.seek_backward == 1
    assert controls[0].new_diff_end == 3
    assert controls[0].new_extra_end == 5
