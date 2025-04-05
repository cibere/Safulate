from __future__ import annotations

from .mock import MockToken
from .tokens import Token, TokenType

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType
    from typing import Literal

    from .values import Value

__all__ = (
    "ErrorManager",
    "SafulateAssertionError",
    "SafulateBreakoutError",
    "SafulateError",
    "SafulateInvalidReturn",
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
        if not exc_type and not exc_value and not traceback:
            return False

        mock_token = getattr(exc_value, "token", None)
        if not isinstance(exc_value, SafulateError) or not isinstance(
            mock_token, MockToken
        ):
            return False

        if self.token:
            token = self.token if isinstance(self.token, Token) else self.token()
        elif self.start:
            token = Token(
                TokenType.ERR,
                getattr(mock_token, "__error_text__"),
                self.start if isinstance(self.start, int) else self.start(),
            )
        else:
            raise RuntimeError("Error manager got no way of getting token")

        exc_value.token = token

        return False


class SafulateError(BaseException):
    def __init__(self, obj: str | Value, token: Token = MockToken()) -> None:
        self.message = str(obj)
        self.token = token

        super().__init__(self.message)

    def make_report(self, source: str) -> str:
        line = source[: self.token.start].count("\n") + 1
        if line > 1:
            col = source[self.token.start - 1 :: -1].index("\n") + 1
        else:
            col = self.token.start + 1

        src = source.splitlines()[line - 1]
        ws = len(src) - len(src.lstrip())
        res = f"\033[31mFile 'files_not_implemented.test' line {line}, col {col}\n\033[36m{line:>5} | \033[0m{src.lstrip()}\n"
        res += (
            "\033[36m  "
            + " " * max(5, len(str(line)))
            + "-" * (col - ws)
            + "^"
            + "-" * (len(src) - col)
            + "-"
        )
        return (
            res
            + "\033[31m\n"
            + type(self).__name__.lstrip("Test")
            + ": "
            + self.message
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


class SafulateBreakoutError(SafulateError):
    def __init__(self, amount: int, token: Token = MockToken()) -> None:
        self.amount = amount

        super().__init__("No more loops to break out of", token)


class SafulateAssertionError(SafulateError):
    pass
