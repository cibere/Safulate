import sys

import msgspec

from .cli import CliOptions, parse_cli_args
from .environment import Environment
from .errors import SafulateError
from .interpreter import TreeWalker
from .lexer import Lexer
from .parser import Parser
from .values import NullValue, Value

REPL_GREETING = "\033[34;1mTest v0.0.0\033[0m"

encoder = msgspec.json.Encoder(enc_hook=lambda c: repr(c))


def run_code(source: str, opts: CliOptions, *, env: Environment | None = None) -> Value:
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
        return ast.visit(TreeWalker(env=env))
    except SafulateError as error:
        error.print_report(source)
        raise


def run_file(args: CliOptions) -> None:
    source = args.filename.read_text()
    run_code(source, args)


def repl(args: CliOptions) -> None:
    print(REPL_GREETING)

    env = Environment().add_builtins()

    try:
        while True:
            code = input("\033[34m>>>\033[0m ")
            if code == "quit":
                return

            try:
                value = run_code(code, args, env=env)
                if not isinstance(value, NullValue):
                    print(value)
            except SafulateError:
                continue
    except KeyboardInterrupt:
        print()
    except EOFError:
        print()


def main() -> None:
    args = parse_cli_args()

    try:
        if args.filename:
            run_file(args)
        elif args.code:
            run_code(args.code, args)
        else:
            repl(args)
    except SafulateError:
        if args.python_errors:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
