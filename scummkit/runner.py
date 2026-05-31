from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


class BuildError(RuntimeError):
    pass


@dataclass
class Runner:
    dry_run: bool = False
    verbose: bool = False
    quiet: bool = False
    _inline_status: bool = field(default=False, init=False)

    def log(self, message: str = "") -> None:
        if self.quiet:
            return
        print(message)

    def status(self, message: str = "", inline: bool = False, done: bool = False) -> None:
        if inline:
            print(f"\r\033[K{message}", end="\n" if done else "", flush=True)
            self._inline_status = not done
            return
        if self._inline_status:
            print()
            self._inline_status = False
        print(message)

    def require_tool(self, name: str, hint: str) -> None:
        if shutil.which(name) is None:
            raise BuildError(f"missing required tool '{name}': {hint}")

    def has_tool(self, name: str) -> bool:
        return shutil.which(name) is not None

    def run(self, args: Iterable[str | Path], **kwargs) -> subprocess.CompletedProcess:
        command = [str(arg) for arg in args]
        if self.dry_run:
            self.log("[dry-run] " + " ".join(command))
            return subprocess.CompletedProcess(command, 0)
        if self.verbose:
            self.log("+ " + " ".join(command))
        if self.quiet:
            kwargs.setdefault("stdout", subprocess.DEVNULL)
            kwargs.setdefault("stderr", subprocess.DEVNULL)
        try:
            return subprocess.run(command, check=True, **kwargs)
        except FileNotFoundError as error:
            raise BuildError(
                f"command not found: {command[0]}; install it and ensure it is on PATH"
            ) from error
        except subprocess.CalledProcessError as error:
            raise BuildError(f"command failed ({error.returncode}): {' '.join(command)}") from error

    def clean_dir(self, path: Path) -> None:
        if str(path) in ("", "/", "."):
            raise BuildError(f"refusing to use unsafe output directory: {path}")
        if self.dry_run:
            self.log(f"[dry-run] rm -rf {path}")
            self.log(f"[dry-run] mkdir -p {path}")
            return
        try:
            shutil.rmtree(path, ignore_errors=True)
            path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise BuildError(f"cannot prepare output directory {path}: {error}") from error


def require_file(path: Path, description: str | None = None) -> None:
    if not path.is_file():
        label = f"{description}: " if description else ""
        raise BuildError(f"missing {label}{path}")


def require_dir(path: Path, description: str | None = None) -> None:
    if not path.is_dir():
        label = f"{description}: " if description else "directory: "
        raise BuildError(f"missing {label}{path}")
