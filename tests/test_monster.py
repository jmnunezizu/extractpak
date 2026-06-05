from pathlib import Path

import pytest

from scummkit import monster


def test_parse_monster_table(tmp_path: Path) -> None:
    table = tmp_path / "monster.tbl"
    table.write_text("00000010sample_a\n00000020sample_b\n", encoding="ascii")

    assert monster.parse_table(table) == [(0x10, "sample_a"), (0x20, "sample_b")]


def test_parse_monster_table_rejects_duplicate_ids(tmp_path: Path) -> None:
    table = tmp_path / "monster.tbl"
    table.write_text("00000010sample_a\n00000010sample_b\n", encoding="ascii")

    with pytest.raises(SystemExit):
        monster.parse_table(table)


def test_parse_monster_table_rejects_duplicate_samples(tmp_path: Path) -> None:
    table = tmp_path / "monster.tbl"
    table.write_text("00000010sample_a\n00000020sample_a\n", encoding="ascii")

    with pytest.raises(SystemExit):
        monster.parse_table(table)


def test_validate_table_warns_on_unexpected_game_count(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    table = tmp_path / "monster.tbl"
    table.write_text("00000010sample_a\n", encoding="ascii")

    assert monster.validate_table_for_game(table, "mi1") == [(0x10, "sample_a")]
    captured = capsys.readouterr()

    assert "expected 4393" in captured.err


def test_build_and_verify_monster_archive(tmp_path: Path) -> None:
    table = tmp_path / "monster.tbl"
    samples = tmp_path / "samples"
    out = tmp_path / "monkey.sog"
    samples.mkdir()
    table.write_text("00000010hello\n00000020bye\n", encoding="ascii")
    (samples / "hello.ogg").write_bytes(b"OggShello")
    (samples / "bye.ogg").write_bytes(b"OggSbye")

    monster.build_monster_archive(table, samples, out, "ogg")

    assert out.is_file()
    monster.verify_archive(out)


def test_build_monster_archive_rejects_missing_referenced_samples(tmp_path: Path) -> None:
    table = tmp_path / "monster.tbl"
    samples = tmp_path / "samples"
    out = tmp_path / "monkey.sog"
    samples.mkdir()
    table.write_text("00000010hello\n00000020bye\n", encoding="ascii")
    (samples / "hello.ogg").write_bytes(b"OggShello")

    with pytest.raises(monster.MonsterError, match="referenced sample"):
        monster.build_monster_archive(table, samples, out, "ogg")

    assert not out.exists()
