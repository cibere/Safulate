from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from .mock import MockToken
from .tokens import Token, TokenType

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType
    from typing import Literal

    from .values import Value

T = TypeVar("T")

__all__ = (
    "ErrorManager",
    "SafulateAssertionError",
    "SafulateBreakoutError",
    "SafulateError",
    "SafulateInvalidContinue",
    "SafulateInvalidReturn",
    "SafulateKeyError",
    "SafulateNameError",
    "SafulateSyntaxError",
    "SafulateTypeError",
    "SafulateValueError",
)


class ErrorManager:
    __slots__ = ("start", "token")

    def __init__(
        self,
        *,
        start: Callable[[], int] | int | None = None,
        token: Token | None | Callable[[], Token] = None,
    ) -> None:
        self.start = start
        self.token = token

    def __enter__(self) -> None:
        return

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if (not exc_type and not exc_value and not traceback) or not isinstance(
            exc_value, SafulateError
        ):
            return False

        if self.token:
            token = self.token if isinstance(self.token, Token) else self.token()
        elif self.start:
            token = Token(
                TokenType.ERR,
                "",
                self.start if isinstance(self.start, int) else self.start(),
            )
        else:
            raise RuntimeError("Error manager got no way of getting token")

        exc_value.tokens.insert(0, TokenEntry(token))

        return False


class TokenEntry:
    def __init__(
        self, token: Token, *, source: str | None = None, filename: str | None = None
    ) -> None:
        self.token = token
        self.source = source
        self.filename = filename

    def update_if_empty(
        self, source: str | None = None, filename: str | None = None
    ) -> None:
        if source is not None:
            self.source = source
        if filename is not None:
            self.filename = filename


class SafulateError(BaseException):
    def __init__(
        self, msg: str, token: Token | None = None, obj: Value | None = None
    ) -> None:
        self.msg = msg
        self.obj = obj
        self.tokens: list[TokenEntry] = []

        if token:
            self.tokens.append(TokenEntry(token))

        super().__init__(self.msg)

    def _make_subreport(self, entry: TokenEntry, src: str) -> str:
        src = entry.source or src

        line = src[: entry.token.start].count("\n") + 1
        if line > 1:
            col = src[entry.token.start - 1 :: -1].index("\n") + 1
        else:
            col = entry.token.start + 1

        src = src.splitlines()[line - 1]
        ws = len(src) - len(src.lstrip())
        file_prefix = f"File {entry.filename!r}, " if entry.filename else ""
        res = f"\033[31m{file_prefix}Line {line}, col {col}\n\033[36m{line:>5} | \033[0m{src.lstrip()}\n"
        res += (
            "\033[36m  "
            + " " * max(5, len(str(line)))
            + "-" * (col - ws)
            + "^"
            + "-" * (len(src) - col)
            + "-"
        )
        return res

    def make_report(self, source: str) -> str:
        return (
            "\n".join(self._make_subreport(token, source) for (token) in self.tokens)
            + "\033[31m\n"
            + self.__class__.__name__.removeprefix("Safulate")
            + ": "
            + self.msg
            + "\033[0m"
        )

    def print_report(self, source: str) -> None:
        print(self.make_report(source))


class SafulateNameError(SafulateError):
    pass


class SafulateValueError(SafulateError):
    pass


class SafulateSyntaxError(SafulateError):
    pass


class SafulateAttributeError(SafulateError):
    pass


class SafulateImportError(SafulateError):
    pass


class SafulateVersionConflict(SafulateError):
    pass


class SafulateTypeError(SafulateError):
    pass


class SafulateInvalidReturn(SafulateError):
    def __init__(self, value: Value, token: Token = MockToken()) -> None:
        self.value = value

        super().__init__("Return used outside of function", token)


class SafulateInvalidContinue(SafulateError):
    def __init__(self, amount: int, token: Token = MockToken()) -> None:
        self.amount = amount

        super().__init__("Continue used in a context where it isn't allowed", token)

    def handle_skips(self, loops: list[T]) -> T | None:
        next_loop = None

        while self.amount != 0:
            try:
                next_loop = loops.pop(0)
            except IndexError:
                return
            self.amount -= 1

        if next_loop:
            loops.insert(0, next_loop)
        return next_loop


class SafulateBreakoutError(SafulateError):
    def __init__(self, amount: int, token: Token = MockToken()) -> None:
        self.amount = amount

        super().__init__("No more loops to break out of", token)

    def check(self) -> None:
        self.amount -= 1
        if self.amount != 0:
            raise self from None


class SafulateAssertionError(SafulateError):
    pass


class SafulateKeyError(SafulateError):
    pass


class SafulateScopeError(SafulateError):
    pass
