from __future__ import annotations

from enum import Enum as _Enum
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar, cast, overload

__all__ = (
    "AttrSpec",
    "BinarySpec",
    "CallSpec",
    "EnumAnd",
    "EnumOr",
    "FormatSpec",
    "ParamType",
    "SequenceConst",
    "SoftKeyword",
    "SpecName",
    "TokenType",
    "UnarySpec",
    "spec_name_from_str",
)

if TYPE_CHECKING:
    EnumT = TypeVar("EnumT", bound="Enum")
    EnumAndT = TypeVar("EnumAndT", bound="Enum" | "EnumAnd[Any]" | "EnumOr[Any]")
    EnumOrT = TypeVar("EnumOrT", bound="Enum" | "EnumAnd[Any]" | "EnumOr[Any]")
else:
    EnumT = TypeVar("EnumT")
    EnumAndT = TypeVar("EnumAndT")
    EnumOrT = TypeVar("EnumOrT")


class Enum(_Enum):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

    def __or__(
        self, other: EnumT | EnumOr[EnumT] | EnumAnd[EnumT]
    ) -> EnumOr[Self | EnumT]:
        return EnumOr(self, *other.value if isinstance(other, EnumOr) else (other,))

    def __and__(
        self, other: EnumT | EnumOr[EnumT] | EnumAnd[EnumT]
    ) -> EnumAnd[Self | EnumT]:
        return EnumAnd(self, *other.value if isinstance(other, EnumOr) else (other,))


class EnumAnd(Generic[EnumAndT]):
    def __init__(self, *vals: EnumAndT) -> None:
        self.__val: tuple[EnumAndT, ...] = vals

    # def __repr__(self) -> str:
    #     return f"{self.__class__.__name__}(value={self.value!r})"

    def __repr__(self) -> str:
        return f"({' & '.join(repr(child) for child in self.value)})"

    @property
    def value(self) -> tuple[EnumAndT, ...]:
        return self.__val

    @overload
    def __or__(self, other: EnumT) -> EnumOr[EnumAndT | EnumT]: ...
    @overload
    def __or__(self, other: EnumOr[EnumT]) -> EnumOr[Self | EnumOr[EnumT]]: ...
    @overload
    def __or__(self, other: EnumAnd[EnumT]) -> EnumOr[Self | EnumAnd[EnumT]]: ...
    def __or__(
        self, other: EnumT | EnumOr[EnumT] | EnumAnd[EnumT]
    ) -> (
        EnumOr[EnumAndT | EnumT]
        | EnumOr[Self | EnumOr[EnumT]]
        | EnumOr[Self | EnumAnd[EnumT]]
    ):
        if isinstance(other, Enum):
            return EnumOr(*self.value, other)
        else:
            return EnumOr(self, other)

    @overload
    def __and__(self, other: EnumT) -> EnumAnd[EnumAndT | EnumT]: ...
    @overload
    def __and__(self, other: EnumOr[EnumT]) -> EnumAnd[Self | EnumOr[EnumT]]: ...
    @overload
    def __and__(self, other: EnumAnd[EnumT]) -> EnumAnd[Self | EnumAnd[EnumT]]: ...
    def __and__(
        self, other: EnumT | EnumOr[EnumT] | EnumAnd[EnumT]
    ) -> (
        EnumAnd[EnumAndT | EnumT]
        | EnumAnd[Self | EnumOr[EnumT]]
        | EnumAnd[Self | EnumAnd[EnumT]]
    ):
        if isinstance(other, Enum):
            return EnumAnd(*self.value, other)
        else:
            return EnumAnd(self, other)


class EnumOr(Generic[EnumOrT]):
    def __init__(self, *vals: EnumOrT) -> None:
        self.__val: tuple[EnumOrT, ...] = vals

    # def __repr__(self) -> str:
    #     return f"{self.__class__.__name__}(value={self.value!r})"

    def __repr__(self) -> str:
        return f"({' | '.join(repr(child) for child in self.value)})"

    @property
    def value(self) -> tuple[EnumOrT, ...]:
        return self.__val

    @overload
    def __or__(self, other: EnumT) -> EnumOr[EnumOrT | EnumT]: ...
    @overload
    def __or__(self, other: EnumOr[EnumT]) -> EnumOr[Self | EnumOr[EnumT]]: ...
    @overload
    def __or__(self, other: EnumAnd[EnumT]) -> EnumOr[Self | EnumAnd[EnumT]]: ...
    def __or__(
        self, other: EnumT | EnumOr[EnumT] | EnumAnd[EnumT]
    ) -> (
        EnumOr[EnumOrT | EnumT]
        | EnumOr[Self | EnumOr[EnumT]]
        | EnumOr[Self | EnumAnd[EnumT]]
    ):
        if isinstance(other, Enum):
            return EnumOr(*self.value, other)
        else:
            return EnumOr(self, other)

    @overload
    def __and__(self, other: EnumT) -> EnumAnd[EnumOrT | EnumT]: ...
    @overload
    def __and__(self, other: EnumOr[EnumT]) -> EnumAnd[Self | EnumOr[EnumT]]: ...
    @overload
    def __and__(self, other: EnumAnd[EnumT]) -> EnumAnd[Self | EnumAnd[EnumT]]: ...
    def __and__(
        self, other: EnumT | EnumOr[EnumT] | EnumAnd[EnumT]
    ) -> (
        EnumAnd[EnumOrT | EnumT]
        | EnumAnd[Self | EnumOr[EnumT]]
        | EnumAnd[Self | EnumAnd[EnumT]]
    ):
        if isinstance(other, Enum):
            return EnumAnd(*self.value, other)
        else:
            return EnumAnd(self, other)


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


class SequenceConst(Enum):
    any = "any"
    none = "none"
