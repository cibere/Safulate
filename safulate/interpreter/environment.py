from __future__ import annotations

from typing import Any

from ..errors import SafulateNameError
from ..lexer import Token
from ..properties import cached_property
from .objects import SafBaseObject, null

__all__ = ("Environment",)


class Environment:
    __slots__ = "__cs_builtins__", "parent", "scope", "values"

    def __init__(
        self,
        parent: Environment | None = None,
        scope: SafBaseObject | None = None,
        isolated_public_vars: bool = False,
    ) -> None:
        self.values: dict[str, SafBaseObject] = {}
        self.parent: Environment | None = parent
        self.scope: SafBaseObject | None = scope

        if not isolated_public_vars and scope:
            self.values = scope.public_attrs

    @cached_property("__cs_builtins__")
    def _builtins(self) -> dict[str, SafBaseObject]:
        from .libs.builtins import Builtins

        return Builtins().public_attrs

    def __getitem__(self, token: Token) -> SafBaseObject:
        name = token.lexme

        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent[token]
        if name in self._builtins:
            return self._builtins[name]

        raise SafulateNameError(f"Name {name!r} is not defined", token)

    def __setitem__(self, token: Token | str, value: Any) -> None:
        name = token.lexme if isinstance(token, Token) else token

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

    def declare(self, token: Token | str) -> None:
        self.values[token.lexme if isinstance(token, Token) else token] = null
