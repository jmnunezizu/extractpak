import json
import struct
from pathlib import Path

from scummkit import speech_manifest


def _field(text: str, size: int) -> bytes:
    data = text.encode("cp1252") + b"\0"
    return data + (b" " * (size - len(data)))


def _record(sample: str, text: str, room: int = 32, script: int = 1, offset: int = 10, message: int = 0) -> bytes:
    header = bytearray(16)
    struct.pack_into("<HHHH", header, 4, room, script, offset, message)
    fields = [_field(text, speech_manifest.MI1_TEXT_FIELD_SIZE)]
    fields.extend(_field("", speech_manifest.MI1_TEXT_FIELD_SIZE) for _ in range(4))
    return bytes(header) + b"".join(fields) + _field(sample, speech_manifest.MI1_SAMPLE_NAME_SIZE)


def test_parse_mi1_speech_info_and_build_manifest(tmp_path: Path) -> None:
    speech_info = tmp_path / "speech.info"
    speech_info.write_bytes(
        b"".join(
            [
                _record("GUY_32_alley_1_1", "Hello", room=32, script=7, offset=12, message=1),
                _record("GUY_32_alley_1_1", "Hello duplicate", room=32, script=7, offset=12, message=1),
                _record("STN_59_stans_89_1", "Price", room=59, script=3, offset=20, message=2),
            ]
        )
    )

    records = speech_manifest.parse_mi1_speech_info(speech_info)
    entries = speech_manifest.build_mi1_manifest(records)

    assert len(records) == 3
    assert len(entries) == 2
    assert entries[0].speech_id == 1
    assert entries[0].sample == "GUY_32_alley_1_1"
    assert entries[0].room == 32
    assert entries[0].script == 7
    assert entries[0].local_script_offset == 12
    assert entries[0].message_index == 1
    assert entries[1].speech_id == 2


def test_write_manifest_and_monster_table(tmp_path: Path) -> None:
    records = [
        speech_manifest.Mi1SpeechRecord(
            record_index=1,
            room=1,
            script=2,
            local_script_offset=3,
            message_index=4,
            text="Hello",
            sample="sample_a",
        )
    ]
    entries = speech_manifest.build_mi1_manifest(records)
    manifest = tmp_path / "manifest.json"
    table = tmp_path / "monster.tbl"

    speech_manifest.write_manifest(manifest, speech_manifest.manifest_payload("mi1", records, entries))
    speech_manifest.write_monster_table(table, entries)

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["format"] == "scummkit-speech-manifest-v1"
    assert payload["entries"][0]["speech_id_hex"] == "00000001"
    assert table.read_text(encoding="ascii") == "00000001sample_a\n"


def test_compare_generated_manifest_with_builder_table(tmp_path: Path) -> None:
    builder_table = tmp_path / "monster.tbl"
    builder_table.write_text("00000010sample_a\n00000020builder_only\n", encoding="ascii")
    entries = [
        speech_manifest.SpeechManifestEntry(
            speech_id=1,
            sample="sample_a",
            source="speech.info",
            first_record_index=1,
            room=1,
            script=0,
            local_script_offset=0,
            message_index=0,
            text="Hello",
        ),
        speech_manifest.SpeechManifestEntry(
            speech_id=2,
            sample="generated_only",
            source="speech.info",
            first_record_index=2,
            room=1,
            script=0,
            local_script_offset=0,
            message_index=0,
            text="Bye",
        ),
    ]

    comparison = speech_manifest.compare_with_builder(entries, builder_table)

    assert comparison.generated_count == 2
    assert comparison.builder_count == 2
    assert comparison.common_count == 1
    assert comparison.missing_from_generated == ["builder_only"]
    assert comparison.extra_in_generated == ["generated_only"]


def test_classification_buckets_builder_only_and_extra_samples(tmp_path: Path, monkeypatch) -> None:
    builder_table = tmp_path / "monster.tbl"
    builder_table.write_text(
        "00000010sample_a\n"
        "00000020sfx_only\n"
        "00000030_cdt_hit01\n"
        "00000040base_sample_alt\n"
        "00000050unknown_only\n",
        encoding="ascii",
    )
    entries = [
        speech_manifest.SpeechManifestEntry(
            speech_id=1,
            sample="sample_a",
            source="speech.info",
            first_record_index=1,
            room=1,
            script=0,
            local_script_offset=0,
            message_index=0,
            text="Hello",
        ),
        speech_manifest.SpeechManifestEntry(
            speech_id=2,
            sample="generated_only",
            source="speech.info",
            first_record_index=2,
            room=1,
            script=0,
            local_script_offset=0,
            message_index=0,
            text="Bye",
        ),
        speech_manifest.SpeechManifestEntry(
            speech_id=3,
            sample="base_sample",
            source="speech.info",
            first_record_index=3,
            room=1,
            script=0,
            local_script_offset=0,
            message_index=0,
            text="Base",
        ),
    ]
    monkeypatch.setattr(speech_manifest, "xwb_sample_names", lambda path: {"sfx_only"})

    classification = speech_manifest.classify_comparison(entries, builder_table, sfxnew=tmp_path / "SFXNew.xwb")

    assert classification.missing_from_generated["sfxnew"] == ["sfx_only"]
    assert classification.missing_from_generated["voice_special_case"] == ["_cdt_hit01"]
    assert classification.missing_from_generated["speech_info_alt_variant"] == ["base_sample_alt"]
    assert classification.missing_from_generated["unknown_builder_only"] == ["unknown_only"]
    assert classification.extra_in_generated["base_for_builder_alt_variant"] == ["base_sample"]
    assert classification.extra_in_generated["unused_speech_info"] == ["generated_only"]


def test_write_classification_payload(tmp_path: Path) -> None:
    classification = speech_manifest.SpeechClassification(
        generated_count=2,
        builder_count=3,
        common_count=1,
        missing_from_generated={
            "sfxnew": ["sfx_only"],
            "voice_special_case": [],
            "speech_info_alt_variant": [],
            "unknown_builder_only": ["unknown_only"],
        },
        extra_in_generated={
            "base_for_builder_alt_variant": [],
            "unused_speech_info": ["generated_only"],
        },
    )
    out = tmp_path / "diff.json"

    speech_manifest.write_classification(out, classification)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["format"] == "scummkit-mi1-speech-diff-v1"
    assert payload["missing_from_generated"]["sfxnew"]["count"] == 1
    assert payload["extra_in_generated"]["unused_speech_info"]["samples"] == ["generated_only"]


def test_build_builder_coverage_manifest_matches_builder_samples(tmp_path: Path, monkeypatch) -> None:
    builder_table = tmp_path / "monster.tbl"
    builder_table.write_text(
        "00000010sample_a\n"
        "00000020sfx_only\n"
        "00000030_cdt_hit01\n"
        "00000040base_sample_alt\n",
        encoding="ascii",
    )
    entries = [
        speech_manifest.SpeechManifestEntry(
            speech_id=1,
            sample="sample_a",
            source="speech.info",
            first_record_index=1,
            room=1,
            script=0,
            local_script_offset=0,
            message_index=0,
            text="Hello",
        ),
        speech_manifest.SpeechManifestEntry(
            speech_id=2,
            sample="base_sample",
            source="speech.info",
            first_record_index=2,
            room=1,
            script=0,
            local_script_offset=0,
            message_index=0,
            text="Base",
        ),
        speech_manifest.SpeechManifestEntry(
            speech_id=3,
            sample="unused",
            source="speech.info",
            first_record_index=3,
            room=1,
            script=0,
            local_script_offset=0,
            message_index=0,
            text="Unused",
        ),
    ]
    monkeypatch.setattr(speech_manifest, "xwb_sample_names", lambda path: {"sfx_only"})

    coverage = speech_manifest.build_builder_coverage_manifest(entries, builder_table, sfxnew=tmp_path / "SFXNew.xwb")

    assert [entry.sample for entry in coverage] == ["sample_a", "sfx_only", "_cdt_hit01", "base_sample_alt"]
    assert [entry.speech_id for entry in coverage] == [1, 2, 3, 4]
    assert [entry.source for entry in coverage] == [
        "speech.info",
        "sfxnew",
        "voice-special-case",
        "speech.info-alt-variant",
    ]
    assert speech_manifest.compare_with_builder(coverage, builder_table).missing_from_generated == []
    assert speech_manifest.compare_with_builder(coverage, builder_table).extra_in_generated == []
