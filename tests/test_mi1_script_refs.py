from pathlib import Path

from scummkit import mi1_resources, mi1_script_refs


def test_script_reference_report_finds_candidate_bytes(tmp_path: Path) -> None:
    script = b"SCRP\x00\x00\x00\x0e\x24\x08\x1c\x24\x35\x19"
    game = mi1_resources.GameResources(
        index_data=b"",
        resource_data=script,
        room_payloads={88: script},
        room_offsets={88: 0},
        entries=[
            mi1_resources.ResourceEntry(
                resource_type="script",
                resource_id=99,
                room_id=88,
                relative_offset=0,
                absolute_offset=8,
                size=len(script),
                tag="SCRP",
            )
        ],
    )

    original = mi1_resources._read_game_dir
    try:
        mi1_resources._read_game_dir = lambda _game_dir: game  # type: ignore[assignment]
        report = mi1_script_refs.build_report(
            game_dir=tmp_path,
            rooms=[36, 53],
            sounds=[8],
            tracks=[25, 28],
        )
    finally:
        mi1_resources._read_game_dir = original  # type: ignore[assignment]

    assert len(report.scripts) == 1
    assert report.scripts[0].room_refs[0].value == 36
    assert report.scripts[0].room_refs[1].value == 53
    assert report.scripts[0].sound_refs[0].value == 8
    assert report.scripts[0].track_refs[0].value == 25
    assert report.scripts[0].track_refs[1].value == 28
