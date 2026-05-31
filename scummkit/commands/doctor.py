from __future__ import annotations

import argparse
from pathlib import Path

from .. import doctor
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("doctor", help="check SCUMMKit dependencies and environment")
    parser.add_argument("--out", type=Path, help="optional output directory write-permission probe")


def run(args: argparse.Namespace) -> None:
    checks = doctor.run_checks(args.out)
    doctor.print_checks(checks)
    if doctor.exit_code(checks) != 0:
        raise BuildError("doctor checks failed")
