from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, cast

from ..errors import ErrorManager, SafulateError, SafulateTypeError
from .enums import CallSpec, SpecName
from .objects import (
    SafBaseObject,
    SafDict,
    SafFunc,
    SafList,
    SafNull,
    SafNum,
    SafStr,
    null,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..lexer import Token
    from .environment import Environment
    from .interpreter import Interpreter

__all__ = ("NativeContext",)


class NativeContext:
    __slots__ = "interpreter", "token"

    def __init__(self, interpreter: Interpreter, token: Token) -> None:
        self.interpreter = interpreter
        self.token = token

    def invoke(
        self, func: SafBaseObject, *args: SafBaseObject, **kwargs: SafBaseObject
    ) -> SafBaseObject:
        with ErrorManager(token=self.token):
            caller = func if isinstance(func, (SafFunc)) else func.specs[CallSpec.call]
            return caller.call(self, *args, **kwargs)  # pyright: ignore[reportArgumentType]

    def invoke_spec(
        self,
        func: SafBaseObject,
        spec_name: SpecName,
        *args: SafBaseObject,
        **kwargs: SafBaseObject,
    ) -> SafBaseObject:
        return self.invoke(func.specs[spec_name], *args, **kwargs)

    @property
    def env(self) -> Environment:
        return self.interpreter.env

    def walk_envs(self) -> Iterator[Environment]:
        env: Environment | None = self.env

        while 1:
            if env:
                yield env
            else:
                break
            env = env.parent

    def python_to_values(self, obj: Any) -> SafBaseObject:
        if obj is None:
            return null

        if isinstance(obj, dict):
            return SafDict.from_data(
                self,
                {
                    key: self.python_to_values(value)
                    for key, value in cast("dict[Any, Any]", obj).items()
                },
            )
        elif isinstance(obj, list):
            return SafList(
                [self.python_to_values(child) for child in cast("list[Any]", obj)]
            )
        elif isinstance(obj, str):
            return SafStr(obj)
        elif isinstance(obj, int | float):
            return SafNum(float(obj))
        else:
            raise SafulateTypeError(f"Unable to convert {obj!r} to value")

    def value_to_python(
        self,
        obj: SafBaseObject,
        *,
        repr_fallback: bool = False,
        ignore_null_attrs: bool = False,
    ) -> Any:
        match obj:
            case SafDict():
                return {
                    self.value_to_python(key, repr_fallback=repr_fallback): value
                    for key, raw_value in obj.data.values()
                    if (
                        (
                            value := self.value_to_python(
                                raw_value, repr_fallback=repr_fallback
                            )
                        )
                        is not None
                        and ignore_null_attrs is True
                    )
                    or ignore_null_attrs is False
                }
            case SafList():
                return [
                    value
                    for child in obj.value
                    if (
                        (
                            value := self.value_to_python(
                                child, repr_fallback=repr_fallback
                            )
                        )
                        is not None
                        and ignore_null_attrs is True
                    )
                    or ignore_null_attrs is False
                ]
            case SafStr() | SafNum():
                return obj.value
            case SafNull():
                return None
            case _ as x if repr_fallback:
                return x.repr_spec(self)
            case _ as x:
                raise SafulateTypeError(
                    f"Unable to convert {x.repr_spec(self)} to value"
                )

    def eval(self, code: str, *, name: str) -> Interpreter:
        from .repl import code_to_ast

        try:
            visitor = self.interpreter.__class__(name)
            code_to_ast(code).visit(visitor)
            return visitor
        except SafulateError as e:
            for token in e.tokens:
                token.update_if_empty(source=code, filename=name)
            raise e
