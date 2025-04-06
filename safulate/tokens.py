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
    LPAR = "LPAR"
    RPAR = "RPAR"
    LSQB = "LSQB"
    RSQB = "RSQB"
    LBRC = "LBRC"
    RBRC = "RBRC"
    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    STARSTAR = "STARSTAR"
    SLASH = "SLASH"
    EQ = "EQ"
    EQEQ = "EQEQ"
    NEQ = "NEQ"
    LESS = "LESS"
    GRTR = "GRTR"
    LESSEQ = "LESSEQ"
    GRTREQ = "GRTREQ"
    SEMI = "SEMI"
    PLUSEQ = "PLUSEQ"
    MINUSEQ = "MINUSEQ"
    STAREQ = "STAREQ"
    STARSTAREQ = "STARSTAREQ"
    SLASHEQ = "SLASHEQ"
    COMMA = "COMMA"
    VAR = "VAR"
    PRIV = "PRIV"
    SPEC = "SPEC"
    FUNC = "FUNC"
    NULL = "NULL"
    RETURN = "RETURN"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    BREAK = "BREAK"
    DOT = "DOT"
    TILDE = "TILDE"
    VER = "VER"
    REQ = "REQ"
    AT = "AT"
    RAISE = "RAISE"
    FOR = "FOR"
    IN = "in"
    NOT = "NOT"
    DEL = "DEL"
    AND = "AND"
    OR = "OR"


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
