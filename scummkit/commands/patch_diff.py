from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .. import mi1_resources, patch_classify, sound_plan
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("patch-diff", help="compare original and patched SCUMM resource files")
    games = parser.add_subparsers(dest="game", required=True)

    mi1 = games.add_parser("mi1", help="diff MI1 monkey.000/.001 resource changes")
    mi1.add_argument("--original-index", type=Path, required=True, help="original classic monkey1.000")
    mi1.add_argument("--original-data", type=Path, required=True, help="original classic monkey1.001")
    mi1.add_argument("--patched-index", type=Path, required=True, help="patched monkey.000")
    mi1.add_argument("--patched-data", type=Path, required=True, help="patched monkey.001")
    mi1.add_argument("--json-out", type=Path, help="optional JSON report output path")
    mi1.add_argument("--classify-out", type=Path, help="optional JSON resource classification output path")
    mi1.add_argument("--sound-plan-out", type=Path, help="optional JSON MI1 sound patch plan output path")
    mi1.add_argument("--limit", type=int, default=40, help="number of changed resources to print; default: 40")
    mi1.set_defaults(func=run_mi1)


def _payload(
    summary: mi1_resources.PatchDiffSummary,
    room_diffs: list[mi1_resources.RoomDiff],
    resource_diffs: list[mi1_resources.ResourceDiff],
) -> dict[str, object]:
    return {
        "format": "scummkit-mi1-patch-diff-v1",
        "summary": asdict(summary),
        "rooms": [asdict(item) for item in room_diffs],
        "resources": [asdict(item) for item in resource_diffs],
    }


def _print_summary(
    summary: mi1_resources.PatchDiffSummary,
    room_diffs: list[mi1_resources.RoomDiff],
    resource_diffs: list[mi1_resources.ResourceDiff],
    limit: int,
    classifications: list[patch_classify.ResourceClassification] | None = None,
) -> None:
    status_order = {"added": 0, "removed": 1, "changed": 2, "moved-only": 3}
    type_order = {"script": 0, "sound": 1, "costume": 2, "charset": 3}
    sorted_resources = sorted(
        resource_diffs,
        key=lambda item: (
            status_order.get(item.status, 99),
            type_order.get(item.resource_type, 99),
            item.patched_room_id if item.patched_room_id is not None else item.original_room_id or 0,
            item.resource_id,
        ),
    )
    by_type: dict[str, dict[str, int]] = {}
    for item in resource_diffs:
        by_type.setdefault(item.resource_type, {}).setdefault(item.status, 0)
        by_type[item.resource_type][item.status] += 1

    print("MI1 patch diff:")
    print(f"  index sha256: {summary.original_index_sha256} -> {summary.patched_index_sha256}")
    print(f"  data sha256:  {summary.original_data_sha256} -> {summary.patched_data_sha256}")
    print(
        "  rooms: "
        f"added={summary.rooms_added} removed={summary.rooms_removed} changed={summary.rooms_changed}"
    )
    print(
        "  resources: "
        f"added={summary.resources_added} removed={summary.resources_removed} "
        f"changed={summary.resources_changed} moved_only={summary.resources_moved_only}"
    )
    if by_type:
        print("  resources by type:")
        for resource_type in sorted(by_type, key=lambda key: type_order.get(key, 99)):
            counts = by_type[resource_type]
            print(
                f"    {resource_type:<7} "
                f"added={counts.get('added', 0)} removed={counts.get('removed', 0)} "
                f"changed={counts.get('changed', 0)} moved_only={counts.get('moved-only', 0)}"
            )
    if classifications is not None:
        payload = patch_classify.classification_payload(classifications)
        print("  classifications:")
        for category, count in payload["summary"]["by_category"].items():
            print(f"    {category}: {count}")
    if room_diffs:
        print("  changed rooms:")
        for item in room_diffs[:limit]:
            print(
                f"    room={item.room_id:03d} status={item.status} "
                f"size={item.original_size}->{item.patched_size}"
            )
        if len(room_diffs) > limit:
            print(f"    ... {len(room_diffs) - limit} more")
    if resource_diffs:
        print("  resources needing attention:")
        for item in sorted_resources[:limit]:
            print(
                f"    type={item.resource_type:<7} id={item.resource_id:03d} status={item.status:<10} "
                f"room={item.original_room_id}->{item.patched_room_id} "
                f"size={item.original_size}->{item.patched_size} "
                f"rel={item.original_relative_offset}->{item.patched_relative_offset}"
            )
        if len(resource_diffs) > limit:
            print(f"    ... {len(resource_diffs) - limit} more")


def run_mi1(args: argparse.Namespace) -> None:
    try:
        summary, room_diffs, resource_diffs = mi1_resources.diff_game_files(
            args.original_index,
            args.original_data,
            args.patched_index,
            args.patched_data,
        )
    except (OSError, mi1_resources.mi1_sbl.InjectError) as error:
        raise BuildError(str(error)) from error

    classifications = patch_classify.classify_resources(resource_diffs)
    sound_items = sound_plan.build_mi1_sound_plan(resource_diffs, classifications)
    _print_summary(summary, room_diffs, resource_diffs, args.limit, classifications)
    sound_payload = sound_plan.payload(sound_items)
    print("  sound plan:")
    print(f"    total: {sound_payload['summary']['total']}")
    print(f"    native SBL covered: {sound_payload['summary']['native_sbl_covered']}")
    print(f"    native SBL uncovered: {sound_payload['summary']['native_sbl_uncovered']}")
    for category, count in sound_payload["summary"]["uncovered_by_category"].items():
        print(f"    uncovered {category}: {count}")
    if args.json_out is not None:
        out = args.json_out.expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(_payload(summary, room_diffs, resource_diffs), indent=2) + "\n", encoding="utf-8")
        print(f"json: {out}")
    if args.classify_out is not None:
        out = args.classify_out.expanduser()
        patch_classify.write_classification(out, classifications)
        print(f"classification: {out}")
    if args.sound_plan_out is not None:
        out = args.sound_plan_out.expanduser()
        sound_plan.write_plan(out, sound_items)
        print(f"sound plan: {out}")
