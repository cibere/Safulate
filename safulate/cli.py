from __future__ import annotations

import argparse
from pathlib import Path


class Options:
    def __init__(
        self,
        lex: bool,
        ast: bool,
        python_errors: bool,
    ) -> None:
        self.lex = lex
        self.ast = ast
        self.python_errors = python_errors

    @classmethod
    def default(cls) -> Options:
        return cls(lex=False, ast=False, python_errors=False)


parser = argparse.ArgumentParser("test")
code_group = parser.add_mutually_exclusive_group()
code_group.add_argument("filename", type=Path, nargs="?")
code_group.add_argument("-c", "--code", nargs="?")

level_group = parser.add_mutually_exclusive_group()
level_group.add_argument("--lex", action="store_true")
level_group.add_argument("--ast", action="store_true")

parser.add_argument("-pyers", "--python-errors", action="store_true")


def parse_cli_args() -> tuple[str | Path | None, Options]:
    args = parser.parse_args()
    source = None
    if args.filename:
        source = args.filename
    elif args.code:
        source = args.code
    return (
        source,
        Options(lex=args.lex, ast=args.ast, python_errors=args.python_errors),
    )
