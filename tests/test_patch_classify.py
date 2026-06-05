from __future__ import annotations

from scummkit import mi1_resources, patch_classify


def _diff(resource_type: str, status: str, *, size: int = 100, tags: list[str] | None = None) -> mi1_resources.ResourceDiff:
    analysis = None
    if resource_type == "sound":
        analysis = {
            "patched_sound": {
                "children": [
                    {
                        "tag": "SOU ",
                        "children": [{"tag": tag, "payload_size": 1, "total_size": 9} for tag in tags or []],
                    }
                ]
            }
        }
    return mi1_resources.ResourceDiff(
        resource_type=resource_type,
        resource_id=1,
        original_room_id=1 if status != "added" else None,
        patched_room_id=1,
        original_size=10 if status != "added" else None,
        patched_size=size,
        original_sha256=None,
        patched_sha256=None,
        original_relative_offset=None,
        patched_relative_offset=0,
        status=status,
        analysis=analysis,
    )


def test_classify_sound_patterns() -> None:
    classifications = patch_classify.classify_resources(
        [
            _diff("sound", "added", size=32),
            _diff("sound", "added", tags=["ROL ", "GMD ", "ADL "]),
            _diff("sound", "changed", tags=["SBL "]),
            _diff("sound", "changed", tags=["SBL ", "ADL "]),
        ]
    )

    assert [item.category for item in classifications] == [
        "sound-control-placeholder",
        "added-music-or-rich-sound",
        "sbl-sfx",
        "sfx-sound-change",
    ]


def test_classification_payload_summarizes_categories() -> None:
    classifications = patch_classify.classify_resources(
        [
            _diff("script", "added"),
            _diff("costume", "changed"),
            _diff("charset", "moved-only"),
        ]
    )

    payload = patch_classify.classification_payload(classifications)

    assert payload["summary"]["by_category"]["added-script"] == 1
    assert payload["summary"]["by_category"]["costume-or-visual-fix"] == 1
    assert payload["summary"]["by_category"]["room-structure-only"] == 1
