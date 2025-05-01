from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = "SoftKeyword", "Token", "TokenType"


class TokenType(Enum):
    ERR = "ERR"
    EOF = "EOF"
    STR = "STR"
    ID = "ID"
    PRIV_ID = "PRIV_ID"
    NUM = "NUM"
    FSTR_START = "FSTR_START"
    FSTR_MIDDLE = "FSTR_MIDDLE"
    FSTR_END = "FSTR_END"
    RSTRING = "RSTRING"

    # trisymbols
    STARSTAREQ = "**="
    EQEQEQ = "==="

    # bisymbols
    STARSTAR = "**"
    LESSEQ = "<="
    GRTREQ = ">="
    PLUSEQ = "+="
    MINUSEQ = "-="
    STAREQ = "*="
    SLASHEQ = "/="
    BOOL = "!!"
    AND = "&&"
    OR = "||"
    EQEQ = "=="
    NEQ = "!="

    # monosymbols
    LPAR = "("
    RPAR = ")"
    LSQB = "["
    RSQB = "]"
    LBRC = "{"
    RBRC = "}"
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    EQ = "="
    LESS = "<"
    GRTR = ">"
    SEMI = ";"
    COMMA = ","
    DOT = "."
    TILDE = "~"
    NOT = "!"
    PIPE = "|"
    AMP = "&"
    AT = "@"
    COLON = ":"

    # hard keywords

    RETURN = "return"
    IF = "if"
    REQ = "req"
    WHILE = "while"
    BREAK = "break"
    DEL = "del"
    RAISE = "raise"
    FOR = "for"
    TRY = "try"
    HAS = "has"
    CONTINUE = "continue"
    PUB = "pub"
    PRIV = "priv"
    TYPE = "type"


class SoftKeyword(Enum):
    ELSE = "else"
    SWITCH = "switch"
    CATCH = "catch"
    AS = "as"
    CASE = "case"
    SPEC = "spec"
    STRUCT = "struct"
    PROP = "prop"

    def __repr__(self) -> str:
        return repr(super().__repr__())


@dataclass
class Token:
    type: TokenType
    lexeme: str
    start: int

    def __repr__(self) -> str:
        mid = repr(self.lexeme).replace('"', '\\"')
        return f'"<{self.type.name},{mid},{self.start}>"'

    @classmethod
    def mock(
        cls,
        token_type: TokenType,
        /,
        *,
        lexme: str | None = None,
        start: int | None = None,
    ) -> Token:
        return Token(
            type=token_type,
            lexeme=token_type.value if lexme is None else lexme,
            start=-1 if start is None else start,
        )
