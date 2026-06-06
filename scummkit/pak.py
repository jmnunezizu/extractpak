from __future__ import annotations

import os
from pathlib import Path

from .paths import EXTRACTPAK
from .runner import BuildError, Runner


def _extractpak_path(extractpak: Path | None) -> Path:
    return EXTRACTPAK if extractpak is None else extractpak


def require_extractpak(extractpak: Path | None = None) -> None:
    path = _extractpak_path(extractpak)
    if not path.is_file():
        raise BuildError(
            f"missing compiled extractpak helper: {path}; "
            "run `clang extractpak.c -o extractpak`"
        )
    if not os.access(path, os.X_OK):
        raise BuildError(
            f"compiled extractpak helper is not executable: {path}; "
            "run `clang extractpak.c -o extractpak`"
        )


def extract_only(
    runner: Runner,
    *,
    pak: Path,
    prefix: str,
    out: Path,
    extractpak: Path | None = None,
) -> None:
    path = _extractpak_path(extractpak)
    require_extractpak(path)
    try:
        runner.run([path, "--only", prefix, pak, out])
    except BuildError as error:
        raise BuildError(
            f"failed to extract {prefix!r} from PAK {pak} into {out}: {error}"
        ) from error


def extract_classic_en(
    runner: Runner,
    *,
    pak: Path,
    out: Path,
    extractpak: Path | None = None,
) -> None:
    extract_only(runner, pak=pak, prefix="classic/en", out=out, extractpak=extractpak)
