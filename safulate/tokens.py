from __future__ import annotations

from dataclasses import dataclass

TYPE_CHECKING = False
if TYPE_CHECKING:
    from .enums import TokenType

__all__ = ("Token",)


@dataclass
class Token:
    type: TokenType
    lexeme: str
    start: int

    def __repr__(self) -> str:
        return f"Token(type={self.type!r}, lexeme={self.lexeme!r}, start={self.start})"

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
            lexeme=token_type.value if lexme is None else lexme,
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
            lexeme=token_type.value if lexme is None else lexme,
            start=self.start,
        )
