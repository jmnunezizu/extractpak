from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path

from . import monster
from . import voices
from . import xwb


MI1_SPEECH_RECORD_SIZE = 1328
MI1_TEXT_FIELD_SIZE = 256
MI1_TEXT_FIELD_COUNT = 5
MI1_HEADER_SIZE = 16
MI1_SAMPLE_NAME_SIZE = 32


class SpeechManifestError(RuntimeError):
    pass


@dataclass(frozen=True)
class Mi1SpeechRecord:
    record_index: int
    room: int
    script: int
    local_script_offset: int
    message_index: int
    text: str
    sample: str


@dataclass(frozen=True)
class SpeechManifestEntry:
    speech_id: int
    sample: str
    source: str
    first_record_index: int
    room: int
    script: int
    local_script_offset: int
    message_index: int
    text: str


@dataclass(frozen=True)
class SpeechComparison:
    generated_count: int
    builder_count: int
    common_count: int
    missing_from_generated: list[str]
    extra_in_generated: list[str]


@dataclass(frozen=True)
class SpeechClassification:
    generated_count: int
    builder_count: int
    common_count: int
    missing_from_generated: dict[str, list[str]]
    extra_in_generated: dict[str, list[str]]


def _decode_field(data: bytes) -> str:
    text = data.split(b"\0", 1)[0].decode("cp1252", errors="replace")
    return text.rstrip(" ")


def parse_mi1_speech_info(path: Path) -> list[Mi1SpeechRecord]:
    blob = path.read_bytes()
    if len(blob) % MI1_SPEECH_RECORD_SIZE != 0:
        raise SpeechManifestError(
            f"{path}: size {len(blob)} is not a multiple of MI1 speech.info record size {MI1_SPEECH_RECORD_SIZE}"
        )

    records: list[Mi1SpeechRecord] = []
    for record_index, offset in enumerate(range(0, len(blob), MI1_SPEECH_RECORD_SIZE), 1):
        record = blob[offset : offset + MI1_SPEECH_RECORD_SIZE]
        room, script, local_script_offset, message_index = struct.unpack_from("<HHHH", record, 4)
        text = _decode_field(record[MI1_HEADER_SIZE : MI1_HEADER_SIZE + MI1_TEXT_FIELD_SIZE])
        name_offset = MI1_HEADER_SIZE + (MI1_TEXT_FIELD_COUNT * MI1_TEXT_FIELD_SIZE)
        sample = _decode_field(record[name_offset : name_offset + MI1_SAMPLE_NAME_SIZE])
        if not sample:
            continue
        records.append(
            Mi1SpeechRecord(
                record_index=record_index,
                room=room,
                script=script,
                local_script_offset=local_script_offset,
                message_index=message_index,
                text=text,
                sample=sample,
            )
        )
    if not records:
        raise SpeechManifestError(f"{path}: no MI1 speech records found")
    return records


def build_mi1_manifest(records: list[Mi1SpeechRecord]) -> list[SpeechManifestEntry]:
    entries: list[SpeechManifestEntry] = []
    seen: set[str] = set()
    for record in records:
        if record.sample in seen:
            continue
        seen.add(record.sample)
        entries.append(
            SpeechManifestEntry(
                speech_id=len(entries) + 1,
                sample=record.sample,
                source="speech.info",
                first_record_index=record.record_index,
                room=record.room,
                script=record.script,
                local_script_offset=record.local_script_offset,
                message_index=record.message_index,
                text=record.text,
            )
        )
    return entries


def _entry_with_id(entry: SpeechManifestEntry, speech_id: int) -> SpeechManifestEntry:
    return SpeechManifestEntry(
        speech_id=speech_id,
        sample=entry.sample,
        source=entry.source,
        first_record_index=entry.first_record_index,
        room=entry.room,
        script=entry.script,
        local_script_offset=entry.local_script_offset,
        message_index=entry.message_index,
        text=entry.text,
    )


def _derived_entry(sample: str, source: str, speech_id: int) -> SpeechManifestEntry:
    return SpeechManifestEntry(
        speech_id=speech_id,
        sample=sample,
        source=source,
        first_record_index=0,
        room=0,
        script=0,
        local_script_offset=0,
        message_index=0,
        text="",
    )


def build_builder_coverage_manifest(
    entries: list[SpeechManifestEntry],
    builder_table: Path,
    *,
    sfxnew: Path | None = None,
) -> list[SpeechManifestEntry]:
    classification = classify_comparison(entries, builder_table, sfxnew=sfxnew)
    if classification.missing_from_generated["unknown_builder_only"]:
        raise SpeechManifestError(
            "cannot build MI1 builder-coverage manifest with unknown builder-only samples: "
            + ", ".join(classification.missing_from_generated["unknown_builder_only"][:20])
        )

    by_sample = {entry.sample: entry for entry in entries}
    unused = set(classification.extra_in_generated["unused_speech_info"])
    generated_alt_bases = set(classification.extra_in_generated["base_for_builder_alt_variant"])
    builder_rows = monster.parse_table_or_raise(builder_table)
    sfx_names = set(classification.missing_from_generated["sfxnew"])
    special_names = set(classification.missing_from_generated["voice_special_case"])
    alt_names = set(classification.missing_from_generated["speech_info_alt_variant"])

    coverage: list[SpeechManifestEntry] = []
    for _offset, sample in builder_rows:
        speech_id = len(coverage) + 1
        if sample in by_sample and sample not in unused and sample not in generated_alt_bases:
            coverage.append(_entry_with_id(by_sample[sample], speech_id))
        elif sample in sfx_names:
            coverage.append(_derived_entry(sample, "sfxnew", speech_id))
        elif sample in special_names:
            coverage.append(_derived_entry(sample, "voice-special-case", speech_id))
        elif sample in alt_names:
            coverage.append(_derived_entry(sample, "speech.info-alt-variant", speech_id))
        else:
            raise SpeechManifestError(f"builder table sample is not covered by MI1 classification: {sample}")
    return coverage


def manifest_payload(
    game: str,
    records: list[Mi1SpeechRecord],
    entries: list[SpeechManifestEntry],
    *,
    coverage_mode: str = "speech-info",
) -> dict[str, object]:
    return {
        "format": "scummkit-speech-manifest-v1",
        "game": game,
        "coverage_mode": coverage_mode,
        "record_count": len(records),
        "unique_sample_count": len(entries),
        "id_policy": f"sequential SCUMMKit {coverage_mode} order; not Ultimate Talkie MONSTER offsets",
        "entries": [
            {
                "speech_id": entry.speech_id,
                "speech_id_hex": f"{entry.speech_id:08x}",
                "sample": entry.sample,
                "source": entry.source,
                "first_record_index": entry.first_record_index,
                "room": entry.room,
                "script": entry.script,
                "local_script_offset": entry.local_script_offset,
                "message_index": entry.message_index,
                "text": entry.text,
            }
            for entry in entries
        ],
    }


def write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_monster_table(path: Path, entries: list[SpeechManifestEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{entry.speech_id:08x}{entry.sample}" for entry in entries]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def compare_with_builder(entries: list[SpeechManifestEntry], builder_table: Path) -> SpeechComparison:
    generated = {entry.sample for entry in entries}
    builder = {name for _offset, name in monster.parse_table_or_raise(builder_table)}
    return SpeechComparison(
        generated_count=len(generated),
        builder_count=len(builder),
        common_count=len(generated & builder),
        missing_from_generated=sorted(builder - generated),
        extra_in_generated=sorted(generated - builder),
    )


def xwb_sample_names(path: Path) -> set[str]:
    bank = xwb.parse_xwb(path)
    return {Path(xwb.safe_name(entry["name"], entry["index"])).stem for entry in bank["entries"]}


def classify_comparison(
    entries: list[SpeechManifestEntry],
    builder_table: Path,
    *,
    sfxnew: Path | None = None,
) -> SpeechClassification:
    comparison = compare_with_builder(entries, builder_table)
    sfx_names = xwb_sample_names(sfxnew) if sfxnew is not None else set()
    special_names = set(voices.MI1_SPECIAL_CASE_OUTPUTS)
    generated = {entry.sample for entry in entries}

    missing: dict[str, list[str]] = {
        "sfxnew": [],
        "voice_special_case": [],
        "speech_info_alt_variant": [],
        "unknown_builder_only": [],
    }
    for name in comparison.missing_from_generated:
        if name in sfx_names:
            missing["sfxnew"].append(name)
        elif name in special_names:
            missing["voice_special_case"].append(name)
        elif name.endswith("_alt") and name[:-4] in generated:
            missing["speech_info_alt_variant"].append(name)
        else:
            missing["unknown_builder_only"].append(name)

    alt_bases = {name[:-4] for name in missing["speech_info_alt_variant"]}
    extra: dict[str, list[str]] = {
        "base_for_builder_alt_variant": [],
        "unused_speech_info": [],
    }
    for name in comparison.extra_in_generated:
        if name in alt_bases:
            extra["base_for_builder_alt_variant"].append(name)
        else:
            extra["unused_speech_info"].append(name)
    return SpeechClassification(
        generated_count=comparison.generated_count,
        builder_count=comparison.builder_count,
        common_count=comparison.common_count,
        missing_from_generated=missing,
        extra_in_generated=extra,
    )


def classification_payload(classification: SpeechClassification) -> dict[str, object]:
    return {
        "format": "scummkit-mi1-speech-diff-v1",
        "generated_unique_samples": classification.generated_count,
        "builder_table_samples": classification.builder_count,
        "common_samples": classification.common_count,
        "missing_from_generated": {
            key: {
                "count": len(names),
                "samples": names,
            }
            for key, names in classification.missing_from_generated.items()
        },
        "extra_in_generated": {
            key: {
                "count": len(names),
                "samples": names,
            }
            for key, names in classification.extra_in_generated.items()
        },
        "notes": [
            "sfxnew entries exist directly in MI1 Special Edition SFXNew.xwb",
            "voice_special_case entries are generated by SCUMMKit's MI1 voice special-case pipeline",
            "speech_info_alt_variant entries are builder alternate names whose base sample exists in speech.info",
            "unknown_builder_only entries still need source/provenance analysis",
            "base_for_builder_alt_variant entries are speech.info samples whose _alt variant is used by the builder",
            "unused_speech_info entries appear in Special Edition speech.info but not in the builder monster.tbl",
        ],
    }


def write_classification(path: Path, classification: SpeechClassification) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(classification_payload(classification), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def format_comparison(comparison: SpeechComparison, title: str = "MI1 speech manifest comparison") -> str:
    lines = [
        f"{title}:",
        f"  generated unique samples: {comparison.generated_count}",
        f"  builder table samples:    {comparison.builder_count}",
        f"  common samples:           {comparison.common_count}",
        f"  missing from generated:   {len(comparison.missing_from_generated)}",
        f"  extra in generated:       {len(comparison.extra_in_generated)}",
    ]
    if comparison.missing_from_generated:
        lines.append("  first missing:")
        lines.extend(f"    {name}" for name in comparison.missing_from_generated[:20])
    if comparison.extra_in_generated:
        lines.append("  first extra:")
        lines.extend(f"    {name}" for name in comparison.extra_in_generated[:20])
    lines.append("")
    lines.append("Note: generated speech IDs are SCUMMKit IDs, not recovered Ultimate Talkie MONSTER offsets.")
    return "\n".join(lines)


def format_classification(classification: SpeechClassification) -> str:
    lines = [
        "MI1 speech diff classification:",
        f"  generated unique samples: {classification.generated_count}",
        f"  builder table samples:    {classification.builder_count}",
        f"  common samples:           {classification.common_count}",
        "  missing from generated:",
    ]
    for key, names in classification.missing_from_generated.items():
        lines.append(f"    {key}: {len(names)}")
    lines.append("  extra in generated:")
    for key, names in classification.extra_in_generated.items():
        lines.append(f"    {key}: {len(names)}")
    unknown = classification.missing_from_generated.get("unknown_builder_only", [])
    if unknown:
        lines.append("  first unknown builder-only samples:")
        lines.extend(f"    {name}" for name in unknown[:20])
    lines.append("")
    lines.append("Note: classification is based on sample names; generated IDs still do not match Ultimate Talkie offsets.")
    return "\n".join(lines)
