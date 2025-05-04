from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from .enums import TokenType
from .properties import cached_property
from .tokens import Token

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType
    from typing import Literal

    from .objects import SafBaseObject, SafPythonError

T = TypeVar("T")

__all__ = (
    "ErrorManager",
    "SafulateAssertionError",
    "SafulateBreakoutError",
    "SafulateError",
    "SafulateIndexError",
    "SafulateInvalidContinue",
    "SafulateInvalidReturn",
    "SafulateKeyError",
    "SafulateNameError",
    "SafulateRuntimeError",
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
        self, msg: str, token: Token | None = None, obj: SafBaseObject | None = None
    ) -> None:
        super().__init__(msg)

        self.msg = msg
        self.obj = obj
        self.tokens: list[TokenEntry] = []

        if token:
            self.tokens.append(TokenEntry(token))

    @property
    def name(self) -> str:
        return self.__class__.__name__.removeprefix("Safulate")

    @cached_property
    def saf_value(self) -> SafPythonError:
        from .objects import SafPythonError, null

        return SafPythonError(error=self.name, msg=self.msg, obj=self.obj or null)

    def _make_subreport(self, entry: TokenEntry, src: str, filename: str | None) -> str:
        src = entry.source or src
        filename = entry.filename or filename

        line = src[: entry.token.start].count("\n") + 1
        if line > 1:
            col = src[entry.token.start - 1 :: -1].index("\n") + 1
        else:
            col = entry.token.start + 1

        src = src.splitlines()[line - 1]
        ws = len(src) - len(src.lstrip())
        file_prefix = f"File {filename!r}, " if filename else ""
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

    def make_report(self, src: str, *, filename: str | None = None) -> str:
        return (
            "\n".join(
                self._make_subreport(token, src=src, filename=filename)
                for (token) in self.tokens
            )
            + "\033[31m\n"
            + self.name
            + ": "
            + self.msg
            + "\033[0m"
        )

    def print_report(self, source: str, *, filename: str | None = None) -> None:
        print(self.make_report(source, filename=filename))


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
    def __init__(self, value: SafBaseObject, token: Token) -> None:
        self.value = value

        super().__init__("Return used outside of function", token)


class SafulateInvalidContinue(SafulateError):
    def __init__(self, amount: int, token: Token) -> None:
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
    def __init__(self, amount: int, token: Token) -> None:
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


class SafulateIndexError(SafulateError):
    pass


class SafulateRuntimeError(SafulateError):
    pass
