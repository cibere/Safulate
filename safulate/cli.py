from __future__ import annotations

import argparse
from pathlib import Path


class CliOptions:
    filename: Path
    code: str
    lex: bool
    ast: bool
    python_errors: bool


parser = argparse.ArgumentParser("test")
code_group = parser.add_mutually_exclusive_group()
code_group.add_argument("filename", type=Path, nargs="?")
code_group.add_argument("-c", "--code", nargs="?")

level_group = parser.add_mutually_exclusive_group()
level_group.add_argument("--lex", action="store_true")
level_group.add_argument("--ast", action="store_true")

parser.add_argument("-pyers", "--python-errors", action="store_true")


def parse_cli_args() -> CliOptions:
    return parser.parse_args()  # pyright: ignore[reportReturnType]
