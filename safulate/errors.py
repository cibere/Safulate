from __future__ import annotations

from .mock import MockToken
from .tokens import Token, TokenType

TYPE_CHECKING = False
if TYPE_CHECKING:
    from types import TracebackType
    from typing import Callable, Literal

__all__ = (
    "SafulateError",
    "SafulateNameError",
    "SafulateValueError",
    "SafulateSyntaxError",
    "ErrorManager",
    "SafulateTypeError",
)


class ErrorManager:
    __slots__ = ("get_start", "token")

    def __init__(
        self, *, start: Callable[[], int] | None = None, token: Token | None = None
    ) -> None:
        self.get_start = start
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
            token = self.token
        elif self.get_start:
            token = Token(
                TokenType.ERR, getattr(mock_token, "__error_text__"), self.get_start()
            )
        else:
            raise RuntimeError("Error manager got no way of getting token")

        exc_value.token = token

        return False


class SafulateError(BaseException):
    def __init__(self, msg: str, token: Token = MockToken()):
        super().__init__(msg)

        self.message = msg
        self.token = token

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
