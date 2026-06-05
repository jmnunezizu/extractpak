from pathlib import Path

from scummkit import mi1_resources, mi1_room_audio


def _entry(resource_type: str, resource_id: int, room_id: int, rel: int, size: int, tag: str) -> mi1_resources.ResourceEntry:
    return mi1_resources.ResourceEntry(
        resource_type=resource_type,
        resource_id=resource_id,
        room_id=room_id,
        relative_offset=rel,
        absolute_offset=8 + rel,
        size=size,
        tag=tag,
    )


def test_room_audio_report_summarises_sounds_scripts_and_root_tracks(tmp_path: Path) -> None:
    sound = (
        b"SOUN"
        + (8 + 8 + 8 + 3).to_bytes(4, "big")
        + b"SOU "
        + (8 + 3).to_bytes(4, "big")
        + b"SBL "
        + (3).to_bytes(4, "big")
        + b"abc"
    )
    script = b"SCRP\x00\x00\x00\x0c\x08\x19\x63\x00"
    encd = b"ENCD" + (14).to_bytes(4, "big") + b"\x02\x19\x1c\x08\x00\x00"
    room_container = b"ROOM" + (8 + len(encd)).to_bytes(4, "big") + encd
    room = room_container + sound + script
    game = mi1_resources.GameResources(
        index_data=b"",
        resource_data=room,
        room_payloads={36: room},
        room_offsets={36: 0},
        entries=[
            _entry("sound", 8, 36, len(room_container), len(sound), "SOUN"),
            _entry("script", 1, 36, len(room_container) + len(sound), len(script), "SCRP"),
        ],
    )
    (tmp_path / "track25.ogg").write_bytes(b"OggS")

    report = mi1_room_audio.build_report_from_resources(game=game, game_dir=tmp_path, room_id=36)

    assert report.sounds[0].sound_id == 8
    assert report.sounds[0].child_tags == ["SBL "]
    assert report.sounds[0].native_sbl_source == "8_sound_SBL_growl.wav"
    assert report.scripts[0].referenced_sound_ids == [8]
    assert report.scripts[0].referenced_root_tracks == [25]
    assert report.embedded_scripts[0].tag == "ENCD"
    assert report.embedded_scripts[0].referenced_sound_ids == [8]
    assert report.embedded_scripts[0].referenced_root_tracks == [25]
    assert report.embedded_scripts[0].audio_opcodes[0].name == "startMusic"
    assert report.embedded_scripts[0].audio_opcodes[0].argument == 25
    assert report.embedded_scripts[0].audio_opcodes[0].argument_kind == "direct"
    assert report.embedded_scripts[0].audio_opcodes[1].name == "startSound"
    assert report.embedded_scripts[0].audio_opcodes[1].argument == 8
    assert report.embedded_scripts[0].decode_issues == []
    assert report.root_tracks[0].track == 25


def test_room_audio_report_skips_lscr_local_script_id(tmp_path: Path) -> None:
    lscr = b"LSCR" + (11).to_bytes(4, "big") + b"\x02\x1c\x08"
    room_container = b"ROOM" + (8 + len(lscr)).to_bytes(4, "big") + lscr
    game = mi1_resources.GameResources(
        index_data=b"",
        resource_data=room_container,
        room_payloads={36: room_container},
        room_offsets={36: 0},
        entries=[],
    )

    report = mi1_room_audio.build_report_from_resources(game=game, game_dir=tmp_path, room_id=36)

    assert report.embedded_scripts[0].tag == "LSCR"
    assert report.embedded_scripts[0].audio_opcodes[0].name == "startSound"
    assert report.embedded_scripts[0].audio_opcodes[0].argument == 8
