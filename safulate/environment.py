from __future__ import annotations

from typing import Any

from .errors import SafulateNameError
from .tokens import Token
from .values import FuncValue, NullValue, Value

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

    def __getitem__(self, token: Token) -> Value:
        name = token.lexeme

        if name.startswith("$") and self.scope and name in self.scope.private_attrs:
            return self.scope.private_attrs[name]

        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent[token]

        raise SafulateNameError(f"Name {name!r} is not defined", token)

    def __setitem__(self, token: Token | str, value: Any) -> None:
        name = token.lexeme if isinstance(token, Token) else token

        if self.scope:
            if isinstance(value, FuncValue):
                value.parent = self.scope

            if name.startswith("%"):
                self.scope.specs[name.removeprefix("%")] = value
                return
            if name.startswith("$"):
                self.scope.private_attrs[name] = value
                return

        if name in self.values:
            self.values[name] = value
        elif self.parent:
            self.parent[token] = value
        elif isinstance(token, str):
            self.values[name] = value
        else:
            raise SafulateNameError(f"Name {name!r} is not defined", token)

    def declare(self, token: Token | str) -> None:
        self.values[token.lexeme if isinstance(token, Token) else token] = NullValue()
