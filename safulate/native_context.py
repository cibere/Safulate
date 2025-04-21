from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, cast

from .errors import ErrorManager, SafulateTypeError
from .values import (
    DictValue,
    FuncValue,
    ListValue,
    NullValue,
    NumValue,
    ObjectValue,
    StrValue,
    Value,
    null,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .environment import Environment
    from .interpreter import TreeWalker
    from .tokens import Token

__all__ = ("NativeContext",)


class NativeContext:
    def __init__(self, interpreter: TreeWalker, token: Token) -> None:
        self.interpreter = interpreter
        self.token = token

    def invoke(self, func: Value, *args: Value, **kwargs: Value) -> Value:
        with ErrorManager(token=self.token):
            caller = func if isinstance(func, (FuncValue)) else func.specs["call"]
            return caller.call(self, *args, **kwargs)

    def invoke_spec(
        self, func: Value, spec_name: str, *args: Value, **kwargs: Value
    ) -> Value:
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

    def python_to_values(self, obj: Any) -> Value:
        if obj is None:
            return null

        if isinstance(obj, dict):
            return DictValue(
                {
                    self.python_to_values(key): self.python_to_values(value)
                    for key, value in cast("dict[Any, Any]", obj).items()
                },
            )
        elif isinstance(obj, list):
            return ListValue(
                [self.python_to_values(child) for child in cast("list[Any]", obj)]
            )
        elif isinstance(obj, str):
            return StrValue(obj)
        elif isinstance(obj, int | float):
            return NumValue(float(obj))
        else:
            raise SafulateTypeError(f"Unable to convert {obj!r} to value")

    def value_to_python(
        self,
        obj: Value,
        *,
        repr_fallback: bool = False,
        ignore_null_attrs: bool = False,
    ) -> Any:
        match obj:
            case ObjectValue():
                return {
                    key: value
                    for key, raw_value in obj.attrs.items()
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
            case ListValue():
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
            case StrValue() | NumValue():
                return obj.value
            case NullValue():
                return None
            case _ as x if repr_fallback:
                return x.repr_spec(self)
            case _ as x:
                raise SafulateTypeError(
                    f"Unable to convert {x.repr_spec(self)} to value"
                )
