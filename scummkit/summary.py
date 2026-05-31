from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildSummary:
    game: str
    out: Path
    generated_files: list[Path]
    speech_archive_entries: int
    missing_samples: int
    audio: str
    music: str | None = None
    elapsed_seconds: float | None = None


def format_elapsed(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    return f"{seconds:.1f}s"


def print_build_summary(summary: BuildSummary) -> None:
    print("")
    print("Build summary:")
    print(f"  game: {summary.game}")
    print(f"  output: {summary.out}")
    print(f"  audio: {summary.audio}")
    if summary.music is not None:
        print(f"  music: {summary.music}")
    print(f"  generated files: {len(summary.generated_files)}")
    for path in summary.generated_files:
        print(f"    {path}")
    print(f"  speech archive entries: {summary.speech_archive_entries}")
    print(f"  missing samples: {summary.missing_samples}")
    print(f"  elapsed: {format_elapsed(summary.elapsed_seconds)}")
