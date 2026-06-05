from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .paths import THIRD_PARTY_UTE


@dataclass(frozen=True)
class BuilderInput:
    path: str
    purpose: str
    required: bool = True


@dataclass(frozen=True)
class PatchDataSource:
    root: Path
    data_dir: Path
    bundled: bool

    @property
    def label(self) -> str:
        return "bundled Ultimate Talkie patch data" if self.bundled else "local Ultimate Talkie builder patch data"

    @property
    def flat_layout(self) -> bool:
        return self.data_dir == self.root


BUILDER_INPUTS: dict[str, tuple[BuilderInput, ...]] = {
    "mi1": (
        BuilderInput("tools/patch10.000", "patch monkey1.000 with Ultimate Talkie SCUMM resource changes"),
        BuilderInput("tools/patch10.001", "patch monkey1.001 with Ultimate Talkie SCUMM resource changes"),
        BuilderInput("tools/monster.tbl", "map speech archive IDs to processed Special Edition samples"),
    ),
    "mi2": (
        BuilderInput("tools/patch02.000", "patch monkey2.000 with Ultimate Talkie SCUMM resource changes"),
        BuilderInput("tools/patch02.001", "patch monkey2.001 with Ultimate Talkie SCUMM resource changes"),
        BuilderInput("tools/monster.tbl", "map speech archive IDs to processed Special Edition samples"),
    ),
}

BUNDLED_INPUTS: dict[str, tuple[BuilderInput, ...]] = {
    "mi1": (
        BuilderInput("patch10.000", "patch monkey1.000 with Ultimate Talkie SCUMM resource changes"),
        BuilderInput("patch10.001", "patch monkey1.001 with Ultimate Talkie SCUMM resource changes"),
        BuilderInput("monster.tbl", "map speech archive IDs to processed Special Edition samples"),
    ),
    "mi2": (
        BuilderInput("patch02.000", "patch monkey2.000 with Ultimate Talkie SCUMM resource changes"),
        BuilderInput("patch02.001", "patch monkey2.001 with Ultimate Talkie SCUMM resource changes"),
        BuilderInput("monster.tbl", "map speech archive IDs to processed Special Edition samples"),
    ),
}


def inputs_for(game: str) -> tuple[BuilderInput, ...]:
    try:
        return BUILDER_INPUTS[game]
    except KeyError as error:
        raise ValueError(f"unsupported builder dependency game: {game}") from error


def bundled_inputs_for(game: str) -> tuple[BuilderInput, ...]:
    try:
        return BUNDLED_INPUTS[game]
    except KeyError as error:
        raise ValueError(f"unsupported bundled patch data game: {game}") from error


def bundled_source(game: str) -> PatchDataSource:
    root = THIRD_PARTY_UTE / game
    return PatchDataSource(root=root, data_dir=root, bundled=True)


def resolve_patch_data_source(game: str, builder: Path | None = None) -> PatchDataSource:
    if builder is None:
        return bundled_source(game)
    root = builder.expanduser()
    tools = root / "tools"
    return PatchDataSource(root=root, data_dir=tools if tools.is_dir() else root, bundled=False)


def format_dependency_report(game: str, builder: Path | None = None) -> str:
    source = resolve_patch_data_source(game, builder)
    inputs = bundled_inputs_for(game) if source.flat_layout else inputs_for(game)
    lines = [f"{game} Ultimate Talkie patch/table data used by SCUMMKit:"]
    for item in inputs:
        suffix = ""
        if builder is not None or source.bundled:
            status = "found" if (source.root / item.path).exists() else "missing"
            suffix = f" [{status}]"
        lines.append(f"- {item.path}: {item.purpose}{suffix}")
    lines.append("")
    if source.bundled:
        lines.append("Bundled patch/table data is included with permission from the original Ultimate Talkie author.")
    else:
        lines.append(
            "The builder folder is used only as a local source for these patch/table files; "
            "no Windows builder executables or batch files are run."
        )
    lines.append("No builder readme or _cdt_silence helper sample is required for this build path.")
    return "\n".join(lines)


def _tool_version(name: str) -> str:
    path = shutil.which(name)
    return path if path else "not found"


def write_build_note(
    *,
    game: str,
    out: Path,
    pak: Path,
    patch_data_source: Path,
    audio: str,
    music: str | None = None,
    extra_options: list[str] | None = None,
) -> Path:
    note = out / "SCUMMKIT-BUILD.txt"
    lines = [
        "SCUMMKit build note",
        "",
        f"created_utc: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}",
        f"game: {game}",
        f"pak: {pak}",
        f"ultimate_talkie_patch_data_source: {patch_data_source}",
        f"audio: {audio}",
    ]
    if music is not None:
        lines.append(f"music: {music}")
    for option in extra_options or []:
        lines.append(option)
    lines.extend(
        [
            "",
            "External tools:",
            f"- bspatch: {_tool_version('bspatch')}",
            f"- sox: {_tool_version('sox')}",
            f"- ffmpeg: {_tool_version('ffmpeg')}",
            f"- vgmstream-cli: {_tool_version('vgmstream-cli')}",
            "",
            format_dependency_report(
                game,
                None if patch_data_source == bundled_source(game).root else patch_data_source,
            ),
            "",
            "Redistribution warning:",
            "This output is generated from local game and patch inputs. Do not redistribute generated game assets.",
            "",
        ]
    )
    note.write_text("\n".join(lines), encoding="utf-8")
    return note
