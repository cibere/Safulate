from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .errors import SafulateTypeError
from .values import ListValue, NullValue, NumValue, ObjectValue, StrValue, Value

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
            return NullValue()

        match obj:
            case dict() as obj:
                return ObjectValue(
                    "json-dict",
                    {key: self.python_to_values(value) for key, value in obj.items()},  # pyright: ignore[reportUnknownVariableType]
                )
            case list() as obj:
                return ListValue([self.python_to_values(child) for child in obj])  # pyright: ignore[reportUnknownVariableType]
            case str():
                return StrValue(obj)
            case int() | float():
                return NumValue(float(obj))
            case _ as x:
                raise SafulateTypeError(f"Unable to convert {x!r} to value")

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
                return x.repr_spec()
            case _ as x:
                raise SafulateTypeError(f"Unable to convert {x.repr_spec()} to value")
