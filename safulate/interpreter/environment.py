from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..errors import SafulateNameError, SafulateScopeError
from ..lexer import Token
from ..properties import cached_property
from .objects import SafBaseObject, null

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ("Environment",)


class Environment:
    __slots__ = "__cs_builtins__", "parent", "scope", "values"

    def __init__(
        self,
        *,
        parent: Environment | None = None,
        scope: SafBaseObject,
    ) -> None:
        self.scope: SafBaseObject | None = scope
        self.values: dict[str, SafBaseObject] = scope.public_attrs

    @cached_property("__cs_builtins__")
    def _builtins(self) -> dict[str, SafBaseObject]:
        from .libs.builtins import Builtins

        return Builtins().public_attrs

    def __getitem__(self, token: Token) -> SafBaseObject:
        name = token.lexme

        if name in self.values:
            return self.values[name]
        if self.scope:
            for scope in self.walk_parents(self.scope, include_self=True):
                if name in scope.public_attrs:
                    return scope.public_attrs[name]
        if name in self._builtins:
            return self._builtins[name]

        raise SafulateNameError(f"Name {name!r} is not defined", token)

    def __setitem__(self, token: Token | str, value: Any) -> None:
        name = token.lexme if isinstance(token, Token) else token

        if name in self.values or isinstance(token, str):
            self.values[name] = value
        elif self.scope:
            for scope in self.walk_parents(self.scope, include_self=True):
                if name in scope.public_attrs:
                    scope.public_attrs[name] = value
                    break
        elif name in self._builtins:
            self._builtins[name] = value
        else:
            raise SafulateNameError(f"Name {name!r} is not defined", token)

    def declare(self, token: Token | str) -> None:
        self.values[token.lexme if isinstance(token, Token) else token] = null

    def walk_parents(
        self, obj: SafBaseObject, *, include_self: bool = False
    ) -> Iterator[SafBaseObject]:
        if include_self:
            yield obj

        scope: SafBaseObject | None = obj
        while 1:
            scope = scope.parent

            if scope:
                yield scope
            else:
                break

    def get_scope_parent(self, levels: list[Token]) -> SafBaseObject:
        _levels = levels.copy()
        assert self.scope

        for scope in self.walk_parents(self.scope, include_self=True):
            if _levels:
                _levels.pop(0)

            if not _levels:
                return scope

        raise SafulateScopeError("Can't go any futher", levels[-1])
