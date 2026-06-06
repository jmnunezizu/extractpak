from pathlib import Path
import json
import subprocess


ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = ROOT / "install.sh"
TEST_INSTALL_SH = ROOT / "scripts" / "test-install.sh"
RELEASE_SH = ROOT / "scripts" / "release.sh"
RELEASE_PLEASE_CONFIG = ROOT / "release-please-config.json"
RELEASE_PLEASE_MANIFEST = ROOT / ".release-please-manifest.json"
RELEASE_PLEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release-please.yml"


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
    assert 'cd "$INSTALL_DIR"' in text
    assert "PYTHONPATH" in text


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


def test_release_please_manifest_tracks_project_version() -> None:
    config = json.loads(RELEASE_PLEASE_CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(RELEASE_PLEASE_MANIFEST.read_text(encoding="utf-8"))

    package = config["packages"]["."]
    assert package["release-type"] == "python"
    assert package["package-name"] == "scummkit"
    assert "scummkit/__init__.py" in package["extra-files"]
    assert manifest["."] == "0.3.0"


def test_release_please_workflow_uploads_installer_asset() -> None:
    text = RELEASE_PLEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "googleapis/release-please-action@v4" in text
    assert "release-please-config.json" in text
    assert ".release-please-manifest.json" in text
    assert "gh release upload" in text
    assert "install.sh --clobber" in text
