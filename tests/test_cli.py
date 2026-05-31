from pathlib import Path

from scummkit import cli
from scummkit.runner import Runner


def test_cli_argument_parsing() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "build",
            "mi1",
            "--pak",
            "monkey1.pak",
            "--builder",
            "builder",
            "--out",
            "out",
            "--audio",
            "ogg",
            "--verbose",
        ]
    )

    assert args.command == "build"
    assert args.game == "mi1"
    assert args.audio == "ogg"
    assert args.music == "hybrid"
    assert args.verbose is True


def test_cli_mi1_music_argument_parsing() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "build",
            "mi1",
            "--pak",
            "monkey1.pak",
            "--builder",
            "builder",
            "--out",
            "out",
            "--audio",
            "ogg",
            "--music",
            "se",
        ]
    )

    assert args.music == "se"


def test_cli_inspect_argument_parsing() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "inspect",
            "mi1",
            "resource",
            "--game-dir",
            "game",
            "--room",
            "41",
            "--id",
            "71",
            "--compare",
            "pre-sbl",
        ]
    )

    assert args.command == "inspect"
    assert args.game == "mi1"
    assert args.inspect_action == "resource"
    assert args.type == "sound"
    assert args.room == 41
    assert args.id == 71


def test_mi2_dry_run_does_not_write_final_outputs(tmp_path: Path, monkeypatch) -> None:
    from scummkit import mi2

    pak = tmp_path / "app" / "monkey2.pak"
    builder = tmp_path / "builder"
    out = tmp_path / "out"
    audio = pak.parent / "audio"
    tools = builder / "tools"
    audio.mkdir(parents=True)
    tools.mkdir(parents=True)
    pak.write_bytes(b"pak")
    (builder / "readme.txt").write_text("readme")
    for name in ("patch02.000", "patch02.001", "monster.tbl"):
        (tools / name).write_bytes(b"patch")
    for name in ("Speech.xwb", "Patch.xwb"):
        (audio / name).write_bytes(b"xwb")

    monkeypatch.setattr(Runner, "require_tool", lambda self, name, hint: None)
    monkeypatch.setattr(mi2, "require_audio_tools", lambda runner, audio: None)

    mi2.build(mi2.BuildOptions(pak=pak, builder=builder, out=out, audio="ogg", dry_run=True))

    assert not (out / "monkey2.000").exists()
    assert not (out / "monkey2.sog").exists()


def _write_music_fixture(out: Path) -> None:
    cd = out / "cd_music_ogg"
    se = out / "se_music_ogg"
    cd.mkdir(parents=True)
    se.mkdir()
    for track in (1, 8, 24):
        (cd / f"track{track}.ogg").write_text(f"cd {track}")
    for track in (1, 8, 25, 26, 29):
        (se / f"track{track}.ogg").write_text(f"se {track}")
    (se / "track8_no_sfx.ogg").write_text("unused")


def test_mi1_hybrid_root_music_uses_cd_plus_extended_se(tmp_path: Path) -> None:
    from scummkit import mi1

    out = tmp_path / "out"
    _write_music_fixture(out)

    copied = mi1._copy_default_music_to_root(out, "ogg", "hybrid", verbose=False)

    assert copied == 6
    assert (out / "track1.ogg").read_text() == "cd 1"
    assert (out / "track8.ogg").read_text() == "cd 8"
    assert (out / "track24.ogg").read_text() == "cd 24"
    assert (out / "track25.ogg").read_text() == "se 25"
    assert (out / "track26.ogg").read_text() == "se 26"
    assert (out / "track29.ogg").read_text() == "se 29"
    assert not (out / "track8_no_sfx.ogg").exists()


def test_mi1_cd_root_music_only_uses_cd_tracks(tmp_path: Path) -> None:
    from scummkit import mi1

    out = tmp_path / "out"
    _write_music_fixture(out)

    copied = mi1._copy_default_music_to_root(out, "ogg", "cd", verbose=False)

    assert copied == 3
    assert (out / "track1.ogg").read_text() == "cd 1"
    assert (out / "track8.ogg").read_text() == "cd 8"
    assert (out / "track24.ogg").read_text() == "cd 24"
    assert not (out / "track25.ogg").exists()


def test_mi1_se_root_music_only_uses_se_tracks(tmp_path: Path) -> None:
    from scummkit import mi1

    out = tmp_path / "out"
    _write_music_fixture(out)

    copied = mi1._copy_default_music_to_root(out, "ogg", "se", verbose=False)

    assert copied == 6
    assert (out / "track1.ogg").read_text() == "se 1"
    assert (out / "track8.ogg").read_text() == "se 8"
    assert (out / "track25.ogg").read_text() == "se 25"
    assert (out / "track29.ogg").read_text() == "se 29"
    assert (out / "track8_no_sfx.ogg").read_text() == "unused"
