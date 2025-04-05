import sys

import msgspec

from .cli import CliOptions, parse_cli_args
from .errors import SafulateError
from .interpreter import TreeWalker
from .lexer import Lexer
from .parser import Parser
from .values import NullValue, Value

REPL_GREETING = "\033[34;1mTest v0.0.0\033[0m"

encoder = msgspec.json.Encoder(enc_hook=lambda c: repr(c))


def run_code(source: str, opts: CliOptions) -> Value:
    lexer = Lexer(source)
    parser = Parser()

    try:
        tokens = lexer.tokenize()
        if opts.lex:
            print(msgspec.json.format(encoder.encode(tokens)).decode())
            quit(1)
        ast = parser.parse(tokens)
        if opts.ast:
            print(ast)
            quit(1)
        return ast.accept(TreeWalker())
    except SafulateError as error:
        error.print_report(source)
        raise


def run_file(args: CliOptions) -> None:
    source = args.filename.read_text()
    run_code(source, args)


def repl() -> None:
    print(REPL_GREETING)

    try:
        while True:
            code = input("\033[34m>>>\033[0m ")
            try:
                value = run_code(code, args)
                if not isinstance(value, NullValue):
                    print(value)
            except SafulateError:
                continue
    except KeyboardInterrupt:
        print()
    except EOFError:
        print()


if __name__ == "__main__":
    args = parse_cli_args()

    try:
        if args.filename:
            run_file(args)
        elif args.code:
            run_code(args.code, args)
        else:
            repl()
    except SafulateError:
        if args.python_errors:
            raise
        sys.exit(1)

    # run("18/2+1**2;")
    # run("18/(2+1)**;")
    # run("1+null;")
    # run_file("test.test")
