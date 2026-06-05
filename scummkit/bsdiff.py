from __future__ import annotations

import bz2
import json
from dataclasses import asdict, dataclass
from pathlib import Path


class BsdiffError(RuntimeError):
    pass


@dataclass(frozen=True)
class BsdiffControl:
    index: int
    diff_len: int
    extra_len: int
    seek_adjust: int
    old_start: int
    old_end: int
    new_start: int
    new_diff_end: int
    new_extra_end: int


@dataclass(frozen=True)
class BsdiffSummary:
    patch_size: int
    control_block_compressed_size: int
    diff_block_compressed_size: int
    extra_block_compressed_size: int
    control_block_size: int
    diff_block_size: int
    extra_block_size: int
    new_size: int
    control_count: int
    total_diff_bytes: int
    total_extra_bytes: int
    seek_forward: int
    seek_backward: int
    largest_extra_len: int


def offtin(data: bytes) -> int:
    if len(data) != 8:
        raise BsdiffError("BSDIFF integer must be 8 bytes")
    value = data[7] & 0x7F
    for index in range(6, -1, -1):
        value = value * 256 + data[index]
    return -value if data[7] & 0x80 else value


def parse_patch(path: Path) -> tuple[BsdiffSummary, list[BsdiffControl]]:
    blob = path.read_bytes()
    if len(blob) < 32 or blob[:8] != b"BSDIFF40":
        raise BsdiffError(f"{path}: not a BSDIFF40 patch")
    control_compressed = offtin(blob[8:16])
    diff_compressed = offtin(blob[16:24])
    new_size = offtin(blob[24:32])
    if control_compressed < 0 or diff_compressed < 0 or new_size < 0:
        raise BsdiffError(f"{path}: invalid negative BSDIFF header size")
    control_start = 32
    diff_start = control_start + control_compressed
    extra_start = diff_start + diff_compressed
    if extra_start > len(blob):
        raise BsdiffError(f"{path}: BSDIFF blocks extend beyond patch file")

    control_block = bz2.decompress(blob[control_start:diff_start])
    diff_block = bz2.decompress(blob[diff_start:extra_start])
    extra_block = bz2.decompress(blob[extra_start:])
    if len(control_block) % 24 != 0:
        raise BsdiffError(f"{path}: control block size is not a multiple of 24")

    controls: list[BsdiffControl] = []
    old_pos = 0
    new_pos = 0
    total_diff = 0
    total_extra = 0
    seek_forward = 0
    seek_backward = 0
    largest_extra = 0
    for offset in range(0, len(control_block), 24):
        diff_len = offtin(control_block[offset : offset + 8])
        extra_len = offtin(control_block[offset + 8 : offset + 16])
        seek_adjust = offtin(control_block[offset + 16 : offset + 24])
        if diff_len < 0 or extra_len < 0:
            raise BsdiffError(f"{path}: negative diff/extra length in control {offset // 24}")
        controls.append(
            BsdiffControl(
                index=offset // 24,
                diff_len=diff_len,
                extra_len=extra_len,
                seek_adjust=seek_adjust,
                old_start=old_pos,
                old_end=old_pos + diff_len,
                new_start=new_pos,
                new_diff_end=new_pos + diff_len,
                new_extra_end=new_pos + diff_len + extra_len,
            )
        )
        total_diff += diff_len
        total_extra += extra_len
        largest_extra = max(largest_extra, extra_len)
        if seek_adjust >= 0:
            seek_forward += seek_adjust
        else:
            seek_backward += -seek_adjust
        old_pos += diff_len + seek_adjust
        new_pos += diff_len + extra_len

    if total_diff != len(diff_block):
        raise BsdiffError(f"{path}: diff block length mismatch")
    if total_extra != len(extra_block):
        raise BsdiffError(f"{path}: extra block length mismatch")
    if new_pos != new_size:
        raise BsdiffError(f"{path}: control stream produces {new_pos} bytes, expected {new_size}")

    return (
        BsdiffSummary(
            patch_size=len(blob),
            control_block_compressed_size=control_compressed,
            diff_block_compressed_size=diff_compressed,
            extra_block_compressed_size=len(blob) - extra_start,
            control_block_size=len(control_block),
            diff_block_size=len(diff_block),
            extra_block_size=len(extra_block),
            new_size=new_size,
            control_count=len(controls),
            total_diff_bytes=total_diff,
            total_extra_bytes=total_extra,
            seek_forward=seek_forward,
            seek_backward=seek_backward,
            largest_extra_len=largest_extra,
        ),
        controls,
    )


def payload(summary: BsdiffSummary, controls: list[BsdiffControl], limit: int = 20) -> dict[str, object]:
    largest_extra = sorted((item for item in controls if item.extra_len), key=lambda item: item.extra_len, reverse=True)
    return {
        "format": "scummkit-bsdiff-inspect-v1",
        "summary": asdict(summary),
        "first_controls": [asdict(item) for item in controls[:limit]],
        "largest_extra_controls": [asdict(item) for item in largest_extra[:limit]],
    }


def write_report(path: Path, summary: BsdiffSummary, controls: list[BsdiffControl], limit: int = 20) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload(summary, controls, limit), indent=2) + "\n", encoding="utf-8")
