from __future__ import annotations

import shutil
from pathlib import Path

from .runner import BuildError, Runner


def sox_can_write(fmt: str) -> bool:
    if shutil.which("sox") is None:
        return False
    result = __import__("subprocess").run(
        ["sox", "--help-format", fmt],
        stdout=__import__("subprocess").PIPE,
        stderr=__import__("subprocess").DEVNULL,
        text=True,
        check=False,
    )
    return "Writes:" in result.stdout


def require_audio_tools(runner: Runner, audio: str) -> None:
    runner.require_tool("sox", "install SoX; it is required for voice.bat trim/mix/conversion steps")
    if audio == "raw":
        return
    if audio == "ogg":
        if not sox_can_write("ogg") and not runner.has_tool("oggenc") and not runner.has_tool("ffmpeg"):
            raise BuildError("Ogg output requires SoX with Ogg support, oggenc, or ffmpeg")
    elif audio == "flac":
        if not runner.has_tool("flac") and not runner.has_tool("ffmpeg"):
            raise BuildError("FLAC output requires flac or ffmpeg")
    elif audio == "mp3":
        if not runner.has_tool("lame") and not runner.has_tool("ffmpeg"):
            raise BuildError("MP3 output requires lame or ffmpeg")
    else:
        raise BuildError("--audio must be one of: flac, ogg, mp3, raw")


def encode_wav(runner: Runner, wav: Path, destination: Path, audio: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if audio == "raw":
        runner.run(["sox", wav, "-D", "-b", "8", "-c", "1", "-r", "22050", "-t", "wav", "-V0", destination])
    elif audio == "flac":
        if runner.has_tool("flac"):
            runner.run(["flac", "-f", "-s", "-8", "-o", destination, wav])
        else:
            runner.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", wav, "-c:a", "flac", destination])
    elif audio == "ogg":
        if sox_can_write("ogg"):
            runner.run(["sox", wav, "--comment", "", destination])
        elif runner.has_tool("oggenc"):
            runner.run(["oggenc", "-Q", "-o", destination, wav])
        else:
            runner.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", wav, "-c:a", "vorbis", "-q:a", "5", "-strict", "-2", destination])
    elif audio == "mp3":
        if runner.has_tool("lame"):
            runner.run(["lame", "--quiet", wav, destination])
        else:
            runner.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libmp3lame", destination])
    else:
        raise BuildError(f"unsupported audio mode: {audio}")


def count_files(path: Path, pattern: str) -> int:
    return sum(1 for item in path.rglob(pattern) if item.is_file()) if path.exists() else 0


def probe_some(runner: Runner, directory: Path, limit: int = 3) -> None:
    checked = 0
    for path in sorted(p for p in directory.iterdir() if p.is_file()):
        if runner.has_tool("sox"):
            runner.run(["sox", path, "-n", "stat"], stdout=__import__("subprocess").DEVNULL, stderr=__import__("subprocess").DEVNULL)
        elif runner.has_tool("ffmpeg"):
            runner.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-f", "null", "-"], stdout=__import__("subprocess").DEVNULL)
        checked += 1
        if checked >= limit:
            break
    runner.log(f"Probed {checked} processed audio file(s).")
