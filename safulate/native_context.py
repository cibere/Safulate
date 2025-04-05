from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interpreter import TreeWalker
    from .tokens import Token

__all__ = ("NativeContext",)


class NativeContext:
    def __init__(self, interpreter: TreeWalker, token: Token):
        self.interpreter = interpreter
        self.token = token
