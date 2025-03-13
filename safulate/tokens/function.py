from __future__ import annotations
from typing import Callable, Concatenate, TYPE_CHECKING, Self
from inspect import signature
from copy import copy
from .mixins import AttrsMixin, BuiltinMethodsMixin

if TYPE_CHECKING:
    from ..executer import Executer
    from . import Token, ArgToken

MISSING = object()


class Function[**P, RT: Token](AttrsMixin, BuiltinMethodsMixin):
    value = None

    def __init__(
        self,
        func: Callable[Concatenate[Executer, P], RT],
        *,
        args: list[ArgToken] | None = None,
    ) -> None:
        self.func = func
        self._args = args

    def copy(self) -> Self:
        return copy(self)

    @property
    def args(self) -> list[ArgToken]:
        return self._args or self.get_args()

    def __call__(self, exe: Executer, *raw_args: P.args, **kwargs: P.kwargs) -> RT:
        args = (exe, *raw_args)
        # print(f"Calling {self.func!r} with {args=} and {kwargs=}")
        return self.func(*args, **kwargs)  # pyright: ignore[reportArgumentType,reportCallIssue]

    def get_args(self) -> list[ArgToken]:
        from . import ArgToken  # circular import

        return [
            ArgToken(required=param.default == param.empty, value=param.name)
            for param in list(signature(self.func).parameters.values())[1:]
        ]

    def __repr__(self) -> str:
        return f"<Function {self.func!r}>"
