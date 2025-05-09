from __future__ import annotations

from enum import Enum as _Enum
from typing import cast

__all__ = (
    "AttrSpec",
    "BinarySpec",
    "CallSpec",
    "FormatSpec",
    "ParamType",
    "SoftKeyword",
    "SpecName",
    "TokenType",
    "UnarySpec",
    "spec_name_from_str",
)


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
    IN = "in"

    def __repr__(self) -> str:
        return repr(super().__repr__())


class BinarySpec(Enum):
    add = TokenType.PLUS
    sub = TokenType.MINUS
    mul = TokenType.STAR
    pow = TokenType.STARSTAR
    div = TokenType.SLASH
    eq = TokenType.EQEQ
    neq = TokenType.NEQ
    less = TokenType.LESS
    grtr = TokenType.GRTR
    lesseq = TokenType.LESSEQ
    grtreq = TokenType.GRTREQ
    amp = TokenType.AMP
    pipe = TokenType.PIPE
    has_item = TokenType.HAS


class UnarySpec(Enum):
    uadd = TokenType.PLUS
    neg = TokenType.MINUS
    bool = TokenType.BOOL


class CallSpec(Enum):
    call = TokenType.LPAR
    altcall = TokenType.LSQB
    get_attr = TokenType.DOT
    iter = 0
    next = 1
    format = 2
    get = 3


class FormatSpec(Enum):
    repr = "r"
    str = "s"
    hash = "h"


class AttrSpec(Enum):
    type = 4


SpecName = BinarySpec | UnarySpec | CallSpec | FormatSpec | AttrSpec

__spec_name_mapping: dict[str, SpecName] = {
    spec.name: spec
    for EnumSpec in cast("tuple[type[SpecName]]", getattr(SpecName, "__args__"))
    for spec in EnumSpec
}


def spec_name_from_str(name: str) -> SpecName:
    spec = __spec_name_mapping.get(name)
    if spec:
        return spec

    raise ValueError(f"Unknown spec name {name!r}")
