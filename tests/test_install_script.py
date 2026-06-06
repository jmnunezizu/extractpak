from pathlib import Path
import json
import os
import subprocess


ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = ROOT / "install.sh"
TEST_INSTALL_SH = ROOT / "scripts" / "test-install.sh"
RELEASE_SH = ROOT / "scripts" / "release.sh"
RELEASE_PLEASE_CONFIG = ROOT / "release-please-config.json"
RELEASE_PLEASE_MANIFEST = ROOT / ".release-please-manifest.json"
RELEASE_PLEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release-please.yml"
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_INIT = ROOT / "scummkit" / "__init__.py"


def _pyproject_version() -> str:
    for line in PYPROJECT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise AssertionError("missing pyproject.toml project version")


def test_install_script_is_valid_posix_shell() -> None:
    subprocess.run(["sh", "-n", str(INSTALL_SH)], check=True)


def test_install_smoke_script_is_valid_posix_shell() -> None:
    subprocess.run(["sh", "-n", str(TEST_INSTALL_SH)], check=True)


def test_release_script_is_valid_posix_shell() -> None:
    subprocess.run(["sh", "-n", str(RELEASE_SH)], check=True)


def test_install_script_defaults_to_next_release() -> None:
    text = INSTALL_SH.read_text(encoding="utf-8")

    assert "VERSION=${SCUMMKIT_VERSION:-latest}" in text
    assert "resolve_latest_version" in text
    assert "SCUMMKIT_HOME" in text
    assert "SCUMMKIT_BIN_DIR" in text
    assert "SCUMMKIT_ARCHIVE_URL" in text
    assert "SCUMMKIT_NO_PATH_UPDATE" in text
    assert 'cd "$INSTALL_DIR"' in text
    assert "PYTHONPATH" in text
    assert "ensure_bin_on_path" in text
    assert "SCUMMKit installer" in text


def test_install_script_help() -> None:
    result = subprocess.run(
        ["sh", str(INSTALL_SH), "--help"],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Usage: install.sh" in result.stdout
    assert "SCUMMKIT_VERSION" in result.stdout
    assert "does not install system dependencies" in result.stdout


def test_install_script_dry_run_with_archive_override(tmp_path: Path) -> None:
    archive = tmp_path / "scummkit.tar.gz"
    archive.write_bytes(b"not used in dry run")
    result = subprocess.run(
        [
            "sh",
            str(INSTALL_SH),
            "--dry-run",
        ],
        check=True,
        text=True,
        capture_output=True,
        env={
            "HOME": str(tmp_path),
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
            "SCUMMKIT_ARCHIVE_URL": f"file://{archive}",
            "SCUMMKIT_VERSION": "v0.3.0",
        },
    )

    assert "SCUMMKit install plan:" in result.stdout
    assert "version:      v0.3.0" in result.stdout
    assert "No files were changed." in result.stdout


def test_install_script_updates_shell_profile_when_bin_dir_not_on_path(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-root"
    archive = tmp_path / "scummkit.tar.gz"
    home = tmp_path / "home"
    install_home = tmp_path / "install"
    bin_dir = tmp_path / "bin"
    archive_root.mkdir()
    (archive_root / "README.md").write_text("test archive\n", encoding="utf-8")
    (archive_root / "pyproject.toml").write_text("[project]\nname='scummkit'\n", encoding="utf-8")
    (archive_root / "extractpak.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    package = archive_root / "scummkit"
    package.mkdir()
    (package / "__init__.py").write_text("__version__ = '0.3.1'\n", encoding="utf-8")
    (package / "__main__.py").write_text(
        "import sys\nprint('doctor ok' if sys.argv[1:] == ['doctor'] else 'scummkit 0.3.1')\n",
        encoding="utf-8",
    )
    subprocess.run(["tar", "-czf", str(archive), "-C", str(archive_root), "."], check=True)

    result = subprocess.run(
        ["sh", str(INSTALL_SH)],
        check=True,
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
            "SHELL": "/bin/zsh",
            "SCUMMKIT_ARCHIVE_URL": f"file://{archive}",
            "SCUMMKIT_HOME": str(install_home),
            "SCUMMKIT_BIN_DIR": str(bin_dir),
            "SCUMMKIT_VERSION": "v0.3.1",
            "PYTHON": "python3",
        },
    )

    zshrc = home / ".zshrc"
    assert zshrc.read_text(encoding="utf-8") == (
        "\n"
        "# SCUMMKit installer\n"
        f'export PATH="{bin_dir}:$PATH"\n'
    )
    assert "Added SCUMMKit to PATH for future shells" in result.stdout
    assert f'export PATH="{bin_dir}:$PATH"' in result.stdout


def test_release_please_manifest_tracks_project_version() -> None:
    config = json.loads(RELEASE_PLEASE_CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(RELEASE_PLEASE_MANIFEST.read_text(encoding="utf-8"))
    version = _pyproject_version()

    package = config["packages"]["."]
    assert package["release-type"] == "python"
    assert package["package-name"] == "scummkit"
    assert "scummkit/__init__.py" in package["extra-files"]
    assert manifest["."] == version
    assert f'__version__ = "{version}"' in PACKAGE_INIT.read_text(encoding="utf-8")


def test_release_please_workflow_uploads_installer_asset() -> None:
    text = RELEASE_PLEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "googleapis/release-please-action@v4" in text
    assert "release-please-config.json" in text
    assert ".release-please-manifest.json" in text
    assert "gh release upload" in text
    assert "install.sh --clobber" in text
