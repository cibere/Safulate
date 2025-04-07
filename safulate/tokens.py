from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TokenType(Enum):
    ERR = "ERR"
    EOF = "EOF"
    STR = "STR"
    ID = "ID"
    NUM = "NUM"

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

    # keywords
    VAR = "var"
    PRIV = "priv"
    SPEC = "spec"
    FUNC = "func"
    NULL = "null"
    RETURN = "return"
    IF = "if"
    ELSE = "else"
    WHILE = "while"
    BREAK = "break"
    VER = "ver"
    REQ = "req"
    DEL = "del"
    RAISE = "raise"
    FOR = "for"
    CONTAINS = "contains"
    TRY = "try"


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
