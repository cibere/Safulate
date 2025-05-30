from __future__ import annotations

from msgspec import Struct

TYPE_CHECKING = False
if TYPE_CHECKING:
    from .enums import TokenType

__all__ = ("Token",)


class Token(Struct):
    type: TokenType
    lexme: str
    start: int

    def __repr__(self) -> str:
        return f"Token(type={self.type!r}, lexme={self.lexme!r}, start={self.start})"

    @classmethod
    def mock(
        cls,
        token_type: TokenType,
        /,
        *,
        lexme: str | None = None,
        start: int | None = None,
    ) -> Token:
        return Token(
            type=token_type,
            lexme=token_type.value if lexme is None else lexme,
            start=-1 if start is None else start,
        )

    def with_type(
        self,
        token_type: TokenType,
        /,
        *,
        lexme: str | None = None,
    ) -> Token:
        return Token(
            token_type,
            lexme=token_type.value if lexme is None else lexme,
            start=self.start,
        )
