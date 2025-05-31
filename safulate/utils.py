from __future__ import annotations

from enum import Enum as _Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

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

    @classmethod
    def all_values(cls) -> Iterable[Any]:
        return cls._value2member_map_.keys()


class LazyImport:
    def __init__(self, *parts: str) -> None:
        self.__parts = parts

    def __getattr__(self, name: str) -> Any:
        parts = list(self.__parts)
        mod = __import__(parts.pop(0))

        while parts:
            mod = getattr(mod, parts.pop(0))

        def patched_getattribute(name: str) -> Any:
            return getattr(mod, name)

        self.__getattribute__ = patched_getattribute
        return patched_getattribute(name)
