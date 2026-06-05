from __future__ import annotations

import argparse
import difflib
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import mi1_sbl
from .runner import BuildError, require_file


RESOURCE_TYPES = {
    "script": ("DSCR", b"SCRP"),
    "sound": ("DSOU", b"SOUN"),
    "costume": ("DCOS", b"COST"),
    "charset": ("DCHR", b"CHAR"),
}


@dataclass(frozen=True)
class ResourceEntry:
    resource_type: str
    resource_id: int
    room_id: int
    relative_offset: int
    absolute_offset: int
    size: int
    tag: str


@dataclass
class GameResources:
    index_data: bytes
    resource_data: bytes
    room_payloads: dict[int, bytes]
    room_offsets: dict[int, int]
    entries: list[ResourceEntry]


@dataclass(frozen=True)
class ResourceDiff:
    resource_type: str
    resource_id: int
    original_room_id: int | None
    patched_room_id: int | None
    original_size: int | None
    patched_size: int | None
    original_sha256: str | None
    patched_sha256: str | None
    original_relative_offset: int | None
    patched_relative_offset: int | None
    status: str
    analysis: dict[str, Any] | None = None


@dataclass(frozen=True)
class RoomDiff:
    room_id: int
    original_size: int | None
    patched_size: int | None
    original_sha256: str | None
    patched_sha256: str | None
    status: str


@dataclass(frozen=True)
class PatchDiffSummary:
    original_index_sha256: str
    patched_index_sha256: str
    original_data_sha256: str
    patched_data_sha256: str
    rooms_added: int
    rooms_removed: int
    rooms_changed: int
    resources_added: int
    resources_removed: int
    resources_changed: int
    resources_moved_only: int


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_game_files(index_path: Path, resource_path: Path) -> GameResources:
    require_file(index_path)
    require_file(resource_path)
    index_data = mi1_sbl.xor_data(index_path.read_bytes())
    resource_data = mi1_sbl.xor_data(resource_path.read_bytes())
    return _parse_game_data(index_data, resource_data)


def _read_game_dir(game_dir: Path) -> GameResources:
    monkey000 = game_dir / "monkey.000"
    monkey001 = game_dir / "monkey.001"
    return _read_game_files(monkey000, monkey001)


def _parse_game_data(index_data: bytes, resource_data: bytes) -> GameResources:
    _loff_size, loff_entries = mi1_sbl.parse_loff(resource_data)
    room_offsets = {room: offset - 8 for room, offset in loff_entries}
    room_payloads = mi1_sbl.get_room_payloads(resource_data)
    entries: list[ResourceEntry] = []

    for resource_type, (directory_tag, expected_tag) in RESOURCE_TYPES.items():
        _chunk_offset, _size, count, rooms, offsets = mi1_sbl.parse_directory_chunk(index_data, directory_tag)
        for resource_id, (room_id, relative_offset) in enumerate(zip(rooms, offsets)):
            if not room_id and not relative_offset:
                continue
            payload = room_payloads.get(room_id)
            room_offset = room_offsets.get(room_id)
            if payload is None or room_offset is None:
                continue
            if relative_offset + 8 > len(payload):
                size = 0
                tag = "????"
            else:
                raw_tag = payload[relative_offset : relative_offset + 4]
                size = mi1_sbl.read_be_size(payload, relative_offset)
                tag = raw_tag.decode("ascii", errors="replace")
                if raw_tag != expected_tag:
                    tag = f"{tag}!"
            entries.append(
                ResourceEntry(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    room_id=room_id,
                    relative_offset=relative_offset,
                    absolute_offset=room_offset + 8 + relative_offset,
                    size=size,
                    tag=tag,
                )
            )
    entries.sort(key=lambda item: (item.room_id, item.resource_type, item.resource_id))
    return GameResources(index_data, resource_data, room_payloads, room_offsets, entries)


def _resource_bytes(game: GameResources, entry: ResourceEntry) -> bytes:
    payload = game.room_payloads[entry.room_id]
    return payload[entry.relative_offset : entry.relative_offset + entry.size]


def _byte_change_ranges(original: bytes, patched: bytes, limit: int = 20) -> dict[str, object]:
    matcher = difflib.SequenceMatcher(None, original, patched, autojunk=False)
    ranges = []
    total_blocks = 0
    original_changed = 0
    patched_changed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        total_blocks += 1
        original_changed += i2 - i1
        patched_changed += j2 - j1
        if len(ranges) < limit:
            ranges.append(
                {
                    "kind": tag,
                    "original_start": i1,
                    "original_end": i2,
                    "patched_start": j1,
                    "patched_end": j2,
                    "original_len": i2 - i1,
                    "patched_len": j2 - j1,
                }
            )
    return {
        "block_count": total_blocks,
        "original_changed_bytes": original_changed,
        "patched_changed_bytes": patched_changed,
        "ranges": ranges,
        "ranges_truncated": total_blocks > len(ranges),
    }


def _read_payload_chunk(data: bytes, offset: int) -> tuple[str, int, int] | None:
    if offset + 8 > len(data):
        return None
    tag = data[offset : offset + 4].decode("ascii", errors="replace")
    payload_size = int.from_bytes(data[offset + 4 : offset + 8], "big")
    total_size = 8 + payload_size
    if payload_size < 0 or offset + total_size > len(data):
        return None
    return tag, payload_size, total_size


def _sound_structure(data: bytes) -> dict[str, object]:
    if len(data) < 8 or data[:4] != b"SOUN":
        return {"valid": False}
    soun_size = int.from_bytes(data[4:8], "big")
    result: dict[str, object] = {
        "valid": True,
        "soun_size": soun_size,
        "file_size": len(data),
        "children": [],
    }
    children: list[dict[str, object]] = []
    offset = 8
    while offset + 8 <= len(data):
        child = _read_payload_chunk(data, offset)
        if child is None:
            children.append({"offset": offset, "tag": "invalid", "payload_size": None, "total_size": None})
            break
        tag, payload_size, total_size = child
        item: dict[str, object] = {
            "offset": offset,
            "tag": tag,
            "payload_size": payload_size,
            "total_size": total_size,
        }
        if tag == "SOU ":
            item["children"] = _sou_children(data[offset + 8 : offset + total_size], offset + 8)
        children.append(item)
        offset += total_size
    result["children"] = children
    return result


def _sou_children(payload: bytes, base_offset: int) -> list[dict[str, object]]:
    children: list[dict[str, object]] = []
    offset = 0
    while offset + 8 <= len(payload):
        child = _read_payload_chunk(payload, offset)
        if child is None:
            children.append(
                {
                    "offset": base_offset + offset,
                    "tag": "invalid",
                    "payload_size": None,
                    "total_size": None,
                }
            )
            break
        tag, payload_size, total_size = child
        children.append(
            {
                "offset": base_offset + offset,
                "tag": tag,
                "payload_size": payload_size,
                "total_size": total_size,
            }
        )
        offset += total_size
    return children


def _resource_analysis(resource_type: str, original_data: bytes | None, patched_data: bytes | None) -> dict[str, Any] | None:
    if original_data is None and patched_data is None:
        return None
    analysis: dict[str, Any] = {}
    if resource_type == "script" and original_data is not None and patched_data is not None and original_data != patched_data:
        analysis["byte_changes"] = _byte_change_ranges(original_data, patched_data)
    if resource_type == "sound":
        if original_data is not None:
            analysis["original_sound"] = _sound_structure(original_data)
        if patched_data is not None:
            analysis["patched_sound"] = _sound_structure(patched_data)
        if original_data is not None and patched_data is not None and original_data != patched_data:
            analysis["byte_changes"] = _byte_change_ranges(original_data, patched_data, limit=10)
    return analysis or None


def _find_entry(game: GameResources, room_id: int, resource_id: int, resource_type: str) -> ResourceEntry | None:
    for entry in game.entries:
        if entry.room_id == room_id and entry.resource_id == resource_id and entry.resource_type == resource_type:
            return entry
    return None


def _entry_by_key(game: GameResources) -> dict[tuple[str, int], ResourceEntry]:
    return {(entry.resource_type, entry.resource_id): entry for entry in game.entries}


def _room_diff(original: GameResources, patched: GameResources) -> list[RoomDiff]:
    diffs: list[RoomDiff] = []
    room_ids = sorted(set(original.room_payloads) | set(patched.room_payloads))
    for room_id in room_ids:
        original_payload = original.room_payloads.get(room_id)
        patched_payload = patched.room_payloads.get(room_id)
        if original_payload is None:
            status = "added"
        elif patched_payload is None:
            status = "removed"
        elif original_payload == patched_payload:
            continue
        else:
            status = "changed"
        diffs.append(
            RoomDiff(
                room_id=room_id,
                original_size=len(original_payload) if original_payload is not None else None,
                patched_size=len(patched_payload) if patched_payload is not None else None,
                original_sha256=_sha256(original_payload) if original_payload is not None else None,
                patched_sha256=_sha256(patched_payload) if patched_payload is not None else None,
                status=status,
            )
        )
    return diffs


def _resource_diff(original: GameResources, patched: GameResources) -> list[ResourceDiff]:
    diffs: list[ResourceDiff] = []
    original_entries = _entry_by_key(original)
    patched_entries = _entry_by_key(patched)
    keys = sorted(set(original_entries) | set(patched_entries))
    for resource_type, resource_id in keys:
        original_entry = original_entries.get((resource_type, resource_id))
        patched_entry = patched_entries.get((resource_type, resource_id))
        original_data = _resource_bytes(original, original_entry) if original_entry is not None else None
        patched_data = _resource_bytes(patched, patched_entry) if patched_entry is not None else None
        if original_entry is None:
            status = "added"
        elif patched_entry is None:
            status = "removed"
        elif original_data != patched_data:
            status = "changed"
        elif (
            original_entry.room_id != patched_entry.room_id
            or original_entry.relative_offset != patched_entry.relative_offset
        ):
            status = "moved-only"
        else:
            continue
        diffs.append(
            ResourceDiff(
                resource_type=resource_type,
                resource_id=resource_id,
                original_room_id=original_entry.room_id if original_entry is not None else None,
                patched_room_id=patched_entry.room_id if patched_entry is not None else None,
                original_size=original_entry.size if original_entry is not None else None,
                patched_size=patched_entry.size if patched_entry is not None else None,
                original_sha256=_sha256(original_data) if original_data is not None else None,
                patched_sha256=_sha256(patched_data) if patched_data is not None else None,
                original_relative_offset=original_entry.relative_offset if original_entry is not None else None,
                patched_relative_offset=patched_entry.relative_offset if patched_entry is not None else None,
                status=status,
                analysis=_resource_analysis(resource_type, original_data, patched_data),
            )
        )
    return diffs


def diff_games(original: GameResources, patched: GameResources) -> tuple[PatchDiffSummary, list[RoomDiff], list[ResourceDiff]]:
    room_diffs = _room_diff(original, patched)
    resource_diffs = _resource_diff(original, patched)
    summary = PatchDiffSummary(
        original_index_sha256=_sha256(original.index_data),
        patched_index_sha256=_sha256(patched.index_data),
        original_data_sha256=_sha256(original.resource_data),
        patched_data_sha256=_sha256(patched.resource_data),
        rooms_added=sum(1 for item in room_diffs if item.status == "added"),
        rooms_removed=sum(1 for item in room_diffs if item.status == "removed"),
        rooms_changed=sum(1 for item in room_diffs if item.status == "changed"),
        resources_added=sum(1 for item in resource_diffs if item.status == "added"),
        resources_removed=sum(1 for item in resource_diffs if item.status == "removed"),
        resources_changed=sum(1 for item in resource_diffs if item.status == "changed"),
        resources_moved_only=sum(1 for item in resource_diffs if item.status == "moved-only"),
    )
    return summary, room_diffs, resource_diffs


def diff_game_files(
    original_index: Path,
    original_data: Path,
    patched_index: Path,
    patched_data: Path,
) -> tuple[PatchDiffSummary, list[RoomDiff], list[ResourceDiff]]:
    original = _read_game_files(original_index.expanduser(), original_data.expanduser())
    patched = _read_game_files(patched_index.expanduser(), patched_data.expanduser())
    return diff_games(original, patched)


def _print_entry(entry: ResourceEntry) -> None:
    print(
        f"room={entry.room_id:03d} type={entry.resource_type:<7} id={entry.resource_id:03d} "
        f"tag={entry.tag:<5} rel={entry.relative_offset:06d} abs={entry.absolute_offset:08d} "
        f"size={entry.size}"
    )


def list_resources(game_dir: Path) -> None:
    game = _read_game_dir(game_dir.expanduser())
    for entry in game.entries:
        _print_entry(entry)
    print(f"resources: {len(game.entries)}")


def list_room(game_dir: Path, room_id: int) -> None:
    game = _read_game_dir(game_dir.expanduser())
    room_entries = [entry for entry in game.entries if entry.room_id == room_id]
    for entry in room_entries:
        _print_entry(entry)
    print(f"room {room_id:03d} resources: {len(room_entries)}")


def show_resource(
    game_dir: Path,
    room_id: int,
    resource_id: int,
    resource_type: str,
    dump: Path | None = None,
    compare_game_dir: Path | None = None,
) -> None:
    game = _read_game_dir(game_dir.expanduser())
    entry = _find_entry(game, room_id, resource_id, resource_type)
    if entry is None:
        raise BuildError(f"resource not found: room {room_id} {resource_type} {resource_id}")
    _print_entry(entry)
    data = _resource_bytes(game, entry)
    print(f"sha256={_sha256(data)}")
    if dump is not None:
        dump = dump.expanduser()
        dump.parent.mkdir(parents=True, exist_ok=True)
        dump.write_bytes(data)
        print(f"dumped: {dump}")
    if compare_game_dir is not None:
        compare = _read_game_dir(compare_game_dir.expanduser())
        compare_entry = _find_entry(compare, room_id, resource_id, resource_type)
        if compare_entry is None:
            print(f"compare: missing in {compare_game_dir}")
            return
        compare_data = _resource_bytes(compare, compare_entry)
        print(
            "compare: "
            f"size {compare_entry.size} -> {entry.size}; "
            f"sha256 {_sha256(compare_data)} -> {_sha256(data)}; "
            f"equal={compare_data == data}"
        )


def add_inspect_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser], handler=None) -> None:
    inspect = sub.add_parser("inspect", help="inspect generated game resources")
    games = inspect.add_subparsers(dest="game", required=True)
    mi1 = games.add_parser("mi1", help="inspect MI1 SCUMM resources")
    mi1_actions = mi1.add_subparsers(dest="inspect_action", required=True)

    resources = mi1_actions.add_parser("resources", help="list indexed resources")
    resources.add_argument("--game-dir", type=Path, required=True)
    if handler is not None:
        resources.set_defaults(func=handler)

    room = mi1_actions.add_parser("room", help="list resources in a room")
    room.add_argument("--game-dir", type=Path, required=True)
    room.add_argument("--room", type=int, required=True)
    if handler is not None:
        room.set_defaults(func=handler)

    resource = mi1_actions.add_parser("resource", help="show or dump one indexed resource")
    resource.add_argument("--game-dir", type=Path, required=True)
    resource.add_argument("--room", type=int, required=True)
    resource.add_argument("--id", type=int, required=True)
    resource.add_argument("--type", choices=sorted(RESOURCE_TYPES), default="sound")
    resource.add_argument("--dump", type=Path)
    resource.add_argument("--compare", type=Path, help="compare against another game directory")
    if handler is not None:
        resource.set_defaults(func=handler)


def run_inspect(args: argparse.Namespace) -> None:
    if args.game != "mi1":
        raise BuildError("only MI1 resource inspection is currently implemented")
    if args.inspect_action == "resources":
        list_resources(args.game_dir)
    elif args.inspect_action == "room":
        list_room(args.game_dir, args.room)
    elif args.inspect_action == "resource":
        show_resource(args.game_dir, args.room, args.id, args.type, args.dump, args.compare)
    else:
        raise BuildError("unsupported inspect command")
