from __future__ import annotations

import importlib
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .paths import EXTRACTPAK


SUPPORTED_PYTHON = (3, 9)

MODULES = [
    "scummkit.audio",
    "scummkit.cli",
    "scummkit.mi1",
    "scummkit.mi1_resources",
    "scummkit.mi1_sbl",
    "scummkit.mi2",
    "scummkit.monster",
    "scummkit.music",
    "scummkit.paths",
    "scummkit.runner",
    "scummkit.sbl",
    "scummkit.voices",
    "scummkit.xwb",
]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _tool_check(name: str) -> DoctorCheck:
    found = shutil.which(name)
    if found:
        return DoctorCheck(name, True, f"found: {found}")
    return DoctorCheck(name, False, "not found")


def _python_check() -> DoctorCheck:
    version = sys.version_info
    current = f"{version.major}.{version.minor}.{version.micro}"
    required = ".".join(str(part) for part in SUPPORTED_PYTHON)
    if version >= SUPPORTED_PYTHON:
        return DoctorCheck("python", True, f"{current} supported")
    return DoctorCheck("python", False, f"{current} unsupported; Python {required}+ is required")


def _extractpak_check() -> DoctorCheck:
    if EXTRACTPAK.is_file() and os.access(EXTRACTPAK, os.X_OK):
        return DoctorCheck("extractpak", True, f"found: {EXTRACTPAK}")
    if EXTRACTPAK.is_file():
        return DoctorCheck(
            "extractpak",
            False,
            f"found but not executable: {EXTRACTPAK}; run `clang extractpak.c -o extractpak`",
        )
    return DoctorCheck(
        "extractpak",
        False,
        f"not found at {EXTRACTPAK}; run `clang extractpak.c -o extractpak`",
    )


def _import_check() -> DoctorCheck:
    failed: list[str] = []
    for module in MODULES:
        try:
            importlib.import_module(module)
        except Exception as error:  # pragma: no cover - detail is important if it happens.
            failed.append(f"{module} ({error})")
    if failed:
        return DoctorCheck("imports", False, "failed: " + "; ".join(failed))
    return DoctorCheck("imports", True, f"{len(MODULES)} modules imported")


def _out_check(out: Path) -> DoctorCheck:
    path = out.expanduser()
    target_dir = path if path.exists() and path.is_dir() else path.parent
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        probe = target_dir / ".scummkit-doctor-write-test"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
    except OSError as error:
        return DoctorCheck("output", False, f"{path} is not writable: {error}")
    return DoctorCheck("output", True, f"writable: {path}")


def run_checks(out: Path | None = None) -> list[DoctorCheck]:
    checks = [
        _python_check(),
        _tool_check("ffmpeg"),
        _tool_check("sox"),
        _tool_check("vgmstream-cli"),
        _extractpak_check(),
        _import_check(),
    ]
    if out is not None:
        checks.append(_out_check(out))
    return checks


def print_checks(checks: list[DoctorCheck]) -> None:
    for check in checks:
        marker = "[ok]" if check.ok else "[fail]"
        print(f"{marker} {check.name} {check.detail}")


def exit_code(checks: list[DoctorCheck]) -> int:
    return 1 if any(check.required and not check.ok for check in checks) else 0
