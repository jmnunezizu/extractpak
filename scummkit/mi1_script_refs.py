from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import mi1_resources


@dataclass(frozen=True)
class ByteReference:
    value: int
    count: int
    offsets: list[int]


@dataclass(frozen=True)
class ScriptReference:
    room_id: int
    script_id: int
    size: int
    room_refs: list[ByteReference]
    sound_refs: list[ByteReference]
    track_refs: list[ByteReference]


@dataclass(frozen=True)
class ScriptReferenceReport:
    rooms: list[int]
    sounds: list[int]
    tracks: list[int]
    scripts: list[ScriptReference]


def _find_byte_refs(data: bytes, candidates: list[int], limit: int) -> list[ByteReference]:
    refs: list[ByteReference] = []
    for value in sorted(set(candidates)):
        if value < 0 or value > 255:
            continue
        offsets = [index for index, byte in enumerate(data) if byte == value]
        if offsets:
            refs.append(ByteReference(value=value, count=len(offsets), offsets=offsets[:limit]))
    return refs


def build_report(
    *,
    game_dir: Path,
    rooms: list[int],
    sounds: list[int],
    tracks: list[int],
    offset_limit: int = 12,
) -> ScriptReferenceReport:
    game = mi1_resources._read_game_dir(game_dir)
    scripts: list[ScriptReference] = []
    for entry in game.entries:
        if entry.resource_type != "script":
            continue
        data = mi1_resources._resource_bytes(game, entry)
        room_refs = _find_byte_refs(data, rooms, offset_limit)
        sound_refs = _find_byte_refs(data, sounds, offset_limit)
        track_refs = _find_byte_refs(data, tracks, offset_limit)
        if not room_refs and not sound_refs and not track_refs:
            continue
        scripts.append(
            ScriptReference(
                room_id=entry.room_id,
                script_id=entry.resource_id,
                size=entry.size,
                room_refs=room_refs,
                sound_refs=sound_refs,
                track_refs=track_refs,
            )
        )
    scripts.sort(key=lambda item: (item.room_id, item.script_id))
    return ScriptReferenceReport(
        rooms=sorted(set(rooms)),
        sounds=sorted(set(sounds)),
        tracks=sorted(set(tracks)),
        scripts=scripts,
    )


def payload(report: ScriptReferenceReport) -> dict[str, object]:
    return {
        "format": "scummkit-mi1-script-reference-report-v1",
        "summary": {
            "scripts": len(report.scripts),
            "rooms": report.rooms,
            "sounds": report.sounds,
            "tracks": report.tracks,
        },
        "scripts": [asdict(script) for script in report.scripts],
    }


def write_report(path: Path, report: ScriptReferenceReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload(report), indent=2) + "\n", encoding="utf-8")
