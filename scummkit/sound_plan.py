from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from . import mi1_resources, mi1_sbl, patch_classify


@dataclass(frozen=True)
class SoundPlanItem:
    room_id: int | None
    sound_id: int
    status: str
    category: str
    native_sbl_covered: bool
    native_sbl_source: str | None
    native_sbl_effects: list[str]
    native_sbl_child_index: int | None
    original_size: int | None
    patched_size: int | None
    child_tags: list[str]


def build_mi1_sound_plan(
    resource_diffs: list[mi1_resources.ResourceDiff],
    classifications: list[patch_classify.ResourceClassification],
) -> list[SoundPlanItem]:
    classes = {
        (item.resource_type, item.resource_id, item.status, item.room_id): item
        for item in classifications
    }
    native_sbl = {
        (command.room_id, command.sound_id): command
        for command in mi1_sbl.native_sbl_commands()
    }
    items: list[SoundPlanItem] = []
    for diff in resource_diffs:
        if diff.resource_type != "sound":
            continue
        room_id = diff.patched_room_id if diff.patched_room_id is not None else diff.original_room_id
        classification = classes.get((diff.resource_type, diff.resource_id, diff.status, room_id))
        command = native_sbl.get((room_id, diff.resource_id))
        items.append(
            SoundPlanItem(
                room_id=room_id,
                sound_id=diff.resource_id,
                status=diff.status,
                category=classification.category if classification is not None else "unknown",
                native_sbl_covered=command is not None,
                native_sbl_source=command.source if command is not None else None,
                native_sbl_effects=list(command.effects) if command is not None else [],
                native_sbl_child_index=command.sbl_child_index if command is not None else None,
                original_size=diff.original_size,
                patched_size=diff.patched_size,
                child_tags=patch_classify.sound_child_tags(diff),
            )
        )
    items.sort(key=lambda item: (item.room_id if item.room_id is not None else -1, item.sound_id, item.status))
    return items


def payload(items: list[SoundPlanItem]) -> dict[str, object]:
    by_category = Counter(item.category for item in items)
    by_coverage = Counter("covered" if item.native_sbl_covered else "uncovered" for item in items)
    uncovered_by_category = Counter(item.category for item in items if not item.native_sbl_covered)
    return {
        "format": "scummkit-mi1-sound-plan-v1",
        "summary": {
            "total": len(items),
            "native_sbl_covered": by_coverage.get("covered", 0),
            "native_sbl_uncovered": by_coverage.get("uncovered", 0),
            "by_category": dict(sorted(by_category.items())),
            "uncovered_by_category": dict(sorted(uncovered_by_category.items())),
        },
        "sounds": [asdict(item) for item in items],
    }


def write_plan(path: Path, items: list[SoundPlanItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload(items), indent=2) + "\n", encoding="utf-8")
