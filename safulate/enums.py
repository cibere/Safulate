from __future__ import annotations

from enum import Enum as _Enum


class Enum(_Enum):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class ParamType(Enum):
    vararg = 1
    varkwarg = 2
    arg = 3
    kwarg = 4
    arg_or_kwarg = 5

    def to_arg_type_str(self) -> str:
        return {
            ParamType.kwarg: "keyword ",
            ParamType.arg: "positional ",
        }.get(self, "")


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
    ELLIPSIS = "..."

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
