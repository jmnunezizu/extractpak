from __future__ import annotations

import argparse

from .. import mi1_resources


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    mi1_resources.add_inspect_parser(sub, handler=run)


def run(args: argparse.Namespace) -> None:
    mi1_resources.run_inspect(args)
