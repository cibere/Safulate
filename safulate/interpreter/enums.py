from __future__ import annotations

from typing import cast

from ..lexer import TokenType
from ..utils import Enum

__all__ = (
    "AttrSpec",
    "BinarySpec",
    "CallSpec",
    "FormatSpec",
    "SpecName",
    "UnarySpec",
    "spec_name_from_str",
)


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
    init = 4


class FormatSpec(Enum):
    repr = "r"
    str = "s"
    hash = "h"


class AttrSpec(Enum):
    type = 4
    parent = 5


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
