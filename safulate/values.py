from __future__ import annotations

import inspect
import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Concatenate, TypeVar, cast, final

from .asts import ASTBlock, ASTFuncDecl_Param, ASTFuncDecl_ParamType
from .errors import (
    SafulateAttributeError,
    SafulateIndexError,
    SafulateInvalidReturn,
    SafulateKeyError,
    SafulateTypeError,
    SafulateValueError,
)
from .properties import cached_property
from .tokens import Token, TokenType

if TYPE_CHECKING:
    import re

    from .native_context import NativeContext

ValueT = TypeVar("ValueT")
NativeMethodT = TypeVar(
    "NativeMethodT", bound=Callable[Concatenate[Any, "NativeContext", ...], "Value"]
)

__all__ = (
    "DictValue",
    "FuncValue",
    "ListValue",
    "MatchValue",
    "NativeErrorValue",
    "NullValue",
    "NumValue",
    "ObjectValue",
    "PatternValue",
    "PropertyValue",
    "StrValue",
    "TypeValue",
    "Value",
    "false",
    "null",
    "private_method",
    "private_property",
    "public_method",
    "public_property",
    "spec_meth",
    "spec_prop",
    "true",
)


def __method_deco(
    char: str, is_prop: bool
) -> Callable[[str], Callable[[NativeMethodT], NativeMethodT]]:
    def deco(name: str) -> Callable[[NativeMethodT], NativeMethodT]:
        def decorator(func: NativeMethodT) -> NativeMethodT:
            setattr(func, "__safulate_native_method__", (char, name, is_prop))
            return func

        return decorator

    return deco


public_method = __method_deco("", is_prop=False)
public_property = __method_deco("", is_prop=True)
private_method = __method_deco("$", is_prop=False)
private_property = __method_deco("$", is_prop=True)
spec_meth = __method_deco("%", is_prop=False)
spec_prop = __method_deco("%", is_prop=True)

# region Base


class Value(ABC):
    __safulate_public_attrs__: dict[str, Value] | None = None
    __safulate_private_attrs__: dict[str, Value] | None = None
    __safulate_specs__: dict[str, Value] | None = None

    def _attrs_hook(self, attrs: defaultdict[str, dict[str, Value]]) -> None:
        return

    @cached_property
    def _attrs(self) -> defaultdict[str, dict[str, Value]]:
        data: defaultdict[str, dict[str, Value]] = defaultdict(dict)
        for name, _ in inspect.getmembers(
            self.__class__, lambda attr: hasattr(attr, "__safulate_native_method__")
        ):
            value = getattr(self, name)

            type_, func_name, is_prop = getattr(value, "__safulate_native_method__")
            func = FuncValue.from_native(name, value)
            data[type_][func_name] = PropertyValue(func) if is_prop else func
        self._attrs_hook(data)
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

    @private_method("get_specs")
    def get_specs(self, ctx: NativeContext) -> Value:
        return DictValue(self.specs.copy())

    @spec_meth("add")
    def add(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Add is not defined for this type")

    @spec_meth("sub")
    def sub(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Subtract is not defined for this type")

    @spec_meth("mul")
    def mul(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Multiply is not defined for this type")

    @spec_meth("div")
    def div(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Divide is not defined for this type")

    @spec_meth("pow")
    def pow(self, ctx: NativeContext, _other: Value) -> Value:
        raise SafulateValueError("Exponentiation is not defined for this type")

    @spec_meth("uadd")
    def uadd(self, ctx: NativeContext) -> Value:
        raise SafulateValueError("Unary add is not defined for this type")

    @spec_meth("neg")
    def neg(self, ctx: NativeContext) -> Value:
        raise SafulateValueError("Unary minus is not defined for this type")

    @spec_meth("eq")
    def eq(self, ctx: NativeContext, other: Value) -> BoolValue:
        return BoolValue(self == other)

    @spec_meth("neq")
    def neq(self, ctx: NativeContext, other: Value) -> BoolValue:
        val = ctx.invoke_spec(self, "eq", other).bool_spec(ctx)
        return BoolValue(not val)

    @spec_meth("has_item")
    def has_item(self, ctx: NativeContext, other: Value) -> BoolValue:
        val = ctx.invoke_spec(self, "iter")
        if not isinstance(val, ListValue):
            raise SafulateValueError(
                f"iter spec returned {val.repr_spec(ctx)}, expected list"
            )
        return BoolValue(other in val.value)

    @spec_meth("less")
    def less(self, ctx: NativeContext, _other: Value) -> BoolValue:
        raise SafulateValueError("Less than is not defined for this type")

    @spec_meth("grtr")
    def grtr(self, ctx: NativeContext, _other: Value) -> BoolValue:
        raise SafulateValueError("Greater than is not defined for this type")

    @spec_meth("lesseq")
    def lesseq(self, ctx: NativeContext, _other: Value) -> BoolValue:
        raise SafulateValueError("Less than or equal to is not defined for this type")

    @spec_meth("grtreq")
    def grtreq(self, ctx: NativeContext, _other: Value) -> BoolValue:
        raise SafulateValueError(
            "Greater than or equal to is not defined for this type"
        )

    @spec_meth("amp")
    def amp(self, ctx: NativeContext, other: Value) -> Value:
        raise SafulateValueError("amp is not defined for this type")

    @spec_meth("pipe")
    def pipe(self, ctx: NativeContext, other: Value) -> Value:
        raise SafulateValueError("pipe is not defined for this type")

    @spec_meth("not")
    def not_(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.bool_spec(ctx))

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> BoolValue:
        return true

    if TYPE_CHECKING:
        altcall: Callable[Concatenate[Any, NativeContext, ...], Value]
        call: Callable[Concatenate[Any, NativeContext, ...], Value]
    else:

        @spec_meth("altcall")
        def altcall(self, ctx: NativeContext, *args: Value, **kwargs: Value) -> Value:
            raise SafulateValueError("Cannot altcall this type")

        @spec_meth("call")
        def call(self, ctx: NativeContext, *args: Value, **kwargs: Value) -> Value:
            raise SafulateValueError("Cannot call this type")

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> ListValue:
        raise SafulateValueError("This type is not iterable")

    @spec_meth("get")
    def get_spec(self, ctx: NativeContext) -> Value:
        return self

    @spec_meth("repr")
    @abstractmethod
    def repr(self, ctx: NativeContext) -> Value: ...

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> Value:
        return ctx.invoke_spec(self, "repr")

    @spec_meth("format")
    def format(self, ctx: NativeContext, val: Value) -> Value:
        raise SafulateValueError(f"Unknown format type {val.repr_spec(ctx)}")

    @spec_meth("get_attr")
    def get_attr(self, ctx: NativeContext, name: Value) -> Value:
        if not isinstance(name, StrValue):
            raise SafulateValueError(f"Expected str, got {name.repr_spec(ctx)} instead")
        val = self.public_attrs.get(name.value)
        if val is None:
            raise SafulateAttributeError(f"Attribute Not Found: {name.repr_spec(ctx)}")
        return ctx.invoke_spec(val, "get")

    @final
    def __str__(self) -> str:
        raise RuntimeError("use str_spec instead")

    @final
    def __repr__(self) -> str:
        raise RuntimeError("use repr_spec instead")

    def run_spec(
        self, spec_name: str, return_value: type[ValueT], ctx: NativeContext
    ) -> ValueT:
        value = ctx.invoke_spec(self, spec_name)
        if not isinstance(value, return_value):
            raise SafulateValueError(
                f"expected return for {spec_name!r} is str, not {value.repr_spec(ctx)}",
                ctx.token,
            )

        return value

    def repr_spec(self, ctx: NativeContext) -> str:
        return self.run_spec("repr", StrValue, ctx).value

    def str_spec(self, ctx: NativeContext) -> str:
        return self.run_spec("str", StrValue, ctx).value

    def bool_spec(self, ctx: NativeContext) -> bool:
        val = self.run_spec("bool", BoolValue, ctx)
        if int(val.value) not in (1, 0):
            raise SafulateValueError(
                f"expected return for bool spec to be a bool, got {val.repr_spec(ctx)} instead"
            )
        return bool(val.value)


class TypeValue(Value):
    def __init__(self, name: str) -> None:
        self.name = name

    def _attrs_hook(self, attrs: defaultdict[str, dict[str, Value]]) -> None:
        attrs["%"]["type"] = TypeValue("type")

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<type {self.name!r}>")

    @public_method("check")
    def check(self, ctx: NativeContext, obj: Value) -> NumValue:
        obj_type = obj.specs["type"]
        return NumValue(
            1 if isinstance(obj_type, TypeValue) and obj_type.name == self.name else 0
        )


class ObjectValue(Value):
    __saf_typename__: str
    __saf_init_attrs__: dict[str, Value] | None

    def __init__(self, name: str, attrs: dict[str, Value] | None = None) -> None:
        self.__saf_typename__ = name
        self.__saf_init_attrs__ = attrs

    def _attrs_hook(self, attrs: defaultdict[str, dict[str, Value]]) -> None:
        if self.__saf_init_attrs__:
            attrs[""].update(self.__saf_init_attrs__)
        attrs["%"]["type"] = TypeValue(self.__saf_typename__)

    @property
    def type(self) -> TypeValue:
        typ = self.specs["type"]
        assert isinstance(typ, TypeValue)
        return typ

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<{self.type.name}>")


# region Atoms


class NullValue(ObjectValue):
    def __init__(self) -> None:
        super().__init__("null")

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue("null")

    @spec_meth("eq")
    def eq(self, ctx: NativeContext, other: Value) -> BoolValue:
        return BoolValue(isinstance(other, NullValue))

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> BoolValue:
        return false


class NumValue(ObjectValue):
    def __init__(self, value: float) -> None:
        super().__init__("num")

        self.value = value

    @spec_meth("add")
    def add(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Add is not defined for number and this type")

        return NumValue(self.value + other.value)

    @spec_meth("sub")
    def sub(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Subtract is not defined for number and this type")

        return NumValue(self.value - other.value)

    @spec_meth("mul")
    def mul(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Multiply is not defined for number and this type")

        return NumValue(self.value * other.value)

    @spec_meth("div")
    def div(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Divide is not defined for number and this type")
        return NumValue(self.value / other.value)

    @spec_meth("pow")
    def pow(self, ctx: NativeContext, other: Value) -> NumValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Exponentiation is not defined for number and this type"
            )

        return NumValue(self.value**other.value)

    @spec_meth("uadd")
    def uadd(self, ctx: NativeContext) -> NumValue:
        return NumValue(self.value)

    @spec_meth("neg")
    def neg(self, ctx: NativeContext) -> NumValue:
        return NumValue(-self.value)

    @spec_meth("eq")
    def eq(self, ctx: NativeContext, other: Value) -> BoolValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Equality is not defined for number and this type")

        return BoolValue(self.value == other.value)

    @spec_meth("neq")
    def neq(self, ctx: NativeContext, other: Value) -> BoolValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Non-equality is not defined for number and this type"
            )

        return BoolValue(self.value != other.value)

    @spec_meth("less")
    def less(self, ctx: NativeContext, other: Value) -> BoolValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Less than is not defined for number and this type"
            )

        return BoolValue(self.value < other.value)

    @spec_meth("grtr")
    def grtr(self, ctx: NativeContext, other: Value) -> BoolValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Greater than is not defined for number and this type"
            )

        return BoolValue(self.value > other.value)

    @spec_meth("lesseq")
    def lesseq(self, ctx: NativeContext, other: Value) -> BoolValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Less than or equal to is not defined for number and this type"
            )

        return BoolValue(self.value <= other.value)

    @spec_meth("grtreq")
    def grtreq(self, ctx: NativeContext, other: Value) -> BoolValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError(
                "Greater than or equal to is not defined for number and this type",
            )

        return BoolValue(self.value >= other.value)

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value != 0)

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        if self.value % 1 == 0 and "e" not in str(self.value):
            return StrValue(str(int(self.value)))

        return StrValue(str(self.value))


class BoolValue(NumValue):
    def __init__(self, status: Any) -> None:
        self.status: bool = bool(status)
        self.value = int(self.status)

        ObjectValue.__init__(self, str(self.status).lower())

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(self.type.name)

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> StrValue:
        return self.repr(ctx)

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> BoolValue:
        return self


class StrValue(ObjectValue):
    def __init__(self, value: str) -> None:
        super().__init__("str")

        self.value = value.encode("ascii").decode("unicode_escape")

    @spec_meth("altcall")
    def altcall(self, ctx: NativeContext, idx: Value) -> StrValue:
        if not isinstance(idx, NumValue):
            raise SafulateTypeError(f"Expected num, got {idx.repr_spec(ctx)} instead")

        return StrValue(self.value[int(idx.value)])

    @spec_meth("add")
    def add(self, ctx: NativeContext, other: Value) -> StrValue:
        if not isinstance(other, StrValue):
            other = ctx.invoke_spec(other, "str")
        if not isinstance(other, StrValue):
            raise SafulateValueError(
                f"{other.repr_spec(ctx)} could not be converted into a string"
            )

        return StrValue(self.value + other.value)

    @spec_meth("mul")
    def mul(self, ctx: NativeContext, other: Value) -> StrValue:
        if not isinstance(other, NumValue):
            raise SafulateValueError("Multiply is not defined for string and this type")

        if other.value % 1 != 0:
            raise SafulateValueError(
                "Cannot multiply string by a float, must be integer"
            )

        return StrValue(self.value * int(other.value))

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> ListValue:
        return ListValue([StrValue(char) for char in self.value])

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(len(self.value) != 0)

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(repr(self.value))

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> StrValue:
        return StrValue(self.value)

    @spec_meth("eq")
    def eq(self, ctx: NativeContext, other: Value) -> BoolValue:
        return BoolValue(isinstance(other, StrValue) and other.value == self.value)

    @public_method("format")
    def format_(self, ctx: NativeContext, *args: Value) -> Value:
        val = self.value
        for arg in args:
            if not isinstance(arg, StrValue):
                raise SafulateTypeError("Format can only visit str values")

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
    def casendswithefold(self, ctx: NativeContext, sub: Value) -> BoolValue:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return BoolValue(self.value.endswith(sub.value))

    @public_method("index")
    def index(self, ctx: NativeContext, sub: Value) -> Value:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return NumValue(int(self.value.index(sub.value)))

    @public_method("is_alnum")
    def isalnum(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.isalnum())

    @public_method("is_alpha")
    def isalpha(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.isalpha())

    @public_method("is_ascii")
    def isascii(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.isascii())

    @public_method("is_decimal")
    def isdecimal(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.isdecimal())

    @public_method("is_digit")
    def isdigit(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.isdigit())

    @public_method("is_lower")
    def islower(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.islower())

    @public_method("is_numeric")
    def isnumeric(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.isnumeric())

    @public_method("is_space")
    def isspace(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.isspace())

    @public_method("is_title")
    def istitle(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.istitle())

    @public_method("is_upper")
    def isupper(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.value.isupper())

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
        return StrValue(self.value.replace(before.value, after.value, int(count.value)))

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


# region Structures


class ListValue(ObjectValue):
    def __init__(self, value: list[Value]) -> None:
        super().__init__("list")

        self.value = value

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
            raise SafulateTypeError(f"expected num, got {index.repr_spec(ctx)} instead")
        if abs(index.value) > len(self.value):
            return null

        return self.value.pop(int(index.value))

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(len(self.value) != 0)

    @spec_meth("altcall")
    def altcall(self, ctx: NativeContext, idx: Value) -> Value:
        if not isinstance(idx, NumValue):
            raise SafulateTypeError(f"Expected num, got {idx.repr_spec(ctx)} instead.")

        try:
            return self.value[int(idx.value)]
        except IndexError:
            raise SafulateIndexError(f"Index {idx.repr_spec(ctx)} is out of range")

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> ListValue:
        return self

    @spec_meth("repr")
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


class FuncValue(ObjectValue):
    def __init__(
        self,
        name: Token | None,
        params: list[ASTFuncDecl_Param],
        body: ASTBlock | Callable[Concatenate[NativeContext, ...], Value],
        parent: Value | None = None,
        extra_vars: dict[str, Value] | None = None,
        partial_args: tuple[Value, ...] | None = None,
        partial_kwargs: dict[str, Value] | None = None,
    ) -> None:
        super().__init__("func")

        self.name = name
        self.params = params
        self.body = body
        self.parent = parent
        self.extra_vars = extra_vars or {}
        self.partial_args = partial_args or ()
        self.partial_kwargs = partial_kwargs or {}

    def _validate_params(
        self, ctx: NativeContext, *init_args: Value, **kwargs: Value
    ) -> dict[str, Value]:
        params = self.params.copy()
        args = list(init_args)
        passable_params: dict[str, Value] = {}

        for param in params:
            if param.type is ASTFuncDecl_ParamType.vararg:
                passable_params[param.name.lexeme] = ListValue(args)
                args = []
            elif param.type is ASTFuncDecl_ParamType.varkwarg:
                passable_params[param.name.lexeme] = DictValue(kwargs)
                kwargs = {}
            elif args:
                if not param.is_arg:
                    raise SafulateValueError(
                        f"Extra positional argument was passed: {args[0].repr_spec(ctx)}"
                    )
                arg = args.pop(0)
                passable_params[param.name.lexeme] = arg
            elif kwargs:
                if not param.is_kwarg:
                    if param.default is None:
                        raise SafulateValueError(
                            f"Required positional argument was not passed: {param.name.lexeme!r}"
                        )
                    passable_params[param.name.lexeme] = (
                        param.default
                        if isinstance(param.default, Value)
                        else param.default.visit(ctx.interpreter)
                    )
                else:
                    if param.name.lexeme not in kwargs:
                        if param.default is None:
                            arg_type = {
                                ASTFuncDecl_ParamType.kwarg: "keyword ",
                                ASTFuncDecl_ParamType.arg: "positional ",
                            }.get(param.type, "")
                            raise SafulateValueError(
                                f"Required {arg_type}argument was not passed: {param.name.lexeme!r}"
                            )
                        else:
                            passable_params[param.name.lexeme] = (
                                param.default
                                if isinstance(param.default, Value)
                                else param.default.visit(ctx.interpreter)
                            )
                    else:
                        passable_params[param.name.lexeme] = kwargs.pop(
                            param.name.lexeme
                        )
            else:
                if param.default is None:
                    arg_type = {
                        ASTFuncDecl_ParamType.kwarg: "keyword ",
                        ASTFuncDecl_ParamType.arg: "positional ",
                    }.get(param.type, "")
                    raise SafulateValueError(
                        f"Required {arg_type}argument was not passed: {param.name.lexeme!r}"
                    )
                passable_params[param.name.lexeme] = (
                    param.default
                    if isinstance(param.default, Value)
                    else param.default.visit(ctx.interpreter)
                )

        if args:
            raise SafulateValueError(
                f"Received {len(args)} extra positional argument(s)."
            )
        if kwargs:
            raise SafulateValueError(
                f"Recieved {len(kwargs)} extra keyword argument(s): {', '.join(kwargs.keys())}"
            )
        return passable_params

    @spec_meth("altcall")
    def altcall(self, ctx: NativeContext, *args: Value, **kwargs: Value) -> Value:
        if ctx.token.lexeme == "ADD-TO-START":
            args = (*args, *self.partial_args)
        else:
            args = (*self.partial_args, *args)

        return FuncValue(
            name=self.name,
            params=self.params,
            body=self.body,
            parent=self.parent,
            extra_vars=self.extra_vars,
            partial_args=args,
            partial_kwargs=self.partial_kwargs | kwargs,
        )

    @spec_meth("call")
    def call(self, ctx: NativeContext, *args: Value, **kwargs: Value) -> Value:
        params = self._validate_params(
            ctx,
            *self.partial_args,
            *args,
            **self.partial_kwargs,
            **kwargs,
        )

        if isinstance(self.body, Callable):
            return self.body(ctx, *args, **kwargs)

        ret_value = null
        with ctx.interpreter.scope(source=self.parent):
            ctx.interpreter.env["parent"] = self.parent or null

            for param, value in [*params.items(), *self.extra_vars.items()]:
                ctx.interpreter.env.declare(param)
                ctx.interpreter.env[param] = value

            try:
                self.body.visit_unscoped(ctx.interpreter)
            except SafulateInvalidReturn as r:
                ret_value = r.value

        return ret_value

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        suffix = f" {self.name.lexeme!r}" if self.name else ""
        return StrValue(f"<func{suffix}>")

    @classmethod
    def from_native(
        cls, name: str, callback: Callable[Concatenate[NativeContext, ...], Value]
    ) -> FuncValue:
        raw_params = list(inspect.signature(callback).parameters.values())

        return FuncValue(
            name=Token(TokenType.ID, name, -1),
            params=[
                ASTFuncDecl_Param(
                    name=Token(TokenType.ID, param.name, -1),
                    default=None if param.default is param.empty else param.default,
                    type={
                        param.VAR_POSITIONAL: ASTFuncDecl_ParamType.vararg,
                        param.VAR_KEYWORD: ASTFuncDecl_ParamType.varkwarg,
                        param.POSITIONAL_ONLY: ASTFuncDecl_ParamType.arg,
                        param.KEYWORD_ONLY: ASTFuncDecl_ParamType.kwarg,
                        param.POSITIONAL_OR_KEYWORD: ASTFuncDecl_ParamType.arg_or_kwarg,
                    }[param.kind],
                )
                for param in raw_params
            ][1:],
            body=callback,
        )


class PropertyValue(ObjectValue):
    def __init__(self, func: FuncValue) -> None:
        super().__init__("property")

        self.func = func

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<property {self.func.repr_spec(ctx)}>")

    @spec_meth("get")
    def get_spec(self, ctx: NativeContext) -> Value:
        return ctx.invoke(self.func)

    @public_property("func")
    def func_prop(self, ctx: NativeContext) -> Value:
        return self.func


MISSING: Any = object()
null = NullValue()
true = BoolValue(True)
false = BoolValue(False)


class DictValue(ObjectValue):
    def __init__(self, data: dict[str, Value]) -> None:
        super().__init__("dict")

        self.data = data

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(
            "{"
            + ", ".join(
                f"{key!r}:{value.repr_spec(ctx)}" for key, value in self.data.items()
            )
            + "}"
        )

    @spec_meth("altcall")
    def altcall(
        self, ctx: NativeContext, key: Value, default: Value = MISSING
    ) -> Value:
        return self.get(ctx, key, default)

    @public_method("get")
    def get(self, ctx: NativeContext, key: Value, default: Value = null) -> Value:
        try:
            return self.data[key.str_spec(ctx)]
        except KeyError:
            if default is MISSING:
                raise SafulateKeyError(f"Key {key.repr_spec(ctx)} was not found")
            return default

    @public_method("set")
    def set(self, ctx: NativeContext, key: Value, value: Value) -> Value:
        self.data[key.repr_spec(ctx)] = value
        return value

    @public_method("keys")
    def keys(self, ctx: NativeContext) -> ListValue:
        return ListValue([StrValue(x) for x in list(self.data.keys())])

    @public_method("values")
    def values(self, ctx: NativeContext) -> ListValue:
        return ListValue(list(self.data.values()))

    @public_method("items")
    def items(self, ctx: NativeContext) -> ListValue:
        return ListValue(
            [ListValue([StrValue(key), value]) for key, value in self.data.items()]
        )

    @public_method("pop")
    def pop(
        self, ctx: NativeContext, key: Value, default: Value | None = None
    ) -> Value:
        try:
            return self.data.pop(key.repr_spec(ctx))
        except KeyError:
            if default is None:
                raise SafulateKeyError(f"Key {key.repr_spec(ctx)} was not found")
            return default

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> ListValue:
        return self.keys(ctx)

    @spec_meth("has")
    def has(self, ctx: NativeContext, key: Value) -> NumValue:
        return NumValue(int(key in self.data))

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.data)


# region Regex


class PatternValue(ObjectValue):
    def __init__(self, pattern: re.Pattern[str]) -> None:
        super().__init__("regex pattern")

        self.pattern = pattern

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<regex pattern {self.pattern!r}>")

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> StrValue:
        return self.get_pattern_prop(ctx)

    @public_property("pattern")
    def get_pattern_prop(self, ctx: NativeContext) -> StrValue:
        return StrValue(self.pattern.pattern)

    @public_method("search")
    def search(
        self, ctx: NativeContext, sub: Value, start: Value = null, end: Value = null
    ) -> MatchValue | NullValue:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str for substring, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(start, NullValue | NumValue):
            raise SafulateTypeError(
                f"Expected num or null for start pos, got {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, NullValue | NumValue):
            raise SafulateTypeError(
                f"Expected num or null for end pos, got {end.repr_spec(ctx)} instead"
            )

        match = self.pattern.search(
            sub.value,
            0 if isinstance(start, NullValue) else int(start.value),
            sys.maxsize if isinstance(end, NullValue) else int(end.value),
        )
        if match is None:
            return null

        return MatchValue(match, self)

    @public_method("match")
    def match(
        self, ctx: NativeContext, sub: Value, start: Value = null, end: Value = null
    ) -> MatchValue | NullValue:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str for substring, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(start, NullValue | NumValue):
            raise SafulateTypeError(
                f"Expected num or null for start pos, got {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, NullValue | NumValue):
            raise SafulateTypeError(
                f"Expected num or null for end pos, got {end.repr_spec(ctx)} instead"
            )

        match = self.pattern.match(
            sub.value,
            0 if isinstance(start, NullValue) else int(start.value),
            sys.maxsize if isinstance(end, NullValue) else int(end.value),
        )
        if match is None:
            return null

        return MatchValue(match, self)

    @public_method("fullmatch")
    def fullmatch(
        self, ctx: NativeContext, sub: Value, start: Value = null, end: Value = null
    ) -> MatchValue | NullValue:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str for substring, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(start, NullValue | NumValue):
            raise SafulateTypeError(
                f"Expected num or null for start pos, got {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, NullValue | NumValue):
            raise SafulateTypeError(
                f"Expected num or null for end pos, got {end.repr_spec(ctx)} instead"
            )

        match = self.pattern.fullmatch(
            sub.value,
            0 if isinstance(start, NullValue) else int(start.value),
            sys.maxsize if isinstance(end, NullValue) else int(end.value),
        )
        if match is None:
            return null

        return MatchValue(match, self)

    @public_method("find_all")
    def find_all(
        self, ctx: NativeContext, sub: Value, start: Value = null, end: Value = null
    ) -> ListValue:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str for sub, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(start, NullValue | NumValue):
            raise SafulateTypeError(
                f"Expected num or null for start pos, got {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, NullValue | NumValue):
            raise SafulateTypeError(
                f"Expected num or null for end pos, got {end.repr_spec(ctx)} instead"
            )

        return ListValue(
            [
                MatchValue(match, self)
                for match in self.pattern.findall(
                    sub.value,
                    0 if isinstance(start, NullValue) else int(start.value),
                    sys.maxsize if isinstance(end, NullValue) else int(end.value),
                )
            ]
        )

    @public_method("split")
    def split(self, ctx: NativeContext, sub: Value, max: Value = null) -> Value:
        if not isinstance(sub, StrValue):
            raise SafulateTypeError(
                f"Expected str for sub, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(max, NumValue | NullValue):
            raise SafulateTypeError(
                f"Expected str for max, got {max.repr_spec(ctx)} instead"
            )

        return ListValue(
            [
                StrValue(val)
                for val in self.pattern.split(
                    sub.value, 0 if isinstance(max, NullValue) else 1
                )
            ]
        )

    # @public_method("sub")
    # def sub(self, ctx: NativeContext, sub: Value) -> Value:
    #     if not isinstance(sub, StrValue):
    #         raise SafulateTypeError(f"Expected str for sub, got {sub.repr_spec(ctx)} instead")
    #     self.pattern.sub()

    @public_property("groups")
    def groups(self, ctx: NativeContext) -> ListValue:
        return ListValue([StrValue(group) for group in self.pattern.groupindex])


class MatchValue(ObjectValue):
    def __init__(self, match: re.Match[str], pattern: PatternValue) -> None:
        super().__init__("regex match")

        self.match = match
        self.pattern = pattern

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"<Match groups={self.groups(ctx).repr_spec(ctx)}>")

    @public_property("pattern")
    def get_pattern_prop(self, ctx: NativeContext) -> PatternValue:
        return self.pattern

    @public_property("start_pos")
    def start_pos(self, ctx: NativeContext) -> NumValue:
        return NumValue(self.match.pos)

    @public_property("end_pos")
    def end_pos(self, ctx: NativeContext) -> NumValue:
        return NumValue(self.match.endpos)

    @public_method("groups")
    def groups(self, ctx: NativeContext) -> ListValue:
        return ListValue(
            [
                StrValue(val) if isinstance(val, str) else null
                for val in self.match.groups()
            ]
        )

    @public_method("as_dict")
    def as_dict(self, ctx: NativeContext) -> DictValue:
        return DictValue(
            {
                item.value[0].str_spec(ctx): item.value[1]
                for item in self.groups(ctx).value
                if isinstance(item, ListValue)
            }
        )

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> ListValue:
        return self.groups(ctx)

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> BoolValue:
        return BoolValue(self.match)

    @spec_meth("altcall")
    def altcall(self, ctx: NativeContext, key: Value) -> Value:
        match key:
            case StrValue():
                val = self.match[key.value]
                return StrValue(val) if isinstance(val, str) else null
            case NumValue():
                return self.groups(ctx).value[int(key.value)]
            case _:
                raise SafulateTypeError(
                    f"Expected num or str, got {key.repr_spec(ctx)} instead"
                )


# region Error


class NativeErrorValue(ObjectValue):
    def __init__(self, error: str, msg: str, obj: Value = null) -> None:
        super().__init__(error, {"value": obj, "msg": StrValue(msg)})

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> StrValue:
        return StrValue(f"{self.type.name}: {self.public_attrs['msg'].str_spec(ctx)}")

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> StrValue:
        return StrValue(
            f"<{self.type.name} msg={self.public_attrs['msg'].repr_spec(ctx)} value={self.public_attrs['value'].repr_spec(ctx)}>"
        )
