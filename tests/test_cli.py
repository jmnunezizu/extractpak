from pathlib import Path

from talkiebuilder import cli
from talkiebuilder.runner import Runner


def test_cli_argument_parsing() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "build",
            "mi2",
            "--pak",
            "monkey2.pak",
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
    assert args.game == "mi2"
    assert args.audio == "ogg"
    assert args.verbose is True


def test_mi2_dry_run_does_not_write_final_outputs(tmp_path: Path, monkeypatch) -> None:
    from talkiebuilder import mi2

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
