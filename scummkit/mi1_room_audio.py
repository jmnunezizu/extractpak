from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from . import mi1_ambience, mi1_resources, mi1_sbl, mi1_script_decode


@dataclass(frozen=True)
class RoomAudioSound:
    sound_id: int
    size: int
    child_tags: list[str]
    native_sbl_source: str | None
    native_sbl_effects: list[str]


@dataclass(frozen=True)
class RoomAudioOpcode:
    offset: int
    opcode: int
    name: str
    argument: int | None
    argument_kind: str


@dataclass(frozen=True)
class RoomAudioDecodeIssue:
    offset: int
    opcode: int | None
    reason: str


@dataclass(frozen=True)
class RoomAudioScript:
    script_id: int
    size: int
    referenced_sound_ids: list[int]
    referenced_root_tracks: list[int]
    audio_opcodes: list[RoomAudioOpcode]
    decode_issues: list[RoomAudioDecodeIssue]


@dataclass(frozen=True)
class RoomAudioEmbeddedScript:
    tag: str
    index: int
    offset: int
    size: int
    referenced_sound_ids: list[int]
    referenced_root_tracks: list[int]
    audio_opcodes: list[RoomAudioOpcode]
    decode_issues: list[RoomAudioDecodeIssue]


@dataclass(frozen=True)
class RoomAudioRootTrack:
    track: int
    path: str
    present: bool


@dataclass(frozen=True)
class RoomAudioReport:
    room_id: int
    ambience_cue_name: str | None
    ambience_wave_name: str | None
    sounds: list[RoomAudioSound]
    scripts: list[RoomAudioScript]
    embedded_scripts: list[RoomAudioEmbeddedScript]
    root_tracks: list[RoomAudioRootTrack]


def _room_cue(cues: list[mi1_ambience.AmbienceCue], room_id: int) -> mi1_ambience.AmbienceCue | None:
    prefix = f"{room_id:02d}_"
    for cue in cues:
        if cue.name.startswith(prefix):
            return cue
    return None


def _sound_child_tags(data: bytes) -> list[str]:
    analysis = mi1_resources._sound_structure(data)
    tags: list[str] = []
    for child in analysis.get("children", []):
        if isinstance(child, dict) and child.get("tag") == "SOU ":
            for grandchild in child.get("children", []):
                if isinstance(grandchild, dict) and isinstance(grandchild.get("tag"), str):
                    tags.append(grandchild["tag"])
    return tags


def _root_tracks(game_dir: Path, audio: str) -> list[RoomAudioRootTrack]:
    tracks: list[RoomAudioRootTrack] = []
    for path in sorted(game_dir.glob(f"track*.{audio}"), key=_track_sort_key):
        match = re.fullmatch(r"track(\d+)\." + re.escape(audio), path.name)
        if match is None:
            continue
        tracks.append(RoomAudioRootTrack(track=int(match.group(1)), path=path.name, present=path.is_file()))
    return tracks


def _track_sort_key(path: Path) -> tuple[int, str]:
    match = re.fullmatch(r"track(\d+)\..+", path.name)
    return (int(match.group(1)) if match is not None else 9999, path.name)


def _byte_refs(data: bytes, candidates: set[int]) -> list[int]:
    return sorted(value for value in candidates if 0 <= value <= 255 and bytes([value]) in data)


def _audio_opcodes(data: bytes) -> list[RoomAudioOpcode]:
    decoded = mi1_script_decode.decode_audio_opcodes(data)
    return [
        RoomAudioOpcode(
            offset=item.offset,
            opcode=item.opcode,
            name=item.name,
            argument=item.argument,
            argument_kind=item.argument_kind,
        )
        for item in decoded.audio_opcodes
    ]


def _decode_issues(data: bytes) -> list[RoomAudioDecodeIssue]:
    decoded = mi1_script_decode.decode_audio_opcodes(data)
    return [
        RoomAudioDecodeIssue(offset=item.offset, opcode=item.opcode, reason=item.reason)
        for item in decoded.issues
    ]


def _room_chunks(room_payload: bytes) -> list[tuple[str, int, int, bytes]]:
    chunks: list[tuple[str, int, int, bytes]] = []
    if len(room_payload) < 8 or room_payload[:4] != b"ROOM":
        return chunks
    room_size = int.from_bytes(room_payload[4:8], "big")
    pos = 8
    while pos + 8 <= min(room_size, len(room_payload)):
        tag = room_payload[pos : pos + 4].decode("ascii", errors="replace")
        size = int.from_bytes(room_payload[pos + 4 : pos + 8], "big")
        if size < 8 or pos + size > len(room_payload):
            break
        chunks.append((tag, pos, size, room_payload[pos + 8 : pos + size]))
        pos += size
    return chunks


def build_report(
    *,
    game_dir: Path,
    audio_dir: Path | None = None,
    room_id: int,
    audio: str = "ogg",
) -> RoomAudioReport:
    game = mi1_resources._read_game_dir(game_dir)
    return build_report_from_resources(game=game, game_dir=game_dir, audio_dir=audio_dir, room_id=room_id, audio=audio)


def build_report_from_resources(
    *,
    game: mi1_resources.GameResources,
    game_dir: Path,
    audio_dir: Path | None = None,
    room_id: int,
    audio: str = "ogg",
) -> RoomAudioReport:
    room_entries = [entry for entry in game.entries if entry.room_id == room_id]
    commands = {(command.room_id, command.sound_id): command for command in mi1_sbl.native_sbl_commands()}

    cues: list[mi1_ambience.AmbienceCue] = []
    if audio_dir is not None:
        cues = mi1_ambience.parse_mi1_ambience_cues(audio_dir / "AmbienceCues.xsb", audio_dir / "Ambience.xwb")
    cue = _room_cue(cues, room_id)

    sounds: list[RoomAudioSound] = []
    sound_ids = {entry.resource_id for entry in room_entries if entry.resource_type == "sound"}
    for entry in room_entries:
        if entry.resource_type != "sound":
            continue
        data = mi1_resources._resource_bytes(game, entry)
        command = commands.get((room_id, entry.resource_id))
        sounds.append(
            RoomAudioSound(
                sound_id=entry.resource_id,
                size=entry.size,
                child_tags=_sound_child_tags(data),
                native_sbl_source=command.source if command is not None else None,
                native_sbl_effects=list(command.effects) if command is not None else [],
            )
        )

    root_tracks = _root_tracks(game_dir, audio)
    root_track_ids = {track.track for track in root_tracks}
    scripts: list[RoomAudioScript] = []
    for entry in room_entries:
        if entry.resource_type != "script":
            continue
        data = mi1_resources._resource_bytes(game, entry)
        scripts.append(
            RoomAudioScript(
                script_id=entry.resource_id,
                size=entry.size,
                referenced_sound_ids=_byte_refs(data, sound_ids),
                referenced_root_tracks=_byte_refs(data, root_track_ids),
                audio_opcodes=_audio_opcodes(data),
                decode_issues=_decode_issues(data),
            )
        )

    embedded_scripts: list[RoomAudioEmbeddedScript] = []
    embedded_counts: dict[str, int] = {}
    room_payload = game.room_payloads.get(room_id)
    if room_payload is not None:
        for tag, offset, size, data in _room_chunks(room_payload):
            if tag not in {"ENCD", "EXCD", "LSCR"}:
                continue
            script_data = data[1:] if tag == "LSCR" and data else data
            embedded_counts[tag] = embedded_counts.get(tag, 0) + 1
            embedded_scripts.append(
                RoomAudioEmbeddedScript(
                    tag=tag,
                    index=embedded_counts[tag],
                    offset=offset,
                    size=size,
                    referenced_sound_ids=_byte_refs(script_data, sound_ids),
                    referenced_root_tracks=_byte_refs(script_data, root_track_ids),
                    audio_opcodes=_audio_opcodes(script_data),
                    decode_issues=_decode_issues(script_data),
                )
            )

    return RoomAudioReport(
        room_id=room_id,
        ambience_cue_name=cue.name if cue is not None else None,
        ambience_wave_name=cue.wave_name if cue is not None else None,
        sounds=sorted(sounds, key=lambda item: item.sound_id),
        scripts=sorted(scripts, key=lambda item: item.script_id),
        embedded_scripts=embedded_scripts,
        root_tracks=root_tracks,
    )


def payload(report: RoomAudioReport) -> dict[str, object]:
    return {
        "format": "scummkit-mi1-room-audio-report-v1",
        "report": asdict(report),
    }


def write_report(path: Path, report: RoomAudioReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload(report), indent=2) + "\n", encoding="utf-8")
