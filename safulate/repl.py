from pathlib import Path

import msgspec

from .asts import ASTNode
from .cli import Options
from .environment import Environment
from .errors import SafulateError
from .interpreter import TreeWalker
from .lexer import Lexer
from .objects import SafBaseObject, SafNull
from .parser import Parser
from .tokens import Token, TokenType

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
    source: str,
    *,
    opts: Options | None = None,
    interpreter: TreeWalker | None = None,
    filename: str | None = None,
) -> SafBaseObject:
    try:
        return code_to_ast(source, opts=opts).visit(interpreter or TreeWalker())
    except SafulateError as error:
        error.print_report(source, filename=filename)
        raise


def run_file(path: Path, *, opts: Options | None = None) -> None:
    source = path.read_text()
    run_code(source, opts=opts, filename=path.absolute().as_posix())


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
                if not isinstance(value, SafNull):
                    print(value.str_spec(interpreter.ctx(Token(TokenType.EOF, "", -1))))
            except SafulateError:
                continue
    except KeyboardInterrupt:
        print()
    except EOFError:
        print()
