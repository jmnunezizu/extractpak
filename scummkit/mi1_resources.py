from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_game_dir(game_dir: Path) -> GameResources:
    monkey000 = game_dir / "monkey.000"
    monkey001 = game_dir / "monkey.001"
    require_file(monkey000)
    require_file(monkey001)
    index_data = mi1_sbl.xor_data(monkey000.read_bytes())
    resource_data = mi1_sbl.xor_data(monkey001.read_bytes())
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


def _find_entry(game: GameResources, room_id: int, resource_id: int, resource_type: str) -> ResourceEntry | None:
    for entry in game.entries:
        if entry.room_id == room_id and entry.resource_id == resource_id and entry.resource_type == resource_type:
            return entry
    return None


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
