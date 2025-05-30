from pathlib import Path

import msgspec

from ..cli import Options
from ..errors import SafulateError
from ..lexer import Lexer, Token, TokenType
from ..parser import ASTNode, Parser
from .interpreter import Interpreter
from .objects import SafBaseObject, SafNull

REPL_GREETING = "\033[34;1mTest v0.0.0\033[0m"

encoder = msgspec.json.Encoder(enc_hook=lambda c: repr(c))

__all__ = "code_to_ast", "run_code", "run_file"


def code_to_ast(
    source: str,
    *,
    opts: Options | None = None,
) -> ASTNode:
    opts = opts or Options.default()

    tokens = Lexer(source).tokenize()
    if opts.lex:
        print(msgspec.json.format(encoder.encode(tokens)).decode())
        quit(1)

    ast = Parser(tokens).program()
    if opts.ast:
        print(ast)
        quit(1)

    return ast


def run_code(
    source: str,
    *,
    interpreter: Interpreter,
    opts: Options | None = None,
) -> SafBaseObject:
    try:
        return code_to_ast(source, opts=opts).visit(interpreter)
    except SafulateError as error:
        error.print_report(source, filename=interpreter.module_obj.name)
        raise


def run_file(path: Path, *, opts: Options | None = None) -> None:
    source = path.read_text()
    run_code(source, opts=opts, interpreter=Interpreter(path.absolute().as_posix()))


def start_repl_session(opts: Options) -> None:
    print(REPL_GREETING)
    interpreter = Interpreter("<repl session>")

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
