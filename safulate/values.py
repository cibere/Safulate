from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as _field
from typing import TYPE_CHECKING, Any, Concatenate, cast, final

from .errors import (
    SafulateAttributeError,
    SafulateInvalidReturn,
    SafulateTypeError,
    SafulateValueError,
)
from .mock import MockNativeContext
from .native_context import NativeContext
from .properties import cached_property

if TYPE_CHECKING:
    from .asts import ASTNode
    from .tokens import Token


def __method_deco[T: Callable[Concatenate[Any, NativeContext, ...], "Value"]](
    char: str,
) -> Callable[[str, int | None], Callable[[T], T]]:
    def deco(name: str, arity: int | None) -> Callable[[T], T]:
        def decorator(func: T) -> T:
            setattr(func, "__safulate_native_method__", (char, name, arity))
            return func

        return decorator

    return deco


public_method = __method_deco("")
private_method = __method_deco("$")
special_method = __method_deco("%")


class Value(ABC):
    __safulate_public_attrs__: dict[str, Value] | None = None
    __safulate_private_attrs__: dict[str, Value] | None = (
        None  # __safulate_private_method_info__
    )
    __safulate_specs__: dict[str, Value] | None = (
        None  # __safulate_special_method_info__
    )

    @cached_property
    def _attrs(self) -> defaultdict[str, dict[str, NativeFunc]]:
        data: defaultdict[str, dict[str, NativeFunc]] = defaultdict(dict)
        for name, _ in inspect.getmembers(
            self.__class__, lambda attr: hasattr(attr, "__safulate_native_method__")
        ):
            value = getattr(self, name)

            type_, func_name, arity = getattr(value, "__safulate_native_method__")
            data[type_][func_name] = NativeFunc(
                func_name,
                arity,
                value,
            )
        return data

    @cached_property
    def public_attrs(self) -> dict[str, Value]:
        if self.__safulate_public_attrs__ is None:
            self.__safulate_public_attrs__ = {}

        self.__safulate_public_attrs__.update(self._attrs[""])
        return self.__safulate_public_attrs__

    @cached_property
    def private_attrs(self) -> dict[str, Value]:
        if self.__safulate_private_attrs__ is None:
            self.__safulate_private_attrs__ = {}

        self.__safulate_private_attrs__.update(self._attrs["$"])
        return self.__safulate_private_attrs__

    @cached_property
    def specs(self) -> dict[str, Value]:
        if self.__safulate_specs__ is None:
            self.__safulate_specs__ = {}

        self.__safulate_specs__.update(self._attrs["%"])
        return self.__safulate_specs__

    def __getitem__(self, key: str) -> Value:
        try:
            return self.public_attrs[key]
        except KeyError:
            raise SafulateAttributeError(f"Attribute {key!r} not found")

    def __setitem__(self, key: str, value: Value) -> None:
        self.public_attrs[key] = value

    @private_method("$get_specs", 0)
    def get_specs(self, ctx: NativeContext) -> Value:
        return ContainerValue(f"{self}'s specs", self.specs.copy())

    @special_method("add", 1)
    def add(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Add is not defined for this type")

    @special_method("sub", 1)
    def sub(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Subtract is not defined for this type")

    @special_method("mul", 1)
    def mul(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Multiply is not defined for this type")

    @special_method("div", 1)
    def div(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Divide is not defined for this type")

    @special_method("pow", 1)
    def pow(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Exponentiation is not defined for this type")

    @special_method("uadd", 0)
    def uadd(self, ctx: NativeContext) -> Value:
        raise SafulateValueError("Unary add is not defined for this type")

    @special_method("neg", 0)
    def neg(self, ctx: NativeContext) -> Value:
        raise SafulateValueError("Unary minus is not defined for this type")

    @special_method("eq", 1)
    def eq(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Equality is not defined for this type")

    @special_method("neq", 1)
    def neq(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Non-equality is not defined for this type")

    @special_method("less", 1)
    def less(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Less than is not defined for this type")

    @special_method("grtr", 1)
    def grtr(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Greater than is not defined for this type")

    @special_method("lesseq", 1)
    def lesseq(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Less than or equal to is not defined for this type")

    @special_method("grtreq", 1)
    def grtreq(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError(
            "Greater than or equal to is not defined for this type"
        )

    @special_method("call", None)
    def call(self, ctx: NativeContext, *args: Value) -> Value:
        raise SafulateValueError("Cannot call this type")

    @special_method("iter", 0)
    def iter(self, ctx: NativeContext) -> ListValue:
        raise SafulateValueError("This type is not iterable")

    @special_method("repr", 0)
    @abstractmethod
    def repr(self, ctx: NativeContext) -> Value: ...

    @special_method("str", 0)
    def str(self, ctx: NativeContext) -> Value:
        return self.specs["repr"].call(ctx)

    def truthy(self) -> bool:
        return True

    @final
    def __str__(self) -> str:
        return self.str_spec()

    def repr_spec(self, ctx: NativeContext = MockNativeContext()) -> str:
        func = self.specs["repr"]
        value = func.call(ctx)
        if not isinstance(value, StrValue):
            raise SafulateValueError(
                f"expected return for 'repr' is str, not {value!r}", ctx.token
            )

        return value.value

    def str_spec(self, ctx: NativeContext = MockNativeContext()) -> str:
        func = self.specs["str"]
        value = func.call(ctx)
        if not isinstance(value, StrValue):
            raise SafulateValueError(
                f"expected return for 'str' is str, not {value!r}", ctx.token
            )

        return value.value


@dataclass
class ContainerValue(Value):
    name: str
    attrs: dict[str, Value]

    def __post_init__(self) -> None:
        self.public_attrs.update(self.attrs)

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<Container {self.name!r}>")


class ObjValue(Value):
    def __init__(self, token: Token) -> None:
        self.token = token
        super().__init__()

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<Custom Object @{self.token.start}>")


class NullValue(Value):
    def truthy(self) -> bool:
        return False

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue("null")


@dataclass
class NumValue(Value):
    value: float

    @special_method("add", 1)
    def add(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Add is not defined for number and this type")

        return NumValue(self.value + other.value)

    @special_method("sub", 1)
    def sub(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Subtract is not defined for number and this type")

        return NumValue(self.value - other.value)

    @special_method("mul", 1)
    def mul(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Multiply is not defined for number and this type")

        return NumValue(self.value * other.value)

    @special_method("div", 1)
    def div(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Divide is not defined for number and this type")
        return NumValue(self.value / other.value)

    @special_method("pow", 1)
    def pow(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Exponentiation is not defined for number and this type"
            )

        return NumValue(self.value**other.value)

    @special_method("uadd", 0)
    def uadd(self, ctx: NativeContext) -> NumValue:
        return NumValue(self.value)

    @special_method("neg", 0)
    def neg(self, ctx: NativeContext) -> NumValue:
        return NumValue(-self.value)

    @special_method("eq", 1)
    def eq(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Equality is not defined for number and this type")

        return NumValue(self.value == other.value)

    @special_method("neq", 1)
    def neq(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Non-equality is not defined for number and this type"
            )

        return NumValue(self.value != other.value)

    @special_method("less", 1)
    def less(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Less than is not defined for number and this type"
            )

        return NumValue(self.value < other.value)

    @special_method("grtr", 1)
    def grtr(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Greater than is not defined for number and this type"
            )

        return NumValue(self.value > other.value)

    @special_method("lesseq", 1)
    def lesseq(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Less than or equal to is not defined for number and this type"
            )

        return NumValue(self.value <= other.value)

    @special_method("grtreq", 1)
    def grtreq(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Greater than or equal to is not defined for number and this type",
            )

        return NumValue(self.value >= other.value)

    def truthy(self) -> bool:
        return self.value != 0

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        if self.value % 1 == 0 and "e" not in str(self.value):
            return StrValue(str(int(self.value)))

        return StrValue(str(self.value))


@dataclass
class StrValue(Value):
    value: str

    @special_method("add", 1)
    def add(self, ctx: NativeContext, other: Value) -> StrValue:
        if isinstance(other, StrValue):
            return StrValue(self.value + other.value)

        raise SafulateValueError("Add is not defined for string and this type")

    @special_method("mul", 1)
    def mul(self, ctx: NativeContext, other: Value) -> StrValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Multiply is not defined for string and this type")

        if other.value % 1 != 0:
            raise SafulateValueError(
                "Cannot multiply string by a float, must be integer"
            )

        return StrValue(self.value * int(other.value))

    @special_method("iter", 0)
    def iter(self, ctx: NativeContext) -> ListValue:
        return ListValue([StrValue(char) for char in self.value])

    def truthy(self) -> bool:
        return len(self.value) != 0

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(self.value)


@dataclass
class ListValue(Value):
    value: list[Value]

    @public_method("append", 1)
    def append(self, ctx: NativeContext, item: Value) -> Value:
        self.value.append(item)
        return NullValue()

    @public_method("remove", 1)
    def remove(self, ctx: NativeContext, item: Value) -> Value:
        self.value.remove(item)
        return NullValue()

    @public_method("pop", 1)
    def pop(self, ctx: NativeContext, index: Value) -> Value:
        if not isinstance(index, NumValue):
            raise SafulateTypeError(f"expected num, got {index!r} instead")
        if abs(index.value) > len(self.value):
            return NullValue()

        return self.value.pop(int(index.value))

    def truthy(self) -> bool:
        return len(self.value) != 0

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(
            "["
            + ", ".join(
                [
                    cast("StrValue", val.specs["repr"].call(ctx)).value
                    for val in self.value
                ]
            )
            + "]"
        )


@dataclass
class FuncValue(Value):
    name: Token
    params: list[Token]
    body: ASTNode
    parent: Value = _field(default_factory=NullValue)

    @special_method("call", None)
    def call(self, ctx: NativeContext, *args: Value) -> Value:
        ret_value = NullValue()

        if len(self.params) != len(args):
            raise SafulateValueError(
                f"Function {self.name.lexeme!r} requires {len(self.params)} arguments, but got {len(args)}",
            )

        with ctx.interpreter.scope():
            ctx.interpreter.env["parent"] = self.parent
            if self.parent:
                ctx.interpreter.env.values.update(self.parent.private_attrs)

            for param, arg in zip(self.params, args):
                ctx.interpreter.env.declare(param)
                ctx.interpreter.env[param] = arg

            try:
                self.body.accept(ctx.interpreter)
            except SafulateInvalidReturn as r:
                ret_value = r.value

            self.parent.private_attrs.update(
                {
                    key: value
                    for key, value in ctx.interpreter.env.values.items()
                    if key.startswith("$")
                }
            )

        return ret_value

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<func {self.name.lexeme!r}>")


@dataclass
class NativeFunc(Value):
    name: str
    arity: int | None
    callback: Callable[Concatenate[NativeContext, ...], Value]

    @special_method("call", None)
    def call(self, ctx: NativeContext, *args: Value) -> Value:
        if self.arity is not None and self.arity != len(args):
            raise SafulateValueError(
                f"Built-in function '{self.name}' requires {self.arity} arguments, but got {len(args)}",
            )

        return self.callback(ctx, *args)

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<built-in func {self.name!r}>")


@dataclass
class VersionValue(Value):
    major: NumValue
    minor: NumValue | NullValue
    micro: NumValue | NullValue

    def __post_init__(self) -> None:
        self.public_attrs.update(
            {"major": self.major, "minor": self.minor, "micro": self.micro}
        )

    def _handle_constraint(self, other: Value, constraint: str) -> Value:
        if isinstance(other, VersionValue):
            return VersionConstraintValue(left=self, right=other, constraint=constraint)
        if isinstance(other, NullValue):
            return VersionConstraintValue(left=other, right=self, constraint=constraint)
        raise SafulateValueError(
            f"{constraint!r} operation is not defined for version and this type"
        )

    @special_method("sub", 1)
    def sub(self, ctx: NativeContext, other: Value) -> Value:
        return self._handle_constraint(other, "-")

    @special_method("uadd", 0)
    def uadd(self, ctx: NativeContext) -> Value:
        return self._handle_constraint(NullValue(), "+")

    @special_method("neg", 0)
    def neg(self, ctx: NativeContext) -> Value:
        return self._handle_constraint(NullValue(), "-")

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(
            f"v{self.major}{f'.{self.minor}' if isinstance(self.minor, NumValue) else ''}{f'.{self.micro}' if isinstance(self.micro, NumValue) else ''}"
        )


@dataclass
class VersionConstraintValue(Value):
    left: VersionValue | NullValue
    right: VersionValue
    constraint: str

    @special_method("repr", 0)
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(
            f"{self.left if isinstance(self.left, VersionValue) else ''}{self.constraint}{self.right}"
        )
