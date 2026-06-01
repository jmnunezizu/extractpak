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
    assert args.quiet is None


def test_cli_build_defaults_to_progress_output(monkeypatch) -> None:
    from scummkit import mi2
    from scummkit.commands import build

    captured = {}

    def fake_build(options: mi2.BuildOptions) -> None:
        captured["quiet"] = options.quiet

    monkeypatch.setattr(mi2, "build", fake_build)

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
        ]
    )

    assert args.quiet is None
    build.run(args)
    assert captured["quiet"] is True


def test_cli_build_verbose_disables_progress_output(monkeypatch) -> None:
    from scummkit import mi2
    from scummkit.commands import build

    captured = {}

    def fake_build(options: mi2.BuildOptions) -> None:
        captured["quiet"] = options.quiet
        captured["verbose"] = options.verbose

    monkeypatch.setattr(mi2, "build", fake_build)

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

    assert args.quiet is None
    build.run(args)
    assert captured["quiet"] is False
    assert captured["verbose"] is True


def test_cli_build_quiet_argument_parsing() -> None:
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
            "--quiet",
        ]
    )

    assert args.command == "build"
    assert args.game == "mi2"
    assert args.quiet is True
    assert args.verbose is False


def test_cli_build_no_progress_argument_parsing() -> None:
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
            "--no-progress",
        ]
    )

    assert args.command == "build"
    assert args.game == "mi2"
    assert args.quiet is False
    assert args.verbose is False


def test_cli_build_rejects_quiet_with_verbose() -> None:
    import pytest

    from scummkit.runner import BuildError

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
            "--quiet",
            "--verbose",
        ]
    )

    with pytest.raises(BuildError, match="either --quiet or --verbose"):
        from scummkit.commands import build

        build.run(args)


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


def test_cli_helper_argument_parsing() -> None:
    parser = cli.build_parser()

    xwb_args = parser.parse_args(["xwb", "Speech.xwb", "out", "--decode-wma"])
    assert xwb_args.command == "xwb"
    assert xwb_args.input == Path("Speech.xwb")
    assert xwb_args.output_dir == Path("out")
    assert xwb_args.decode_wma is True

    monster_args = parser.parse_args(
        [
            "monster",
            "--table",
            "monster.tbl",
            "--samples",
            "samples",
            "--out",
            "monkey.sog",
            "--format",
            "ogg",
        ]
    )
    assert monster_args.command == "monster"
    assert monster_args.format == "ogg"

    sbl_args = parser.parse_args(["wav2sbl", "in.wav", "out.sbl"])
    assert sbl_args.command == "wav2sbl"
    assert sbl_args.input == Path("in.wav")
    assert sbl_args.output == Path("out.sbl")


def test_command_modules_register_public_commands() -> None:
    parser = cli.build_parser()

    for argv, expected in [
        (["build", "mi2", "--pak", "p", "--builder", "b", "--out", "o", "--audio", "ogg"], "build"),
        (["doctor"], "doctor"),
        (["inspect", "mi1", "resources", "--game-dir", "game"], "inspect"),
        (["monster", "--verify", "monkey.sog"], "monster"),
        (["xwb", "Speech.xwb", "--list"], "xwb"),
        (["wav2sbl", "--verify", "sound.sbl"], "wav2sbl"),
    ]:
        assert parser.parse_args(argv).command == expected


def test_cli_inject_mi1_sbl_argument_parsing() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "inject",
            "mi1",
            "sbl",
            "--builder",
            "builder",
            "--samples-wav",
            "samples",
            "--monkey000",
            "monkey.000",
            "--monkey001",
            "monkey.001",
            "--work",
            "work",
            "--dry-run",
        ]
    )

    assert args.command == "inject"
    assert args.game == "mi1"
    assert args.inject_action == "sbl"
    assert args.builder == Path("builder")
    assert args.dry_run is True


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
    extractpak = tmp_path / "extractpak"
    extractpak.write_bytes(b"extractpak")
    (builder / "readme.txt").write_text("readme")
    for name in ("patch02.000", "patch02.001", "monster.tbl"):
        (tools / name).write_bytes(b"patch")
    for name in ("Speech.xwb", "Patch.xwb"):
        (audio / name).write_bytes(b"xwb")

    monkeypatch.setattr(Runner, "require_tool", lambda self, name, hint: None)
    monkeypatch.setattr(mi2, "require_audio_tools", lambda runner, audio: None)
    monkeypatch.setattr(mi2, "EXTRACTPAK", extractpak)

    mi2.build(mi2.BuildOptions(pak=pak, builder=builder, out=out, audio="ogg", dry_run=True))

    assert not (out / "monkey2.000").exists()
    assert not (out / "monkey2.sog").exists()


def test_voice_processing_plans_without_external_tools() -> None:
    from scummkit import voices

    mi1_plan = voices.plan_voice_steps("mi1", "ogg")
    mi2_plan = voices.plan_voice_steps("mi2", "ogg")

    assert any("SFXNew.xwb" in step for step in mi1_plan)
    assert any("_cdt_*" in step for step in mi2_plan)
    assert any("final-ogg" in step for step in mi1_plan)


def test_python_code_does_not_reference_shell_scripts() -> None:
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for path in (root / "scummkit").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in (
            "scripts/",
            "process-mi1-music.sh",
            "process-mi1-voices.sh",
            "process-mi2-voices.sh",
            "build-mi1-talkie.sh",
            "build-mi2-talkie.sh",
            "process-mi1-sbl.sh",
        ):
            if needle in text:
                offenders.append((path.relative_to(root), needle))

    assert offenders == []


def test_scripts_directory_contains_no_required_build_scripts() -> None:
    root = Path(__file__).resolve().parents[1]
    scripts = root / "scripts"
    if not scripts.exists():
        return

    required_scripts = {
        "process-mi1-music.sh",
        "process-mi1-voices.sh",
        "process-mi2-voices.sh",
        "build-mi1-talkie.sh",
        "build-mi2-talkie.sh",
        "process-mi1-sbl.sh",
    }
    present = {path.name for path in scripts.iterdir() if path.is_file()}

    assert present.isdisjoint(required_scripts)


def test_doctor_registration_with_out() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["doctor", "--out", "/tmp/scummkit-test", "--json"])

    assert args.command == "doctor"
    assert args.out == Path("/tmp/scummkit-test")
    assert args.json is True


def test_doctor_success_with_monkeypatched_tools(tmp_path: Path, monkeypatch) -> None:
    from scummkit import doctor

    extractpak = tmp_path / "extractpak"
    extractpak.write_text("#!/bin/sh\n", encoding="utf-8")
    extractpak.chmod(0o755)

    monkeypatch.setattr(doctor, "EXTRACTPAK", extractpak)
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/bin/{name}")

    checks = doctor.run_checks(tmp_path / "out")

    assert doctor.exit_code(checks) == 0
    assert {check.name for check in checks} >= {"python", "ffmpeg", "sox", "vgmstream-cli", "extractpak", "imports", "output"}


def test_doctor_failure_when_required_tool_missing(tmp_path: Path, monkeypatch) -> None:
    from scummkit import doctor

    extractpak = tmp_path / "extractpak"
    extractpak.write_text("#!/bin/sh\n", encoding="utf-8")
    extractpak.chmod(0o755)

    monkeypatch.setattr(doctor, "EXTRACTPAK", extractpak)
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None if name == "vgmstream-cli" else f"/bin/{name}")

    checks = doctor.run_checks()

    assert doctor.exit_code(checks) == 1
    assert any(check.name == "vgmstream-cli" and not check.ok for check in checks)


def test_doctor_json_reports_overall_status(tmp_path: Path, monkeypatch) -> None:
    import json

    from scummkit import doctor

    extractpak = tmp_path / "extractpak"
    extractpak.write_text("#!/bin/sh\n", encoding="utf-8")
    extractpak.chmod(0o755)

    monkeypatch.setattr(doctor, "EXTRACTPAK", extractpak)
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/bin/{name}")

    payload = json.loads(doctor.checks_to_json(doctor.run_checks()))

    assert payload["ok"] is True
    assert {check["name"] for check in payload["checks"]} >= {"python", "ffmpeg", "sox"}


def test_build_progress_prints_stage_bar(capsys) -> None:
    from scummkit.progress import BuildProgress

    progress = BuildProgress(total=2, enabled=True, width=4)
    progress.start("Extracting PAK assets")
    progress.done("Extracting PAK assets")
    progress.start("Building speech archive")
    progress.done("Building speech archive")

    output = capsys.readouterr().out
    assert "[----] 0/2 Extracting PAK assets..." in output
    assert "[##--] 1/2 Extracting PAK assets done" in output
    assert "[##--] 1/2 Building speech archive..." in output
    assert "[####] 2/2 Building speech archive done" in output


def test_runner_progress_prints_git_style_status(capsys) -> None:
    from scummkit.runner import Runner

    runner = Runner(quiet=True)
    runner.progress("voices encoded as ogg", 4, 10)
    runner.progress("voices encoded as ogg", 10, 10)

    output = capsys.readouterr().out
    assert "\r\033[K  voices encoded as ogg:  40% (4/10)" in output
    assert "\r\033[K  voices encoded as ogg: 100% (10/10), done\n" in output


def test_build_summary_prints_key_fields(capsys) -> None:
    from scummkit.summary import BuildSummary, print_build_summary

    print_build_summary(
        BuildSummary(
            game="MI Test",
            out=Path("/tmp/out"),
            generated_files=[Path("/tmp/out/monkey.sog")],
            speech_archive_entries=2,
            missing_samples=1,
            audio="ogg",
            music="hybrid",
            elapsed_seconds=1.25,
        )
    )

    output = capsys.readouterr().out
    assert "Build summary:" in output
    assert "game: MI Test" in output
    assert "speech archive entries: 2" in output
    assert "missing samples: 1" in output


def test_require_file_error_message_is_actionable(tmp_path: Path) -> None:
    import pytest

    from scummkit.runner import BuildError, require_file

    with pytest.raises(BuildError, match="missing MI1 PAK file"):
        require_file(tmp_path / "missing.pak", "MI1 PAK file")


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
