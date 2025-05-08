# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "msgspec",
#     "packaging",
# ]
# ///
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Self, TypeAlias, TypeVar

from safulate import (
    EnumAnd,
    EnumOr,
    SoftKeyword,
    Token,
    TokenType,
)
from safulate.enums import Enum

if TYPE_CHECKING:
    from collections.abc import Callable


TokenT = TypeVar("TokenT")
Sequence: TypeAlias = Enum | EnumAnd[Any] | EnumOr[Any]  # | SequenceConst
type TokenValidator[TokenT] = Callable[[TokenT, Enum], bool]


class SequenceTransaction[TokenT]:
    def __init__(
        self, parent: SequenceMatcher[TokenT] | SequenceTransaction[TokenT]
    ) -> None:
        self.idx: int = parent.idx
        self.parent = parent

    def validate(self, type_: Enum, /) -> bool:
        if isinstance(self.parent, SequenceMatcher):
            return self.parent.validate_type(self.token, type_)
        return self.parent.validate(type_)

    @property
    def tokens(self) -> list[TokenT]:
        return self.parent.tokens

    @property
    def token(self) -> TokenT:
        return self.tokens[self.idx]

    def advance(self) -> None:
        self.idx += 1

    def commit(self) -> None:
        self.parent.idx = self.idx

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any):
        return False

    def transaction(self) -> SequenceTransaction[TokenT]:
        return SequenceTransaction(self)

    def process(self, entry: Sequence) -> bool:
        print(f"trans checking {entry!r} {type(entry)} {self.idx=} {id(self)=}")
        match entry:
            case Enum():
                if self.validate(entry):
                    self.advance()
                    return True
                return False
            case EnumAnd():
                with self.transaction() as trans:
                    for child in entry.value:
                        if trans.process(child):
                            self.advance()
                        else:
                            return False

                    trans.commit()
                    return True
            case EnumOr():
                for child in entry.value:
                    with self.transaction() as trans:
                        if trans.process(child):
                            trans.commit()
                            return True
                return False
            case _:
                raise RuntimeError(f"Unknown entry: {entry!r}")


class SequenceMatcher(ABC, Generic[TokenT]):
    def __init__(self, tokens: list[TokenT]) -> None:
        self.tokens = tokens.copy()
        self.idx = 0

    def transaction(self) -> SequenceTransaction[TokenT]:
        return SequenceTransaction(self)

    @abstractmethod
    def validate_type(self, token: TokenT, type: Enum) -> bool: ...

    def check_sequence(
        self,
        *sequence: Sequence,
    ) -> bool:
        print("checking sequence")
        print(sequence)
        print("\n\n\n")
        with self.transaction() as trans:
            for entry in sequence:
                print(f"seq checking {entry!r}")
                if not trans.process(entry):
                    print(f"{entry=} returned false")
                    print(f"{self.idx=}")
                    return False
        return True

    # def check_sequence(
    #     self,
    #     *types: Sequence,
    # ) -> bool:
    #     return self._get_sequence(types, consume=False) is not None


class SafMatcher(SequenceMatcher[Token]):
    def validate_type(self, token: Token, type: Enum) -> bool:
        match type:
            case TokenType():
                return token.type is type
            case SoftKeyword():
                return token.type is TokenType.ID and token.lexeme == type.value
            case _:
                raise RuntimeError(f"Unknown token type {type!r}")


def main():
    # seq = (
    #     (
    #         (TokenType.PUB | TokenType.PRIV) & (SoftKeyword.STRUCT | TokenType.TYPE)
    #     ) | (
    #         TokenType.PUB | TokenType.PRIV | SoftKeyword.STRUCT | TokenType.TYPE
    #     )
    # ) & TokenType.ID & (
    #     TokenType.LPAR | TokenType.LSQB | TokenType.LBRC
    # )
    seq = (
        ((TokenType.PUB | TokenType.PRIV) & (SoftKeyword.STRUCT | TokenType.TYPE))
        | (TokenType.PUB | TokenType.PRIV | SoftKeyword.STRUCT | TokenType.TYPE)
    ) & EnumAnd(TokenType.ID)
    (
        (
            ((TokenType.PUB | TokenType.PRIV) & ("SoftKeyword.STRUCT" | TokenType.TYPE))
            | (TokenType.PUB | TokenType.PRIV | "SoftKeyword.STRUCT" | TokenType.TYPE)
        )
        & (TokenType.ID)
    )

    print(f"{seq!r}")
    print("\n\n\n")
    print(
        repr(
            ((TokenType.PUB | TokenType.PRIV) & (SoftKeyword.STRUCT | TokenType.TYPE))
            | (TokenType.PUB | TokenType.PRIV | SoftKeyword.STRUCT | TokenType.TYPE)
        )
    )
    return
    matcher = SafMatcher(
        [
            Token.mock(TokenType.PUB),
            Token.mock(TokenType.ID, lexme="struct"),
            Token.mock(TokenType.ID, lexme="hi"),
            Token.mock(TokenType.LPAR),
        ]
    )
    res = matcher.check_sequence(seq)
    print(f"{res=}")


main()
