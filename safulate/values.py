from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as _field
from enum import Enum
from enum import auto as _enum_auto
from typing import TYPE_CHECKING, Any, Concatenate, cast, final

from .asts import ASTNode
from .errors import (
    ErrorManager,
    SafulateAttributeError,
    SafulateInvalidReturn,
    SafulateKeyError,
    SafulateTypeError,
    SafulateValueError,
)
from .mock import MockNativeContext
from .properties import cached_property
from .tokens import Token, TokenType

if TYPE_CHECKING:
    from .native_context import NativeContext

__all__ = (
    "DictValue",
    "FuncValue",
    "ListValue",
    "NullValue",
    "NumValue",
    "ObjectValue",
    "PropertyValue",
    "StrValue",
    "TypeValue",
    "Value",
    "ValueTypeEnum",
    "VersionConstraintValue",
    "VersionValue",
    "null",
)


def __method_deco[T: Callable[Concatenate[Any, NativeContext, ...], "Value"]](
    char: str, is_prop: bool
) -> Callable[[str], Callable[[T], T]]:
    def deco(name: str) -> Callable[[T], T]:
        def decorator(func: T) -> T:
            setattr(func, "__safulate_native_method__", (char, name, is_prop))
            return func

        return decorator

    return deco


public_method = __method_deco("", is_prop=False)
private_method = __method_deco("$", is_prop=False)
special_method = __method_deco("%", is_prop=False)
public_property = __method_deco("", is_prop=True)
private_property = __method_deco("$", is_prop=True)


class ValueTypeEnum(Enum):
    str = _enum_auto()
    obj = _enum_auto()
    null = _enum_auto()
    num = _enum_auto()
    list = _enum_auto()
    func = _enum_auto()
    version = _enum_auto()
    version_constraint = _enum_auto()
    type = _enum_auto()
    dict = _enum_auto()
    property = _enum_auto()


class Value(ABC):
    __safulate_public_attrs__: dict[str, Value] | None = None
    __safulate_private_attrs__: dict[str, Value] | None = (
        None  # __safulate_private_method_info__
    )
    __safulate_specs__: dict[str, Value] | None = (
        None  # __safulate_special_method_info__
    )
    type: ValueTypeEnum

    def __init_subclass__(cls, type: ValueTypeEnum) -> None:
        cls.type = type

    @cached_property
    def _attrs(self) -> defaultdict[str, dict[str, FuncValue | PropertyValue]]:
        data: defaultdict[str, dict[str, FuncValue | PropertyValue]] = defaultdict(dict)
        for name, _ in inspect.getmembers(
            self.__class__, lambda attr: hasattr(attr, "__safulate_native_method__")
        ):
            value = getattr(self, name)

            type_, func_name, is_prop = getattr(value, "__safulate_native_method__")
            func = FuncValue.from_native(name, value)
            data[type_][func_name] = PropertyValue(func) if is_prop else func
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

    @private_method("$get_specs")
    def get_specs(self, ctx: NativeContext) -> Value:
        return ObjectValue(f"{self}'s specs", self.specs.copy())

    @special_method("add")
    def add(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Add is not defined for this type")

    @special_method("sub")
    def sub(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Subtract is not defined for this type")

    @special_method("mul")
    def mul(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Multiply is not defined for this type")

    @special_method("div")
    def div(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Divide is not defined for this type")

    @special_method("pow")
    def pow(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Exponentiation is not defined for this type")

    @special_method("uadd")
    def uadd(self, ctx: NativeContext) -> Value:
        raise SafulateValueError("Unary add is not defined for this type")

    @special_method("neg")
    def neg(self, ctx: NativeContext) -> Value:
        raise SafulateValueError("Unary minus is not defined for this type")

    @special_method("eq")
    def eq(self, ctx: NativeContext, other: Value) -> Value:
        return NumValue(int(self == other))

    @special_method("neq")
    def neq(self, ctx: NativeContext, other: Value) -> Value:
        val = ctx.invoke_spec(self, "eq", other)
        if not isinstance(val, NumValue):
            raise SafulateValueError(f"equality spec returned {val!r}, expected number")
        return NumValue(not val.value)

    @special_method("has_item")
    def has_item(self, ctx: NativeContext, other: Value) -> Value:
        val = ctx.invoke_spec(self, "iter")
        if not isinstance(val, ListValue):
            raise SafulateValueError(f"iter spec returned {val!r}, expected list")
        return NumValue(other in val.value)

    @special_method("less")
    def less(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Less than is not defined for this type")

    @special_method("grtr")
    def grtr(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Greater than is not defined for this type")

    @special_method("lesseq")
    def lesseq(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Less than or equal to is not defined for this type")

    @special_method("grtreq")
    def grtreq(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError(
            "Greater than or equal to is not defined for this type"
        )

    @special_method("and")
    def and_(self, ctx: NativeContext, other: Value) -> Value:
        return NumValue(int(self.bool_spec(ctx) and other.bool_spec(ctx)))

    @special_method("or")
    def or_(self, ctx: NativeContext, other: Value) -> Value:
        return self if self.bool_spec(ctx) else other

    @special_method("not")
    def not_(self, ctx: NativeContext) -> Value:
        return NumValue(0) if self.bool_spec(ctx) else NumValue(1)

    @special_method("bool")
    def bool(self, ctx: NativeContext) -> Value:
        return NumValue(1)

    @special_method("call")
    def call(self, ctx: NativeContext, *args: Value) -> Value:
        raise SafulateValueError("Cannot call this type")

    if TYPE_CHECKING:
        subscript = Callable[Concatenate[Any, NativeContext, ...], "Value"]
    else:

        @special_method("subscript")
        def subscript(self, ctx: NativeContext, args: ListValue) -> Value:
            raise SafulateValueError("Cannot subscript this type")

    @special_method("iter")
    def iter(self, ctx: NativeContext) -> ListValue:
        raise SafulateValueError("This type is not iterable")

    @special_method("get")
    def get_spec(self, ctx: NativeContext) -> Value:
        return self

    @special_method("repr")
    @abstractmethod
    def repr(self, ctx: NativeContext) -> Value: ...

    @special_method("str")
    def str(self, ctx: NativeContext) -> Value:
        return ctx.invoke_spec(self, "repr")

    @special_method("format")
    def format(self, ctx: NativeContext, val: Value) -> Value:
        raise SafulateValueError(f"Unknown format type {val.repr_spec(ctx)}")

    @final
    def truthy(self) -> bool:
        return self.bool_spec()

    @final
    def __str__(self) -> str:
        return self.str_spec()

    def __repr__(self) -> str:
        return self.repr_spec()

    def run_spec[T: Value](
        self, spec_name: str, return_value: type[T], ctx: NativeContext
    ) -> T:
        value = ctx.invoke_spec(self, spec_name)
        if not isinstance(value, return_value):
            raise SafulateValueError(
                f"expected return for {spec_name!r} is str, not {value!r}", ctx.token
            )

        return value

    def repr_spec(self, ctx: NativeContext = MockNativeContext()) -> str:
        return self.run_spec("repr", StrValue, ctx).value

    def str_spec(self, ctx: NativeContext = MockNativeContext()) -> str:
        return self.run_spec("str", StrValue, ctx).value

    def bool_spec(self, ctx: NativeContext = MockNativeContext()) -> bool:
        val = self.run_spec("bool", NumValue, ctx)
        if int(val.value) not in (1, 0):
            raise SafulateValueError(
                f"expected return for bool spec to be 1 or 0, got {val!r} instead"
            )
        return bool(val.value)

    @abstractmethod
    def __hash__(self) -> int: ...


@dataclass(repr=False)
class TypeValue(Value, type=ValueTypeEnum.type):
    enum: ValueTypeEnum

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<type {self.enum.name}>")

    @public_method("check")
    def check(self, ctx: NativeContext, obj: Value) -> NumValue:
        return NumValue(int(obj.type is self.enum))

    def __hash__(self) -> int:
        return hash(self.enum)


@dataclass(repr=False)
class ObjectValue(Value, type=ValueTypeEnum.obj):
    name: str
    attrs: dict[str, Value] = _field(default_factory=dict)

    def __post_init__(self) -> None:
        self.public_attrs.update(self.attrs)

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<{self.name}>")

    def __hash__(self) -> int:
        return hash(id(self))


class NullValue(Value, type=ValueTypeEnum.null):
    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue("null")

    @special_method("eq")
    def eq(self, ctx: NativeContext, other: Value) -> Value:
        return NumValue(isinstance(other, NullValue))

    @special_method("bool")
    def bool(self, ctx: NativeContext) -> Value:
        return NumValue(0)

    def __hash__(self) -> int:
        return hash(id(self))


@dataclass(repr=False)
class NumValue(Value, type=ValueTypeEnum.num):
    value: float

    @special_method("add")
    def add(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Add is not defined for number and this type")

        return NumValue(self.value + other.value)

    @special_method("sub")
    def sub(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Subtract is not defined for number and this type")

        return NumValue(self.value - other.value)

    @special_method("mul")
    def mul(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Multiply is not defined for number and this type")

        return NumValue(self.value * other.value)

    @special_method("div")
    def div(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Divide is not defined for number and this type")
        return NumValue(self.value / other.value)

    @special_method("pow")
    def pow(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Exponentiation is not defined for number and this type"
            )

        return NumValue(self.value**other.value)

    @special_method("uadd")
    def uadd(self, ctx: NativeContext) -> NumValue:
        return NumValue(self.value)

    @special_method("neg")
    def neg(self, ctx: NativeContext) -> NumValue:
        return NumValue(-self.value)

    @special_method("eq")
    def eq(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Equality is not defined for number and this type")

        return NumValue(self.value == other.value)

    @special_method("neq")
    def neq(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Non-equality is not defined for number and this type"
            )

        return NumValue(self.value != other.value)

    @special_method("less")
    def less(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Less than is not defined for number and this type"
            )

        return NumValue(self.value < other.value)

    @special_method("grtr")
    def grtr(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Greater than is not defined for number and this type"
            )

        return NumValue(self.value > other.value)

    @special_method("lesseq")
    def lesseq(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Less than or equal to is not defined for number and this type"
            )

        return NumValue(self.value <= other.value)

    @special_method("grtreq")
    def grtreq(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Greater than or equal to is not defined for number and this type",
            )

        return NumValue(self.value >= other.value)

    @special_method("bool")
    def bool(self, ctx: NativeContext) -> NumValue:
        return NumValue(int(self.value != 0))

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        if self.value % 1 == 0 and "e" not in str(self.value):
            return StrValue(str(int(self.value)))

        return StrValue(str(self.value))

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(repr=False)
class StrValue(Value, type=ValueTypeEnum.str):
    value: str

    def __post_init__(self) -> None:
        self.value = self.value.encode("ascii").decode("unicode_escape")

    @special_method("subscript")
    def subscript(self, ctx: NativeContext, idx: Value) -> StrValue:
        if not isinstance(idx, NumValue):
            raise SafulateTypeError(f"Expected num, got {idx.repr_spec(ctx)} instead")

        return StrValue(self.value[int(idx.value)])

    @special_method("add")
    def add(self, ctx: NativeContext, other: Value) -> StrValue:
        if not isinstance(other, StrValue):
            other = ctx.invoke_spec(other, "str")
        if not isinstance(other, StrValue):
            raise SafulateValueError(f"{other!r} could not be converted into a string")

        return StrValue(self.value + other.value)

    @special_method("mul")
    def mul(self, ctx: NativeContext, other: Value) -> StrValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Multiply is not defined for string and this type")

        if other.value % 1 != 0:
            raise SafulateValueError(
                "Cannot multiply string by a float, must be integer"
            )

        return StrValue(self.value * int(other.value))

    @special_method("iter")
    def iter(self, ctx: NativeContext) -> ListValue:
        return ListValue([StrValue(char) for char in self.value])

    @special_method("bool")
    def bool(self, ctx: NativeContext) -> NumValue:
        return NumValue(int(len(self.value) != 0))

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(repr(self.value))

    @special_method("str")
    def str(self, ctx: NativeContext) -> StrValue:
        return StrValue(self.value)

    @special_method("eq")
    def eq(self, ctx: NativeContext, other: Value) -> Value:
        return NumValue(isinstance(other, StrValue) and other.value == self.value)

    @public_method("format")
    def format_(self, ctx: NativeContext, *args: Value) -> Value:
        val = self.value
        for arg in args:
            if not isinstance(arg, StrValue):
                raise SafulateTypeError("Format can only accept str values")

            val = val.replace("{}", arg.value, 1)

        return StrValue(val)

    @public_method("capitalize")
    def capitalize(self, ctx: NativeContext) -> Value:
        return StrValue(self.value.capitalize())

    @public_method("title")
    def title(self, ctx: NativeContext) -> Value:
        return StrValue(self.value.title())

    @public_method("upper")
    def upper(self, ctx: NativeContext) -> Value:
        return StrValue(self.value.upper())

    @public_method("casefold")
    def casefold(self, ctx: NativeContext) -> Value:
        return StrValue(self.value.casefold())

    @public_method("count")
    def count(
        self,
        ctx: NativeContext,
        char: Value,
        start: Value = NumValue(0),
        end: Value = NumValue(-1),
    ) -> Value:
        if not isinstance(char, StrValue):
            raise SafulateTypeError(
                f"Expected str for char, received {char.repr_spec(ctx)} instead"
            )
        if not isinstance(start, NumValue):
            raise SafulateTypeError(
                f"Expected num for start, received {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, NumValue):
            raise SafulateTypeError(
                f"Expected num for end, received {end.repr_spec(ctx)} instead"
            )
        return NumValue(self.value.count(char.value, int(start.value), int(end.value)))

    @public_method("endswith")
    def casendswithefold(self, ctx: NativeContext, sub: Value) -> Value:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return NumValue(int(self.value.endswith(sub.value)))

    @public_method("index")
    def index(self, ctx: NativeContext, sub: Value) -> Value:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return NumValue(int(self.value.index(sub.value)))

    @public_method("is_alnum")
    def isalnum(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.isalnum()))

    @public_method("is_alpha")
    def isalpha(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.isalpha()))

    @public_method("is_ascii")
    def isascii(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.isascii()))

    @public_method("is_decimal")
    def isdecimal(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.isdecimal()))

    @public_method("is_digit")
    def isdigit(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.isdigit()))

    @public_method("is_lower")
    def islower(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.islower()))

    @public_method("is_numeric")
    def isnumeric(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.isnumeric()))

    @public_method("is_space")
    def isspace(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.isspace()))

    @public_method("is_title")
    def istitle(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.istitle()))

    @public_method("is_upper")
    def isupper(self, ctx: NativeContext) -> Value:
        return NumValue(int(self.value.isupper()))

    @public_method("lower")
    def lower(self, ctx: NativeContext) -> Value:
        return StrValue(self.value.lower())

    @public_method("replace")
    def replace(
        self,
        ctx: NativeContext,
        before: Value,
        after: Value,
        count: Value = NumValue(-1),
    ) -> Value:
        if not isinstance(before, StrValue):
            raise SafulateTypeError(
                f"Expected str for before, received {before.repr_spec(ctx)} instead"
            )
        if not isinstance(after, StrValue):
            raise SafulateTypeError(
                f"Expected str for after, received {after.repr_spec(ctx)} instead"
            )
        if not isinstance(count, (NumValue)):
            raise SafulateTypeError(
                f"Expected int for cont, received {count.repr_spec(ctx)} instead"
            )
        return StrValue(
            self.value.replace(before.value, after.value, count=int(count.value))
        )

    @public_method("remove_prefix")
    def remove_prefix(self, ctx: NativeContext, prefix: Value) -> Value:
        if not isinstance(prefix, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {prefix.repr_spec(ctx)} instead"
            )
        return StrValue(self.value.removeprefix(prefix.value))

    @public_method("remove_suffix")
    def remove_suffix(self, ctx: NativeContext, suffix: Value) -> Value:
        if not isinstance(suffix, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {suffix.repr_spec(ctx)} instead"
            )
        return StrValue(self.value.removesuffix(suffix.value))

    @public_method("strip")
    def strip(self, ctx: NativeContext, sub: Value) -> Value:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return StrValue(self.value.strip(sub.value))

    @public_method("lstrip")
    def lstrip(self, ctx: NativeContext, sub: Value) -> Value:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return StrValue(self.value.lstrip(sub.value))

    @public_method("rstrip")
    def rstrip(self, ctx: NativeContext, sub: Value) -> Value:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return StrValue(self.value.rstrip(sub.value))

    @public_method("split")
    def split(self, ctx: NativeContext, delimiter: Value) -> Value:
        if not isinstance(delimiter, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {delimiter.repr_spec(ctx)} instead"
            )
        return ListValue([StrValue(part) for part in self.value.split(delimiter.value)])

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(repr=False)
class ListValue(Value, type=ValueTypeEnum.list):
    value: list[Value]

    @public_method("append")
    def append(self, ctx: NativeContext, item: Value) -> Value:
        self.value.append(item)
        return null

    @public_method("remove")
    def remove(self, ctx: NativeContext, item: Value) -> Value:
        self.value.remove(item)
        return null

    @public_method("pop")
    def pop(self, ctx: NativeContext, index: Value) -> Value:
        if not isinstance(index, NumValue):
            raise SafulateTypeError(f"expected num, got {index!r} instead")
        if abs(index.value) > len(self.value):
            return null

        return self.value.pop(int(index.value))

    @special_method("bool")
    def bool(self, ctx: NativeContext) -> NumValue:
        return NumValue(int(len(self.value) != 0))

    @special_method("subscript")
    def subscript(self, ctx: NativeContext, idx: Value) -> Value:
        if not isinstance(idx, NumValue):
            raise SafulateTypeError(f"Expected num, got {idx.repr_spec(ctx)} instead.")

        return self.value[int(idx.value)]

    @special_method("iter")
    def iter(self, ctx: NativeContext) -> ListValue:
        return self

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(
            "["
            + ", ".join(
                [
                    cast("StrValue", ctx.invoke_spec(val, "repr")).value
                    for val in self.value
                ]
            )
            + "]"
        )

    @public_property("len")
    def len(self, ctx: NativeContext) -> NumValue:
        return NumValue(len(self.value))

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(repr=False)
class FuncValue(Value, type=ValueTypeEnum.func):
    name: Token
    params: list[tuple[Token, ASTNode | Value | None]] | None
    body: ASTNode | Callable[Concatenate[NativeContext, ...], Value]
    parent: Value = _field(default_factory=lambda: null)

    def __hash__(self) -> int:
        return hash([self.params, self.body, self.parent])

    @cached_property
    def required_args(self) -> list[tuple[Token, None]]:
        if not self.params:
            return []
        return [(arg, default) for arg, default in self.params if default is None]

    def _validate_params(
        self, ctx: NativeContext, args: tuple[Value, ...], kwargs: dict[str, Value]
    ) -> dict[str, Value]:
        if self.params is None:
            if kwargs:
                raise SafulateValueError(
                    f"Function {self.name.lexeme!r} does not support keyword arguments",
                )
            return {}
        params = self.params.copy()
        passable_params: dict[str, Value] = {}

        for arg in args:
            (param, _default) = params.pop(0)
            passable_params[param.lexeme] = arg

        for kwarg, value in kwargs.items():
            param = [p for p in params if p[0].lexeme == kwarg]
            if not param:
                raise SafulateValueError(
                    f"Unknown Keyword argument {kwarg!r}",
                )

            params.remove(param[0])
            passable_params[kwarg] = value

        for param, default in params:
            if default is None:
                raise SafulateValueError(
                    f"Required argument {param.lexeme!r} was not passed",
                )
            passable_params[param.lexeme] = (
                default.accept(ctx.interpreter)
                if isinstance(default, ASTNode)
                else default
            )

        return passable_params

    @special_method("call")
    def call(self, ctx: NativeContext, *args: Value, **kwargs: Value) -> Value:
        params = self._validate_params(ctx, args, kwargs)

        if isinstance(self.body, Callable):
            with ErrorManager(token=lambda: ctx.token):
                return self.body(ctx, *args, **kwargs)

        ret_value = null
        with ctx.interpreter.scope():
            ctx.interpreter.env["parent"] = self.parent
            if self.parent:
                ctx.interpreter.env.values.update(self.parent.private_attrs)

            for param, value in params.items():
                ctx.interpreter.env.declare(param)
                ctx.interpreter.env[param] = value

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

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<func {self.name.lexeme!r}>")

    @classmethod
    def from_native(
        cls, name: str, callback: Callable[Concatenate[NativeContext, ...], Value]
    ) -> FuncValue:
        params = list(inspect.signature(callback).parameters.values())

        return FuncValue(
            name=Token(TokenType.ID, name, -1),
            params=None
            if len(params) > 1 and params[1].kind is params[1].VAR_POSITIONAL
            else [
                (
                    Token(TokenType.ID, param.name, -1),
                    None if param.default is param.empty else param.default,
                )
                for param in params
            ][1:],
            body=callback,
        )


@dataclass(repr=False)
class VersionValue(Value, type=ValueTypeEnum.version):
    major: NumValue
    minor: NumValue | NullValue
    micro: NumValue | NullValue

    def __hash__(self) -> int:
        return hash([self.major, self.minor, self.micro])

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

    @special_method("sub")
    def sub(self, ctx: NativeContext, other: Value) -> Value:
        return self._handle_constraint(other, "-")

    @special_method("uadd")
    def uadd(self, ctx: NativeContext) -> Value:
        return self._handle_constraint(null, "+")

    @special_method("neg")
    def neg(self, ctx: NativeContext) -> Value:
        return self._handle_constraint(null, "-")

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(
            f"v{self.major}{f'.{self.minor}' if isinstance(self.minor, NumValue) else ''}{f'.{self.micro}' if isinstance(self.micro, NumValue) else ''}"
        )


@dataclass(repr=False)
class VersionConstraintValue(Value, type=ValueTypeEnum.version_constraint):
    left: VersionValue | NullValue
    right: VersionValue
    constraint: str

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(
            f"{self.left if isinstance(self.left, VersionValue) else ''}{self.constraint}{self.right}"
        )

    def __hash__(self) -> int:
        return hash([self.left, self.right, self.constraint])


MISSING: Any = object()
null = NullValue()


@dataclass(repr=False)
class DictValue(Value, type=ValueTypeEnum.dict):
    data: dict[Value, Value]

    def __hash__(self) -> int:
        return hash(self.data)

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(
            "{"
            + ", ".join(
                f"{key.repr_spec(ctx)}:{value.repr_spec(ctx)}"
                for key, value in self.data.items()
            )
            + "}"
        )

    @special_method("subscript")
    def subscript(
        self, ctx: NativeContext, key: Value, default: Value = MISSING
    ) -> Value:
        return self.get(ctx, key, default)

    @public_method("get")
    def get(self, ctx: NativeContext, key: Value, default: Value = null) -> Value:
        try:
            return self.data[key]
        except KeyError:
            if default is MISSING:
                raise SafulateKeyError(f"Key {key!r} was not found")
            return default

    @public_method("set")
    def set(self, ctx: NativeContext, key: Value, value: Value) -> Value:
        self.data[key] = value
        return value

    @public_method("keys")
    def keys(self, ctx: NativeContext) -> ListValue:
        return ListValue(list(self.data.keys()))

    @public_method("values")
    def values(self, ctx: NativeContext) -> ListValue:
        return ListValue(list(self.data.values()))

    @public_method("items")
    def items(self, ctx: NativeContext) -> ListValue:
        return ListValue([ListValue([key, value]) for key, value in self.data.items()])

    @public_method("pop")
    def pop(
        self, ctx: NativeContext, key: Value, default: Value | None = None
    ) -> Value:
        try:
            return self.data.pop(key)
        except KeyError:
            if default is None:
                raise SafulateKeyError(f"Key {key!r} was not found")
            return default

    @special_method("iter")
    def iter(self, ctx: NativeContext) -> ListValue:
        return self.keys(ctx)

    @special_method("has")
    def has(self, ctx: NativeContext, key: Value) -> NumValue:
        return NumValue(int(key in self.data))

    @special_method("bool")
    def bool(self, ctx: NativeContext) -> NumValue:
        return NumValue(1 if self.data else 0)


class PropertyValue(Value, type=ValueTypeEnum.property):
    def __init__(self, func: FuncValue) -> None:
        self.func = func

    @special_method("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<Property {self.func.repr_spec(ctx)}>")

    def __hash__(self) -> int:
        return hash((f"property-{id(self)}", self.func))

    @special_method("get")
    def get_spec(self, ctx: NativeContext) -> Value:
        return ctx.invoke(self.func)
