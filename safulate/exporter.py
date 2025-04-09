from __future__ import annotations

from typing import TYPE_CHECKING, Concatenate

from .values import NativeFunc, ObjectValue, Value

if TYPE_CHECKING:
    from collections.abc import Callable

    from .native_context import NativeContext

__all__ = ("Exporter",)


class Exporter:
    def __init__(self, name: str) -> None:
        self.name = name
        self.exports: dict[str, Value] = {}

    def __getitem__(self, key: str) -> Value:
        return self.exports[key]

    def __setitem__(self, key: str, value: Value) -> None:
        self.exports[key] = value

    def export(
        self,
        name: str,
    ) -> Callable[[Callable[Concatenate[NativeContext, ...], Value]], NativeFunc]:
        def deco(
            callback: Callable[Concatenate[NativeContext, ...], Value],
        ) -> NativeFunc:
            func = NativeFunc(name, callback)
            self[name] = func
            return func

        return deco

    __call__ = export

    def to_container(self) -> ObjectValue:
        return ObjectValue(self.name, self.exports)
