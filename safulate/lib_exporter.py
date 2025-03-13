from __future__ import annotations
from typing import Callable, Concatenate, TYPE_CHECKING
from .tokens import Token, ContainerToken

from .tokens.function import Function

if TYPE_CHECKING:
    from .executer import Executer


class LibraryExporter:
    def __init__(self, name: str) -> None:
        self.name = name
        self.exports: dict[str, Function | Token] = {}

    def __getitem__(self, key: str) -> Function | Token:
        return self.exports[key]

    def __setitem__(self, key: str, value: Function | Token) -> None:
        self.exports[key] = value

    def export[**P, RT: Token](
        self,
        name: str,
    ) -> Callable[[Callable[Concatenate[Executer, P], RT]], Function[P, RT]]:
        def deco(func: Callable[Concatenate[Executer, P], RT]) -> Function[P, RT]:
            func = Function(func)
            self[name] = func
            return func

        return deco

    __call__ = export

    def to_container(self) -> ContainerToken:
        con = ContainerToken(self.name)
        for name, export in self.exports.items():
            con[name] = export
        return con
