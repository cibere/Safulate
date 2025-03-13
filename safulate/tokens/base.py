from __future__ import annotations
from typing import Any, TYPE_CHECKING
import inspect
from .function import Function
from typing import Callable, Concatenate
from .mixins import AttrsMixin, BuiltinMethodsMixin

if TYPE_CHECKING:
    from . import Token
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


class BaseToken[T](AttrsMixin, BuiltinMethodsMixin):
    public_attrs: dict[str, Token]
    private_attrs: dict[str, Token]
    tag: str | None = None
    value: T

    def __init__(self, value: T) -> None:
        self.value = value
        self.public_attrs = {}
        self.private_attrs = {}

        methods = inspect.getmembers(self, lambda d: hasattr(d, "__func_name__"))
        for key, method in methods:
            method: Callable[Concatenate[Any, Executer, ...], Token]
            func = Function(method)
            self[getattr(method, "__func_name__")] = func

        self.validate()

    def __init_subclass__(cls, tag: str | None = None) -> None:
        cls.tag = tag

    def validate(self) -> None:
        return

    def __repr__(self) -> str:
        if isinstance(self.value, list):
            value = "\n".join([repr(item) for item in self.value])
        else:
            value = repr(self.value)
        return f"<{self.__class__.__name__} {value}>"

    def to_dict(self) -> Any:
        if isinstance(self.value, list):
            val = [getattr(val, "to_dict", lambda: val)() for val in self.value]
        else:
            val = getattr(self.value, "to_dict", lambda: self.value)()
        return {"name": self.__class__.__name__, "value": val}
