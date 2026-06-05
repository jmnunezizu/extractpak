from scummkit import mi1_resources


def _game(room_payload: bytes, *, rel: int = 0) -> mi1_resources.GameResources:
    return mi1_resources.GameResources(
        index_data=b"index",
        resource_data=b"data" + room_payload,
        room_payloads={1: room_payload},
        room_offsets={1: 0},
        entries=[
            mi1_resources.ResourceEntry(
                resource_type="script",
                resource_id=1,
                room_id=1,
                relative_offset=rel,
                absolute_offset=8 + rel,
                size=len(room_payload) - rel,
                tag="SCRP",
            )
        ],
    )


def test_diff_games_reports_changed_resource_and_room() -> None:
    original = _game(b"SCRP\x00\x00\x00\x0coriginal")
    patched = _game(b"SCRP\x00\x00\x00\x0bpatched")

    summary, room_diffs, resource_diffs = mi1_resources.diff_games(original, patched)

    assert summary.rooms_changed == 1
    assert summary.resources_changed == 1
    assert room_diffs[0].room_id == 1
    assert resource_diffs[0].resource_type == "script"
    assert resource_diffs[0].resource_id == 1
    assert resource_diffs[0].status == "changed"
    assert resource_diffs[0].analysis is not None
    assert resource_diffs[0].analysis["byte_changes"]["block_count"] >= 1


def test_diff_games_reports_moved_only_resource() -> None:
    original = _game(b"padSCRP\x00\x00\x00\x08", rel=3)
    patched = _game(b"xxpadSCRP\x00\x00\x00\x08", rel=5)

    summary, _room_diffs, resource_diffs = mi1_resources.diff_games(original, patched)

    assert summary.resources_moved_only == 1
    assert resource_diffs[0].status == "moved-only"
    assert resource_diffs[0].original_relative_offset == 3
    assert resource_diffs[0].patched_relative_offset == 5


def test_sound_analysis_reports_nested_sou_children() -> None:
    sound = (
        b"SOUN"
        + (8 + 8 + 8 + 3).to_bytes(4, "big")
        + b"SOU "
        + (8 + 3).to_bytes(4, "big")
        + b"SBL "
        + (3).to_bytes(4, "big")
        + b"abc"
    )

    analysis = mi1_resources._resource_analysis("sound", None, sound)

    assert analysis["patched_sound"]["valid"] is True
    sou = analysis["patched_sound"]["children"][0]
    assert sou["tag"] == "SOU "
    assert sou["children"][0]["tag"] == "SBL "
    assert sou["children"][0]["payload_size"] == 3
