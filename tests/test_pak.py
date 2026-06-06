from pathlib import Path

import pytest

from scummkit import pak
from scummkit.runner import BuildError, Runner


def test_extract_classic_en_invokes_extractpak(tmp_path: Path) -> None:
    extractpak = tmp_path / "extractpak"
    source = tmp_path / "Monkey1.pak"
    out = tmp_path / "out"
    extractpak.write_text("#!/bin/sh\n", encoding="utf-8")
    extractpak.chmod(0o755)
    source.write_bytes(b"pak")
    commands = []
    runner = Runner(dry_run=True)
    runner.log = lambda message="": commands.append(message)

    pak.extract_classic_en(runner, pak=source, out=out, extractpak=extractpak)

    assert commands == [f"[dry-run] {extractpak} --only classic/en {source} {out}"]


def test_require_extractpak_reports_compile_hint_when_missing(tmp_path: Path) -> None:
    with pytest.raises(BuildError, match="clang extractpak.c -o extractpak"):
        pak.require_extractpak(tmp_path / "extractpak")


def test_extract_only_adds_pak_context_to_failures(tmp_path: Path) -> None:
    extractpak = tmp_path / "extractpak"
    source = tmp_path / "Monkey1.pak"
    out = tmp_path / "out"
    extractpak.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    extractpak.chmod(0o755)
    source.write_bytes(b"pak")

    with pytest.raises(BuildError, match="failed to extract 'classic/en' from PAK"):
        pak.extract_classic_en(Runner(), pak=source, out=out, extractpak=extractpak)
