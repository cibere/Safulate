from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

__all__ = "SoftKeyword", "Token", "TokenType"


class TokenType(Enum):
    ERR = "ERR"
    EOF = "EOF"
    STR = "STR"
    ID = "ID"
    NUM = "NUM"
    VER = "VER"
    FSTR_START = "FSTR_START"
    FSTR_MIDDLE = "FSTR_MIDDLE"
    FSTR_END = "FSTR_END"

    # trisymbols
    STARSTAREQ = "**="

    # bisymbols
    STARSTAR = "**"
    LESSEQ = "<="
    GRTREQ = ">="
    PLUSEQ = "+="
    MINUSEQ = "-="
    STAREQ = "*="
    SLASHEQ = "/="

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
    EQEQ = "=="
    NEQ = "!="
    LESS = "<"
    GRTR = ">"
    SEMI = ";"
    COMMA = ","
    DOT = "."
    TILDE = "~"
    NOT = "!"
    AND = "&"
    OR = "|"
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


class SoftKeyword(Enum):
    ELSE = "else"
    SWITCH = "switch"
    CATCH = "catch"
    AS = "as"
    CASE = "case"
    VAR = "var"
    PRIV = "priv"
    SPEC = "spec"
    FUNC = "func"
    STRUCT = "struct"


@dataclass
class Token:
    type: TokenType
    lexeme: str
    start: int

    def __repr__(self) -> str:
        return (
            f'"<{self.type.name},{repr(self.lexeme).replace('"', '\\"')},{self.start}>"'
        )

    @property
    def value(self) -> Any:
        match self.type:
            case TokenType.STR:
                return self.lexeme[1:-1]
            case TokenType.NUM:
                try:
                    return int(self.lexeme)
                except ValueError:
                    return float(self.lexeme)
            case _:
                raise ValueError(f"Cannot get value of {self.type.name} token")
