from __future__ import annotations

from ..utils import Enum

__all__ = ("IterableType", "ParamType")


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


class IterableType(Enum):
    list = "["
    tuple = "("
    gen = ""
