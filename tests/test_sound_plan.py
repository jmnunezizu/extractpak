from scummkit import mi1_resources, patch_classify, sound_plan


def _sound_diff(sound_id: int, room_id: int, status: str, tags: list[str]) -> mi1_resources.ResourceDiff:
    return mi1_resources.ResourceDiff(
        resource_type="sound",
        resource_id=sound_id,
        original_room_id=room_id if status != "added" else None,
        patched_room_id=room_id,
        original_size=10 if status != "added" else None,
        patched_size=20,
        original_sha256=None,
        patched_sha256=None,
        original_relative_offset=None,
        patched_relative_offset=0,
        status=status,
        analysis={
            "patched_sound": {
                "children": [
                    {
                        "tag": "SOU ",
                        "children": [{"tag": tag, "payload_size": 1, "total_size": 9} for tag in tags],
                    }
                ]
            }
        },
    )


def test_sound_plan_marks_native_sbl_coverage() -> None:
    diffs = [
        _sound_diff(67, 41, "changed", ["SBL "]),
        _sound_diff(999, 1, "added", ["ROL ", "GMD ", "ADL "]),
    ]
    classifications = patch_classify.classify_resources(diffs)

    items = sound_plan.build_mi1_sound_plan(diffs, classifications)

    assert items[0].sound_id == 999
    assert items[0].native_sbl_covered is False
    assert items[1].sound_id == 67
    assert items[1].native_sbl_covered is True
    assert items[1].native_sbl_source == "_cdt_bubble.wav"


def test_sound_plan_payload_summarizes_uncovered_categories() -> None:
    diffs = [_sound_diff(999, 1, "added", ["ROL ", "GMD ", "ADL "])]
    items = sound_plan.build_mi1_sound_plan(diffs, patch_classify.classify_resources(diffs))

    payload = sound_plan.payload(items)

    assert payload["summary"]["total"] == 1
    assert payload["summary"]["native_sbl_uncovered"] == 1
    assert payload["summary"]["uncovered_by_category"]["added-music-or-rich-sound"] == 1
