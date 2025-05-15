import sys
from pathlib import Path

from .cli import parse_cli_args
from .errors import SafulateError
from .interpreter.interpreter import Interpreter
from .interpreter.repl import run_code, run_file, start_repl_session


def main() -> None:
    src, opts = parse_cli_args()

    try:
        match src:
            case Path():
                run_file(src, opts=opts)
            case str():
                run_code(src, opts=opts, interpreter=Interpreter("<cli session>"))
            case _:
                start_repl_session(opts)
    except SafulateError:
        if opts.python_errors:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
