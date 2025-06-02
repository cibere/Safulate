from __future__ import annotations

from typing import TYPE_CHECKING

from .properties import cached_property

if TYPE_CHECKING:
    from . import lexer as l
    from .interpreter import SafBaseObject, SafPythonError
else:
    from .utils import LazyImport

    l = LazyImport("safulate", "lexer")  # noqa: E741

__all__ = (
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


class TokenEntry:
    __slots__ = ("filename", "source", "token")

    def __init__(
        self, token: l.Token, *, source: str | None = None, filename: str | None = None
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
    __slots__ = "__cs_saf_value__", "msg", "obj", "tokens"

    def __init__(
        self, msg: str, token: l.Token | None = None, obj: SafBaseObject | None = None
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

    @cached_property("__cs_saf_value__")
    def saf_value(self) -> SafPythonError:
        from .interpreter.objects import SafPythonError, null

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

    def _add_token(
        self, token: l.Token, *, source: str | None = None, filename: str | None = None
    ) -> None:
        self.tokens.insert(0, TokenEntry(token, source=source, filename=filename))


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
    __slots__ = ("value",)

    def __init__(self, value: SafBaseObject, token: l.Token) -> None:
        self.value = value

        super().__init__("Return used outside of function", token)


class SafulateInvalidContinue(SafulateError):
    __slots__ = ("amount",)

    def __init__(self, amount: int, token: l.Token) -> None:
        self.amount = amount

        super().__init__("Continue used in a context where it isn't allowed", token)


class SafulateBreakoutError(SafulateError):
    __slots__ = ("amount",)

    def __init__(self, amount: int, token: l.Token) -> None:
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
