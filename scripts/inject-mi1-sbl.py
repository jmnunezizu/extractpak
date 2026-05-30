#!/usr/bin/env python3
import argparse
import hashlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import wav2sbl


XOR_KEY = 0x69
TOP_DIRS = {
    "DSCR": b"SCRP",
    "DSOU": b"SOUN",
    "DCOS": b"COST",
    "DCHR": b"CHAR",
}
SOU_CHILD_TYPES = {b"SBL ", b"ADL ", b"SPK ", b"ROL ", b"GMD "}


class InjectError(Exception):
    pass


@dataclass
class SblCommand:
    index: int
    source: str
    effects: list[str]
    target: str
    room_id: int
    sound_id: int
    sbl_child_index: Optional[int]


def xor_data(data):
    return bytes(byte ^ XOR_KEY for byte in data)


def be32(value):
    return value.to_bytes(4, "big")


def read_be_size(data, offset):
    return int.from_bytes(data[offset + 4 : offset + 8], "big")


def set_be_size(buf, offset, value):
    buf[offset + 4 : offset + 8] = be32(value)


def parse_sbl_bat(path):
    commands = []
    pending_sox = None
    lines = path.read_text(encoding="latin1").splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("sox "):
            parts = stripped.split()
            if len(parts) < 13:
                raise InjectError(f"cannot parse SoX command: {stripped}")
            pending_sox = (parts[1], parts[13:])
        elif stripped.lower().startswith("copy ") and "000_SBL.dmp" in stripped:
            if pending_sox is None:
                raise InjectError(f"copy without preceding SoX command: {stripped}")
            match = re.search(r"000_LECF\\(\d+)_LFLF_[^\\]+\\(\d+)_SOUN_(\d+)\\000_SOU(?:\\(\d+)_SBL\.dmp)?", stripped)
            if not match:
                raise InjectError(f"cannot parse SBL target path: {stripped}")
            child_match = re.search(r"\\(\d+)_SBL\.dmp", stripped)
            source, effects = pending_sox
            commands.append(
                SblCommand(
                    index=len(commands) + 1,
                    source=source,
                    effects=effects,
                    target=match.group(0),
                    room_id=int(match.group(1)),
                    sound_id=int(match.group(3)),
                    sbl_child_index=int(child_match.group(1)) if child_match else None,
                )
            )
            pending_sox = None
    if not commands:
        raise InjectError(f"no SBL commands found in {path}")
    return commands


def parse_directory_chunk(data, tag):
    offset = 0
    while offset + 8 <= len(data):
        current = data[offset : offset + 4].decode("ascii")
        size = read_be_size(data, offset)
        if current == tag:
            payload = data[offset + 8 : offset + size]
            count = int.from_bytes(payload[:2], "little")
            rooms = list(payload[2 : 2 + count])
            offsets_start = 2 + count
            offsets = [
                int.from_bytes(payload[offsets_start + i * 4 : offsets_start + (i + 1) * 4], "little")
                for i in range(count)
            ]
            return offset, size, count, rooms, offsets
        offset += size
    raise InjectError(f"missing {tag} directory chunk")


def write_directory_chunk(buf, chunk_offset, count, rooms, offsets):
    size = read_be_size(buf, chunk_offset)
    payload_start = chunk_offset + 8
    existing_count = int.from_bytes(buf[payload_start : payload_start + 2], "little")
    if existing_count != count:
        raise InjectError("directory count changed unexpectedly")
    offsets_start = payload_start + 2 + count
    for i, value in enumerate(offsets):
        buf[offsets_start + i * 4 : offsets_start + (i + 1) * 4] = value.to_bytes(4, "little")
    if chunk_offset + size > len(buf):
        raise InjectError("directory chunk extends beyond index file")


def parse_loff(data):
    if data[:4] != b"LECF":
        raise InjectError("monkey.001 is not an LECF file after decryption")
    if data[8:12] != b"LOFF":
        raise InjectError("LECF does not start with LOFF")
    loff_size = read_be_size(data, 8)
    payload = data[16 : 8 + loff_size]
    count = payload[0]
    entries = []
    for i in range(count):
        start = 1 + i * 5
        entries.append([payload[start], int.from_bytes(payload[start + 1 : start + 5], "little")])
    return loff_size, entries


def collect_directories(index_data):
    directories = {}
    for tag in TOP_DIRS:
        directories[tag] = parse_directory_chunk(index_data, tag)
    return directories


def command_source_path(samples_wav, command):
    candidate = samples_wav / command.source
    if candidate.exists():
        return candidate
    raise InjectError(f"missing SBL source WAV: {candidate}")


def generate_sbl_chunks(commands, samples_wav, work, sample_rate, verbose):
    temp_wav = work / "temp.wav"
    chunks = {}
    for command in commands:
        source = command_source_path(samples_wav, command)
        sox_cmd = [
            "sox",
            str(source),
            "-D",
            "-b",
            "8",
            "-c",
            "1",
            "-r",
            str(sample_rate),
            "-t",
            "wav",
            "-V0",
            str(temp_wav),
            *[arg.replace("%1", str(sample_rate)) for arg in command.effects],
        ]
        if verbose:
            print("+ " + " ".join(sox_cmd))
        subprocess.run(sox_cmd, check=True)
        chunk = wav2sbl.wav_to_sbl_bytes(temp_wav)
        chunks[command.sound_id] = chunk
        if verbose:
            print(
                f"SBL {command.index:02d}: sound {command.sound_id} room {command.room_id} "
                f"{command.source} -> {len(chunk)} bytes"
            )
    return chunks


def replace_sbl_child(sou_chunk, new_sbl, requested_index):
    if sou_chunk[:4] != b"SOU ":
        raise InjectError("target offset does not point to a SOU chunk")
    sou_size = read_be_size(sou_chunk, 0)
    if sou_size + 8 != len(sou_chunk):
        raise InjectError("SOU chunk size mismatch")
    children = []
    offset = 8
    while offset < len(sou_chunk):
        tag = sou_chunk[offset : offset + 4]
        if tag not in SOU_CHILD_TYPES:
            raise InjectError(f"unsupported SOU child type at {offset}: {tag!r}")
        child_size = read_be_size(sou_chunk, offset)
        total = child_size + 8
        if offset + total > len(sou_chunk):
            raise InjectError("SOU child extends past parent")
        children.append([tag, sou_chunk[offset : offset + total]])
        offset += total

    replacement = None
    if requested_index is not None:
        if requested_index >= len(children) or children[requested_index][0] != b"SBL ":
            raise InjectError(f"requested SBL child index {requested_index} does not exist")
        replacement = requested_index
    else:
        for i, (tag, _payload) in enumerate(children):
            if tag == b"SBL ":
                replacement = i
                break
    if replacement is None:
        raise InjectError("target SOU has no SBL child to replace")

    old_size = len(children[replacement][1])
    children[replacement][1] = new_sbl
    payload = b"".join(child for _tag, child in children)
    new_sou = bytearray(b"SOU " + be32(len(payload)) + payload)
    return bytes(new_sou), old_size, len(new_sbl)


def parse_top_chunks(lflf_payload):
    chunks = []
    offset = 0
    while offset < len(lflf_payload):
        if offset + 8 > len(lflf_payload):
            raise InjectError("truncated LFLF child header")
        tag = lflf_payload[offset : offset + 4]
        size = read_be_size(lflf_payload, offset)
        if size < 8 or offset + size > len(lflf_payload):
            raise InjectError(f"invalid {tag!r} chunk size {size} at LFLF offset {offset}")
        chunks.append([tag, lflf_payload[offset : offset + size], offset])
        offset += size
    return chunks


def rebuild_resource_data(data, index_data, commands, sbl_chunks, verbose):
    loff_size, loff_entries = parse_loff(data)
    room_to_lflf = {room: offset - 8 for room, offset in loff_entries}
    dirs = collect_directories(index_data)
    dir_offsets = {tag: values[4] for tag, values in dirs.items()}
    dir_rooms = {tag: values[3] for tag, values in dirs.items()}

    by_sound = {command.sound_id: command for command in commands}
    old_dir_lookup = {}
    for tag, chunk_type in TOP_DIRS.items():
        rooms = dir_rooms[tag]
        offsets = dir_offsets[tag]
        for resource_id, (room, rel_offset) in enumerate(zip(rooms, offsets)):
            if room and rel_offset:
                old_dir_lookup[(room, chunk_type, rel_offset)] = (tag, resource_id)

    lflf_by_offset = {}
    offset = 8 + loff_size
    while offset < len(data):
        if data[offset : offset + 4] != b"LFLF":
            raise InjectError(f"expected LFLF at {offset}")
        size = read_be_size(data, offset)
        lflf_by_offset[offset] = data[offset : offset + size]
        offset += size

    rebuilt_lflfs = []
    injected = []
    for room, old_room_offset in loff_entries:
        old_lflf_offset = old_room_offset - 8
        lflf = lflf_by_offset.get(old_lflf_offset)
        if lflf is None:
            raise InjectError(f"LOFF references missing LFLF for room {room}")
        payload = lflf[8:]
        chunks = parse_top_chunks(payload)
        new_chunks = []
        rel_shift_lookup = {}

        for tag, chunk, old_rel in chunks:
            dir_key = (room, tag, old_rel)
            dir_entry = old_dir_lookup.get(dir_key)
            new_chunk = chunk
            if dir_entry and dir_entry[0] == "DSOU":
                sound_id = dir_entry[1]
                command = by_sound.get(sound_id)
                if command:
                    sou = chunk[8:]
                    new_sou, old_sbl_size, new_sbl_size = replace_sbl_child(
                        sou, sbl_chunks[sound_id], command.sbl_child_index
                    )
                    new_chunk = b"SOUN" + be32(8 + len(new_sou)) + new_sou
                    injected.append(
                        {
                            "index": command.index,
                            "sound_id": sound_id,
                            "room_id": room,
                            "source": command.source,
                            "old_sbl_size": old_sbl_size,
                            "new_sbl_size": new_sbl_size,
                            "old_soun_size": len(chunk),
                            "new_soun_size": len(new_chunk),
                        }
                    )
                    if verbose:
                        print(
                            f"inject sound {sound_id:03d} room {room:03d}: "
                            f"SBL {old_sbl_size} -> {new_sbl_size}, "
                            f"SOUN {len(chunk)} -> {len(new_chunk)}"
                        )
            new_rel = sum(len(existing) for existing in new_chunks)
            if dir_entry:
                rel_shift_lookup[dir_entry] = new_rel
            new_chunks.append(new_chunk)

        new_payload = b"".join(new_chunks)
        new_lflf = b"LFLF" + be32(8 + len(new_payload)) + new_payload
        rebuilt_lflfs.append([room, new_lflf, rel_shift_lookup])

    new_loff_entries = []
    new_offset = 8 + loff_size
    new_lflf_bytes = []
    for room, lflf, rel_lookup in rebuilt_lflfs:
        new_loff_entries.append([room, new_offset + 8])
        for (tag, resource_id), new_rel in rel_lookup.items():
            dir_offsets[tag][resource_id] = new_rel
        new_lflf_bytes.append(lflf)
        new_offset += len(lflf)

    loff_payload = bytearray([len(new_loff_entries)])
    for room, room_offset in new_loff_entries:
        loff_payload.append(room)
        loff_payload.extend(room_offset.to_bytes(4, "little"))
    new_loff = b"LOFF" + be32(8 + len(loff_payload)) + bytes(loff_payload)
    lecf_payload = new_loff + b"".join(new_lflf_bytes)
    new_data = b"LECF" + be32(8 + len(lecf_payload)) + lecf_payload

    new_index = bytearray(index_data)
    for tag, values in dirs.items():
        chunk_offset, _size, count, rooms, _offsets = values
        write_directory_chunk(new_index, chunk_offset, count, rooms, dir_offsets[tag])

    return bytes(new_index), new_data, injected


def get_room_payloads(resource_data):
    loff_size, loff_entries = parse_loff(resource_data)
    room_payloads = {}
    lflf_start = 8 + loff_size
    for room_id, room_offset in loff_entries:
        lflf_offset = room_offset - 8
        if lflf_offset < lflf_start or resource_data[lflf_offset : lflf_offset + 4] != b"LFLF":
            raise InjectError(f"LOFF room {room_id} points at an invalid LFLF offset")
        lflf_size = read_be_size(resource_data, lflf_offset)
        if lflf_offset + lflf_size > len(resource_data):
            raise InjectError(f"LOFF room {room_id} LFLF extends beyond resource file")
        room_payloads[room_id] = resource_data[lflf_offset + 8 : lflf_offset + lflf_size]
    return room_payloads


def find_sbl_size(soun_chunk, requested_index):
    if soun_chunk[:4] != b"SOUN":
        raise InjectError("resource is not a SOUN chunk")
    sou_chunk = soun_chunk[8:]
    if sou_chunk[:4] != b"SOU ":
        raise InjectError("SOUN does not contain a SOU child")
    children = []
    offset = 8
    while offset < len(sou_chunk):
        tag = sou_chunk[offset : offset + 4]
        child_size = read_be_size(sou_chunk, offset)
        total = child_size + 8
        if offset + total > len(sou_chunk):
            raise InjectError("SOU child extends beyond parent during verification")
        children.append((tag, total))
        offset += total
    if requested_index is not None:
        if requested_index >= len(children) or children[requested_index][0] != b"SBL ":
            raise InjectError(f"verified SOU is missing requested SBL child {requested_index}")
        return children[requested_index][1]
    for tag, total in children:
        if tag == b"SBL ":
            return total
    raise InjectError("verified SOU has no SBL child")


def verify_rebuilt_resources(index_data, resource_data, commands):
    room_payloads = get_room_payloads(resource_data)
    by_sound = {command.sound_id: command for command in commands}
    verified_sbl = 0

    for tag, expected_chunk_type in TOP_DIRS.items():
        _chunk_offset, _size, count, rooms, offsets = parse_directory_chunk(index_data, tag)
        if len(rooms) != count or len(offsets) != count:
            raise InjectError(f"{tag} directory count mismatch")
        for resource_id, (room_id, rel_offset) in enumerate(zip(rooms, offsets)):
            if not room_id and not rel_offset:
                continue
            payload = room_payloads.get(room_id)
            if payload is None:
                raise InjectError(f"{tag} resource {resource_id} points to missing room {room_id}")
            if rel_offset + 8 > len(payload):
                raise InjectError(f"{tag} resource {resource_id} offset is outside room {room_id}")
            chunk_type = payload[rel_offset : rel_offset + 4]
            if chunk_type != expected_chunk_type:
                raise InjectError(
                    f"{tag} resource {resource_id} expected {expected_chunk_type!r} "
                    f"at room {room_id} offset {rel_offset}, found {chunk_type!r}"
                )
            chunk_size = read_be_size(payload, rel_offset)
            if chunk_size < 8 or rel_offset + chunk_size > len(payload):
                raise InjectError(f"{tag} resource {resource_id} has an invalid chunk size")
            if tag == "DSOU" and resource_id in by_sound:
                sbl_size = find_sbl_size(
                    payload[rel_offset : rel_offset + chunk_size],
                    by_sound[resource_id].sbl_child_index,
                )
                if sbl_size <= 254:
                    raise InjectError(f"sound {resource_id} SBL replacement was not applied")
                verified_sbl += 1

    if verified_sbl != len(commands):
        raise InjectError(f"verified {verified_sbl} of {len(commands)} injected SBL resources")
    return verified_sbl


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Inject MI1 Ultimate Talkie SBL chunks natively")
    parser.add_argument("--builder", required=True, type=Path)
    parser.add_argument("--samples-wav", required=True, type=Path)
    parser.add_argument("--monkey000", required=True, type=Path)
    parser.add_argument("--monkey001", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--sample-rate", type=int, default=22050)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        sbl_bat = args.builder / "tools" / "sbl.bat"
        if not sbl_bat.exists():
            raise InjectError(f"missing {sbl_bat}")
        if not args.samples_wav.is_dir():
            raise InjectError(f"missing samples WAV directory: {args.samples_wav}")
        commands = parse_sbl_bat(sbl_bat)

        print(f"Parsed {len(commands)} SBL injection commands from {sbl_bat}")
        if args.dry_run:
            for command in commands:
                print(
                    f"[dry-run] sound {command.sound_id:03d} room {command.room_id:03d} "
                    f"{command.source} effects={' '.join(command.effects) or '(none)'}"
                )
            return 0

        args.work.mkdir(parents=True, exist_ok=True)
        pre_sbl = args.work / "pre-sbl"
        pre_sbl.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.monkey000, pre_sbl / "monkey.000")
        shutil.copy2(args.monkey001, pre_sbl / "monkey.001")

        before_000 = sha256(args.monkey000)
        before_001 = sha256(args.monkey001)
        with tempfile.TemporaryDirectory(prefix="mi1-sbl-", dir=args.work) as temp_dir:
            sbl_chunks = generate_sbl_chunks(
                commands, args.samples_wav, Path(temp_dir), args.sample_rate, args.verbose
            )

        index_data = xor_data(args.monkey000.read_bytes())
        resource_data = xor_data(args.monkey001.read_bytes())
        new_index, new_resource_data, injected = rebuild_resource_data(
            resource_data, index_data, commands, sbl_chunks, args.verbose
        )
        if len(injected) != len(commands):
            raise InjectError(f"injected {len(injected)} of {len(commands)} SBL resources")
        verified_sbl = verify_rebuilt_resources(new_index, new_resource_data, commands)

        args.monkey000.write_bytes(xor_data(new_index))
        args.monkey001.write_bytes(xor_data(new_resource_data))
        after_000 = sha256(args.monkey000)
        after_001 = sha256(args.monkey001)

        print("MI1 SBL injection complete.")
        print(f"Injected resources: {len(injected)}")
        print(f"Verified injected resources: {verified_sbl}")
        for item in injected:
            print(
                f"  room {item['room_id']:03d} sound {item['sound_id']:03d}: "
                f"{item['source']} SBL {item['old_sbl_size']} -> {item['new_sbl_size']} bytes; "
                f"SOUN {item['old_soun_size']} -> {item['new_soun_size']} bytes"
            )
        print(f"pre-SBL backup: {pre_sbl}")
        print(f"monkey.000 sha256: {before_000} -> {after_000}")
        print(f"monkey.001 sha256: {before_001} -> {after_001}")
        if before_000 == after_000:
            print("warning: monkey.000 did not change")
        if before_001 == after_001:
            raise InjectError("monkey.001 did not change after SBL injection")
        return 0
    except (OSError, subprocess.CalledProcessError, wav2sbl.SblError, InjectError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
