from __future__ import annotations
from typing import Any, TYPE_CHECKING
from typing import Callable, Concatenate

if TYPE_CHECKING:
    from . import Token
    from .core import StringToken, IntToken
    from ..executer import Executer


def method[**P, RT: Token](
    name: str,
) -> Callable[
    [Callable[Concatenate[Any, Executer, P], RT]],
    Callable[Concatenate[Any, Executer, P], RT],
]:
    def deco[T](func: T) -> T:
        setattr(func, "__func_name__", name)
        return func

    return deco


class AttrsMixin:
    public_attrs: dict[str, Token]
    private_attrs: dict[str, Token]

    if TYPE_CHECKING:
        value: Any

    def __getitem__(self, key: str) -> Token:
        if key != (key := key.removeprefix("$")):
            return self.private_attrs[key]
        return self.public_attrs[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if key != (key := key.removeprefix("$")):
            self.private_attrs[key] = value
        else:
            self.public_attrs[key] = value


class BuiltinMethodsMixin:
    if TYPE_CHECKING:
        value: Any

    @method("$repr")
    def method_repr(self, exe: Executer) -> StringToken:
        from .core import StringToken  # circular import

        return StringToken(f"<{self.__class__.__name__} {self.value=}>")

    @method("$str")
    def to_str(self, exe: Executer) -> StringToken:
        return self.method_repr(exe)

    @method("$eq")
    def equality_check(self, exe: Executer, other: Token) -> IntToken:
        from .core import IntToken  # circular import

        return IntToken(
            1 if isinstance(other, self.__class__) and other.value == self.value else 0
        )

    def to_python(self, exe: Executer) -> Any:
        return self.to_str(exe)

    def resolve(self, exe: Executer) -> Token:
        return exe.resolve_token(self)  # pyright: ignore[reportArgumentType]
