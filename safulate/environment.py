from __future__ import annotations

from typing import Any, Self

from .errors import SafulateAttributeError, SafulateNameError, SafulateScopeError
from .tokens import Token
from .values import FuncValue, Value, null

__all__ = ("Environment",)


class Environment:
    __slots__ = "parent", "scope", "values"

    def __init__(
        self, parent: Environment | None = None, scope: Value | None = None
    ) -> None:
        self.values: dict[str, Value] = {}
        self.parent: Environment | None = parent
        self.scope: Value | None = scope

        if scope:
            self.values = scope.public_attrs

    def add_builtins(self) -> Self:
        from .libs.builtins import exporter as builtins

        self.values.update(builtins.exports)
        return self

    def __getitem__(self, token: Token) -> Value:
        name = token.lexeme

        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent[token]

        raise SafulateNameError(f"Name {name!r} is not defined", token)

    def __setitem__(self, token: Token | str, value: Any) -> None:
        name = token.lexeme if isinstance(token, Token) else token

        if name in self.values:
            self.values[name] = value
        elif self.parent:
            self.parent[token] = value
        elif isinstance(token, str):
            self.values[name] = value
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

    def get_priv(self, name: Token) -> Value:
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

    def _set_parent(self, val: Value) -> None:
        if isinstance(val, FuncValue):
            val.parent = self.scope
