from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from . import mi1_resources


@dataclass(frozen=True)
class ResourceClassification:
    resource_type: str
    resource_id: int
    status: str
    room_id: int | None
    category: str
    confidence: str
    reason: str


def sound_child_tags(diff: mi1_resources.ResourceDiff) -> list[str]:
    analysis = diff.analysis or {}
    sound = analysis.get("patched_sound") or {}
    tags: list[str] = []
    for child in sound.get("children", []):
        for nested in child.get("children", []):
            tag = nested.get("tag")
            if isinstance(tag, str):
                tags.append(tag)
    return tags


def _classify_sound(diff: mi1_resources.ResourceDiff) -> tuple[str, str, str]:
    tags = sound_child_tags(diff)
    tag_set = set(tags)
    patched_size = diff.patched_size or 0
    if patched_size == 32 and not tags:
        return "sound-control-placeholder", "medium", "32-byte sound resource without nested SOU codec chunks"
    if "ROL " in tag_set or "GMD " in tag_set:
        if diff.status == "added":
            return "added-music-or-rich-sound", "medium", "added sound contains ROL/GMD music-capable child chunks"
        return "changed-music-or-rich-sound", "medium", "changed sound contains ROL/GMD music-capable child chunks"
    if tag_set == {"SBL "}:
        return "sbl-sfx", "high", "sound contains only an SBL child chunk"
    if "SBL " in tag_set:
        return "sfx-sound-change", "medium", "sound contains SBL plus other codec child chunks"
    if tags:
        return "non-sbl-sound-change", "low", "sound contains codec child chunks but no SBL child"
    return "unknown-sound-change", "low", "sound structure is not recognized"


def _classify_script(diff: mi1_resources.ResourceDiff) -> tuple[str, str, str]:
    if diff.status == "added":
        return "added-script", "medium", "script resource is added by the patch"
    analysis = diff.analysis or {}
    byte_changes = analysis.get("byte_changes") or {}
    patched_delta = (diff.patched_size or 0) - (diff.original_size or 0)
    if patched_delta > 0:
        return "expanded-script", "low", f"script grew by {patched_delta} bytes"
    if patched_delta < 0:
        return "shrunk-script", "low", f"script shrank by {-patched_delta} bytes"
    return "modified-script", "low", f"script changed in {byte_changes.get('block_count', 'unknown')} byte block(s)"


def _classify_resource(diff: mi1_resources.ResourceDiff) -> ResourceClassification:
    room_id = diff.patched_room_id if diff.patched_room_id is not None else diff.original_room_id
    if diff.status == "moved-only":
        category, confidence, reason = "room-structure-only", "high", "resource bytes are unchanged; only room/offset changed"
    elif diff.resource_type == "sound":
        category, confidence, reason = _classify_sound(diff)
    elif diff.resource_type == "script":
        category, confidence, reason = _classify_script(diff)
    elif diff.resource_type == "costume":
        category, confidence, reason = "costume-or-visual-fix", "medium", "costume resource changed or was added"
    elif diff.resource_type == "charset":
        category, confidence, reason = "room-structure-only", "high", "charset bytes are unchanged; only offset changed"
    else:
        category, confidence, reason = "unknown", "low", "resource type is not classified"
    return ResourceClassification(
        resource_type=diff.resource_type,
        resource_id=diff.resource_id,
        status=diff.status,
        room_id=room_id,
        category=category,
        confidence=confidence,
        reason=reason,
    )


def classify_resources(resource_diffs: list[mi1_resources.ResourceDiff]) -> list[ResourceClassification]:
    return [_classify_resource(diff) for diff in resource_diffs]


def classification_payload(classifications: list[ResourceClassification]) -> dict[str, object]:
    by_category = Counter(item.category for item in classifications)
    by_type_category = Counter((item.resource_type, item.category) for item in classifications)
    return {
        "format": "scummkit-mi1-patch-classification-v1",
        "summary": {
            "total": len(classifications),
            "by_category": dict(sorted(by_category.items())),
            "by_type_category": {
                f"{resource_type}:{category}": count
                for (resource_type, category), count in sorted(by_type_category.items())
            },
        },
        "resources": [asdict(item) for item in classifications],
    }


def write_classification(path: Path, classifications: list[ResourceClassification]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(classification_payload(classifications), indent=2) + "\n", encoding="utf-8")
