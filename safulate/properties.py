"""
This code is originally from discord.py by Rapptz/Danny
https://github.com/Rapptz/discord.py/blob/master/discord/utils.py

Original License:

The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar, overload

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)

__all__ = (
    "CachedSlotProperty",
    "CachedProperty",
    "ClassProperty",
    "cached_property",
    "class_property",
)


class CachedProperty(Generic[T, T_co]):
    def __init__(self, function: Callable[[T], T_co]) -> None:
        self.function = function
        self.__doc__ = getattr(function, "__doc__")

    @overload
    def __get__(self, instance: T, owner: type[T]) -> T_co: ...

    @overload
    def __get__(self, instance: None, owner: type[T]) -> CachedProperty[T, T_co]: ...

    def __get__(
        self, instance: T | None, owner: type[T]
    ) -> T_co | CachedProperty[T, T_co]:
        if instance is None:
            return self

        value = self.function(instance)
        setattr(instance, self.function.__name__, value)

        return value


class CachedSlotProperty(Generic[T, T_co]):
    def __init__(self, name: str, function: Callable[[T], T_co]) -> None:
        self.name = name
        self.function = function
        self.__doc__ = getattr(function, "__doc__")

    @overload
    def __get__(
        self, instance: None, owner: type[T]
    ) -> CachedSlotProperty[T, T_co]: ...

    @overload
    def __get__(self, instance: T, owner: type[T]) -> T_co: ...

    def __get__(
        self, instance: T | None, owner: type[T]
    ) -> CachedSlotProperty[T, T_co] | T_co:
        if instance is None:
            return self

        try:
            return getattr(instance, self.name)
        except AttributeError:
            value = self.function(instance)
            setattr(instance, self.name, value)
            return value


class ClassProperty(Generic[T, T_co]):
    def __init__(self, function: Callable[[type[T]], T_co]) -> None:
        self.function = function

    def __get__(self, instance: T | None, owner: type[T]) -> T_co:
        return self.function(owner)

    def __set__(self, instance: T | None, value: Any) -> None:
        raise AttributeError("class properties can not be changed")


@overload
def cached_property(
    name_or_func: str, /
) -> Callable[[Callable[[T], T_co]], CachedSlotProperty[T, T_co]]: ...


@overload
def cached_property(
    name_or_func: Callable[[T], T_co], /
) -> CachedProperty[T, T_co]: ...


def cached_property(
    name_or_func: str | Callable[[T], T_co], /
) -> (
    CachedProperty[T, T_co]
    | Callable[[Callable[[T], T_co]], CachedSlotProperty[T, T_co]]
):
    if not isinstance(name_or_func, str):
        return CachedProperty(name_or_func)

    def decorator(func: Callable[[T], T_co]) -> CachedSlotProperty[T, T_co]:
        return CachedSlotProperty(name_or_func, func)

    return decorator


def class_property(func: Callable[[type[T]], T_co]) -> ClassProperty[T, T_co]:
    return ClassProperty(func)
