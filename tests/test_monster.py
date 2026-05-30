from pathlib import Path

from talkiebuilder import monster


def test_parse_monster_table(tmp_path: Path) -> None:
    table = tmp_path / "monster.tbl"
    table.write_text("00000010sample_a\n00000020sample_b\n", encoding="ascii")

    assert monster.parse_table(table) == [(0x10, "sample_a"), (0x20, "sample_b")]


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
