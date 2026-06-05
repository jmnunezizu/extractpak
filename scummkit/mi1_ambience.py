from __future__ import annotations

import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path

from . import xwb


class AmbienceCueError(RuntimeError):
    pass


@dataclass(frozen=True)
class AmbienceCue:
    name: str
    sound_index: int | None
    sound_record_offset: int | None
    wave_index: int | None
    wave_name: str | None


def _read_u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _string_at(data: bytes, offset: int) -> str | None:
    if offset < 0 or offset >= len(data):
        return None
    end = data.find(b"\0", offset)
    if end < 0 or end == offset:
        return None
    raw = data[offset:end]
    if any(byte < 32 or byte > 126 for byte in raw):
        return None
    return raw.decode("ascii")


def _find_string_start(data: bytes) -> int:
    candidates = [data.find(b"01_Beach")]
    candidates = [offset for offset in candidates if offset >= 0]
    if not candidates:
        raise AmbienceCueError("could not locate MI1 ambience cue strings")
    return min(candidates)


def _find_cue_name_records(data: bytes, string_start: int) -> tuple[int, int]:
    best_start = 0
    best_count = 0
    for start in range(0, string_start - 6):
        count = 0
        pos = start
        while pos + 6 <= string_start:
            name_offset = _read_u32(data, pos + 2)
            name = _string_at(data, name_offset)
            if name is None or name_offset < string_start:
                break
            count += 1
            pos += 6
        if count > best_count:
            best_start = start
            best_count = count
    if best_count < 2:
        raise AmbienceCueError("could not locate MI1 ambience cue name table")
    return best_start, best_count


def _find_sound_offsets(data: bytes, cue_table_start: int) -> list[int]:
    best: list[int] = []
    for start in range(0, cue_table_start - 5):
        offsets: list[int] = []
        pos = start
        while pos + 5 <= cue_table_start and data[pos] == 4:
            offset = _read_u32(data, pos + 1)
            if offset >= cue_table_start:
                break
            offsets.append(offset)
            pos += 5
        if len(offsets) > len(best):
            best = offsets
    if not best:
        raise AmbienceCueError("could not locate MI1 ambience sound table")
    return best


def _sound_record_end(sound_offsets: list[int], offset: int, cue_table_start: int) -> int:
    later = [item for item in sound_offsets if item > offset]
    return min(later) if later else cue_table_start


def _wave_index_for_sound(data: bytes, start: int, end: int) -> int | None:
    record = data[start:end]
    for pos in range(0, max(0, len(record) - 5)):
        if record[pos : pos + 2] == b"\xff\x0c" and record[pos + 4 : pos + 6] == b"\x00\xff":
            return record[pos + 2]
    for pos in range(0, max(0, len(record) - 2)):
        if record[pos : pos + 2] == b"\xff\x0c":
            return record[pos + 2]
    return None


def parse_mi1_ambience_cues(cues_path: Path, ambience_xwb: Path) -> list[AmbienceCue]:
    data = cues_path.read_bytes()
    if not data.startswith(b"SDBK"):
        raise AmbienceCueError(f"{cues_path} is not an XACT sound bank")
    bank = xwb.parse_xwb(ambience_xwb)
    wave_names = [entry["name"] for entry in bank["entries"]]

    string_start = _find_string_start(data)
    cue_start, cue_count = _find_cue_name_records(data, string_start)
    sound_offsets = _find_sound_offsets(data, cue_start)

    cues: list[AmbienceCue] = []
    for index in range(cue_count):
        pos = cue_start + index * 6
        sound_index_raw = _read_u16(data, pos)
        name_offset = _read_u32(data, pos + 2)
        name = _string_at(data, name_offset)
        if name is None:
            continue
        sound_index = None if sound_index_raw == 0xFFFF else sound_index_raw
        sound_record_offset = None
        wave_index = None
        wave_name = None
        if sound_index is not None and sound_index < len(sound_offsets):
            sound_record_offset = sound_offsets[sound_index]
            end = _sound_record_end(sound_offsets, sound_record_offset, cue_start)
            wave_index = _wave_index_for_sound(data, sound_record_offset, end)
            if wave_index is not None and wave_index < len(wave_names):
                wave_name = wave_names[wave_index]
        cues.append(
            AmbienceCue(
                name=name,
                sound_index=sound_index,
                sound_record_offset=sound_record_offset,
                wave_index=wave_index,
                wave_name=wave_name,
            )
        )
    return cues


def payload(cues: list[AmbienceCue]) -> dict[str, object]:
    mapped = sum(1 for cue in cues if cue.wave_name is not None)
    return {
        "format": "scummkit-mi1-ambience-cues-v1",
        "summary": {
            "total": len(cues),
            "mapped": mapped,
            "unmapped": len(cues) - mapped,
        },
        "cues": [asdict(cue) for cue in cues],
    }


def write_report(path: Path, cues: list[AmbienceCue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload(cues), indent=2) + "\n", encoding="utf-8")
