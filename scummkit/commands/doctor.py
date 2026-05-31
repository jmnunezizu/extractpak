from __future__ import annotations

import argparse
from pathlib import Path

from .. import doctor
from ..runner import BuildError


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("doctor", help="check SCUMMKit dependencies and environment")
    parser.add_argument("--out", type=Path, help="optional output directory write-permission probe")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")


def run(args: argparse.Namespace) -> None:
    checks = doctor.run_checks(args.out)
    if args.json:
        print(doctor.checks_to_json(checks))
    else:
        doctor.print_checks(checks)
    if doctor.exit_code(checks) != 0:
        raise BuildError("doctor checks failed")
