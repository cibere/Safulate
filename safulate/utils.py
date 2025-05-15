from __future__ import annotations

from enum import Enum as _Enum
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")

__all__ = ("Enum", "FallbackDict")


class FallbackDict(dict[KeyT, ValueT], Generic[KeyT, ValueT]):
    def __init__(
        self, initial: dict[KeyT, ValueT], fallback: Callable[[KeyT], ValueT]
    ) -> None:
        super().__init__(initial)

        self.fallback = fallback

    def get(self, key: KeyT) -> ValueT:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.__getitem__(key)

    def __getitem__(self, key: KeyT) -> ValueT:
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.fallback(key)


class Enum(_Enum):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"
