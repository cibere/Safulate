from __future__ import annotations

from typing import Any

from ..errors import SafulateAttributeError, SafulateNameError, SafulateScopeError
from ..lexer import Token
from ..properties import cached_property
from .objects import SafBaseObject, SafFunc, null

__all__ = ("Environment",)


class Environment:
    __slots__ = "__cs_builtins__", "parent", "scope", "values"

    def __init__(
        self, parent: Environment | None = None, scope: SafBaseObject | None = None
    ) -> None:
        self.values: dict[str, SafBaseObject] = {}
        self.parent: Environment | None = parent
        self.scope: SafBaseObject | None = scope

        if scope:
            self.values = scope.public_attrs

    @cached_property("__cs_builtins__")
    def _builtins(self) -> dict[str, SafBaseObject]:
        from .libs.builtins import Builtins

        return Builtins().public_attrs

    def __getitem__(self, token: Token) -> SafBaseObject:
        name = token.lexeme

        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent[token]
        if name in self._builtins:
            return self._builtins[name]

        raise SafulateNameError(f"Name {name!r} is not defined", token)

    def __setitem__(self, token: Token | str, value: Any) -> None:
        name = token.lexeme if isinstance(token, Token) else token

        if name in self.values:
            self.values[name] = value
        elif self.parent:
            self.parent[token] = value
        elif isinstance(token, str):
            self.values[name] = value
        elif name in self._builtins:
            self._builtins[name] = value
        else:
            raise SafulateNameError(f"Name {name!r} is not defined", token)
        self._set_parent(value)

    def declare(self, token: Token | str) -> None:
        self.values[token.lexeme if isinstance(token, Token) else token] = null

    def set_priv(self, name: Token, value: Any) -> None:
        if self.scope is None:
            raise SafulateScopeError(
                "private vars can only be set in an edit object statement", token=name
            )

        self.scope.private_attrs[name.lexeme] = value
        self._set_parent(value)

    def get_priv(self, name: Token) -> SafBaseObject:
        if self.scope is None:
            raise SafulateScopeError(
                "no private vars are being exposed in the current scope", name
            )

        val = self.scope.private_attrs.get(name.lexeme)
        if val is None:
            raise SafulateAttributeError(
                f"Private Var Not Found: {name.lexeme!r}", name
            )

        return val

    def _set_parent(self, val: SafBaseObject) -> None:
        if isinstance(val, SafFunc):
            val.public_attrs["parent"] = self.scope or null
