from pathlib import Path

import msgspec

from .asts import ASTNode
from .cli import Options
from .environment import Environment
from .errors import SafulateError
from .interpreter import TreeWalker
from .lexer import Lexer
from .parser import Parser
from .tokens import Token, TokenType
from .values import NullValue, Value

REPL_GREETING = "\033[34;1mTest v0.0.0\033[0m"

encoder = msgspec.json.Encoder(enc_hook=lambda c: repr(c))

__all__ = "code_to_ast", "run_code", "run_file"


def code_to_ast(
    source: str,
    *,
    opts: Options | None = None,
) -> ASTNode:
    lexer = Lexer(source)
    parser = Parser()
    opts = opts or Options.default()

    tokens = lexer.tokenize()
    if opts.lex:
        print(msgspec.json.format(encoder.encode(tokens)).decode())
        quit(1)
    ast = parser.parse(tokens)
    if opts.ast:
        print(ast)
        quit(1)
    return ast


def run_code(
    source: str, *, opts: Options | None = None, interpreter: TreeWalker | None = None
) -> Value:
    try:
        return code_to_ast(source, opts=opts).visit(interpreter or TreeWalker())
    except SafulateError as error:
        error.print_report(source)
        raise


def run_file(filename: Path, *, opts: Options | None = None) -> None:
    source = filename.read_text()
    run_code(source, opts=opts)


def start_repl_session(opts: Options) -> None:
    print(REPL_GREETING)

    env = Environment().add_builtins()
    interpreter = TreeWalker(env=env)

    try:
        while True:
            code = input("\033[34m>>>\033[0m ")
            if code == "quit":
                return

            try:
                value = run_code(code, opts=opts, interpreter=interpreter)
                if not isinstance(value, NullValue):
                    print(value.str_spec(interpreter.ctx(Token(TokenType.EOF, "", -1))))
            except SafulateError:
                continue
    except KeyboardInterrupt:
        print()
    except EOFError:
        print()
