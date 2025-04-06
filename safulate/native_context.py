from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .values import ListValue, NullValue, NumValue, ObjectValue, StrValue, Value

if TYPE_CHECKING:
    from .interpreter import TreeWalker
    from .tokens import Token

__all__ = ("NativeContext",)


class NativeContext:
    def __init__(self, interpreter: TreeWalker, token: Token) -> None:
        self.interpreter = interpreter
        self.token = token

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
                raise ValueError(f"Unable to convert {x!r} to value")

    def value_to_python(self, obj: Value) -> Any:
        match obj:
            case ObjectValue():
                return {
                    key: self.value_to_python(value) for key, value in obj.attrs.items()
                }
            case ListValue():
                return [self.value_to_python(child) for child in obj.value]
            case StrValue() | NumValue():
                return obj.value
            case NullValue():
                return None
            case _ as x:
                raise ValueError(f"Unable to convert {x!r} to value")
