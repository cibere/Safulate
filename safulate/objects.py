from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Concatenate, TypeVar, cast, final

from .asts import ASTBlock, ASTFuncDecl_Param, ASTNode, ASTVisitor, ParamType
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
    from .native_context import NativeContext

SafBaseObjectT = TypeVar("SafBaseObjectT")
NativeMethodT = TypeVar(
    "NativeMethodT",
    bound=Callable[Concatenate[Any, "NativeContext", ...], "SafBaseObject"],
)

__all__ = (
    "SafBaseObject",
    "SafBool",
    "SafDict",
    "SafFunc",
    "SafIterable",
    "SafList",
    "SafNull",
    "SafNum",
    "SafObject",
    "SafProperty",
    "SafPythonError",
    "SafStr",
    "SafTuple",
    "SafType",
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


class SafBaseObject(ABC):
    __safulate_public_attrs__: dict[str, SafBaseObject] | None = None
    __safulate_private_attrs__: dict[str, SafBaseObject] | None = None
    __safulate_specs__: dict[str, SafBaseObject] | None = None

    def _attrs_hook(self, attrs: defaultdict[str, dict[str, SafBaseObject]]) -> None:
        return

    @cached_property
    def _attrs(self) -> defaultdict[str, dict[str, SafBaseObject]]:
        data: defaultdict[str, dict[str, SafBaseObject]] = defaultdict(dict)
        for name, _ in inspect.getmembers(
            self.__class__, lambda attr: hasattr(attr, "__safulate_native_method__")
        ):
            value = getattr(self, name)

            type_, func_name, is_prop = getattr(value, "__safulate_native_method__")
            func = SafFunc.from_native(name, value)
            data[type_][func_name] = SafProperty(func) if is_prop else func
        self._attrs_hook(data)
        return data

    @cached_property
    def public_attrs(self) -> dict[str, SafBaseObject]:
        if self.__safulate_public_attrs__ is None:
            self.__safulate_public_attrs__ = {}

        self.__safulate_public_attrs__.update(self._attrs[""])
        return self.__safulate_public_attrs__

    @cached_property
    def private_attrs(self) -> dict[str, SafBaseObject]:
        if self.__safulate_private_attrs__ is None:
            self.__safulate_private_attrs__ = {}

        self.__safulate_private_attrs__.update(self._attrs["$"])
        return self.__safulate_private_attrs__

    @cached_property
    def specs(self) -> dict[str, SafBaseObject]:
        if self.__safulate_specs__ is None:
            self.__safulate_specs__ = {}

        self.__safulate_specs__.update(self._attrs["%"])
        return self.__safulate_specs__

    def __getitem__(self, key: str) -> SafBaseObject:
        try:
            return self.public_attrs[key]
        except KeyError:
            raise SafulateAttributeError(f"Attribute {key!r} not found")

    def __setitem__(self, key: str, value: SafBaseObject) -> None:
        self.public_attrs[key] = value

    @private_method("get_specs")
    def get_specs(self, ctx: NativeContext) -> SafBaseObject:
        return SafDict(self.specs.copy())

    @spec_meth("add")
    def add(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Add is not defined for this type")

    @spec_meth("sub")
    def sub(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Subtract is not defined for this type")

    @spec_meth("mul")
    def mul(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Multiply is not defined for this type")

    @spec_meth("div")
    def div(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Divide is not defined for this type")

    @spec_meth("pow")
    def pow(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Exponentiation is not defined for this type")

    @spec_meth("uadd")
    def uadd(self, ctx: NativeContext) -> SafBaseObject:
        raise SafulateValueError("Unary add is not defined for this type")

    @spec_meth("neg")
    def neg(self, ctx: NativeContext) -> SafBaseObject:
        raise SafulateValueError("Unary minus is not defined for this type")

    @spec_meth("eq")
    def eq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        return SafBool(self == other)

    @spec_meth("neq")
    def neq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        val = ctx.invoke_spec(self, "eq", other).bool_spec(ctx)
        return SafBool(not val)

    @spec_meth("has_item")
    def has_item(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        val = ctx.invoke_spec(self, "iter")
        if not isinstance(val, SafList):
            raise SafulateValueError(
                f"iter spec returned {val.repr_spec(ctx)}, expected list"
            )
        return SafBool(other in val.value)

    @spec_meth("less")
    def less(self, ctx: NativeContext, _other: SafBaseObject) -> SafBool:
        raise SafulateValueError("Less than is not defined for this type")

    @spec_meth("grtr")
    def grtr(self, ctx: NativeContext, _other: SafBaseObject) -> SafBool:
        raise SafulateValueError("Greater than is not defined for this type")

    @spec_meth("lesseq")
    def lesseq(self, ctx: NativeContext, _other: SafBaseObject) -> SafBool:
        raise SafulateValueError("Less than or equal to is not defined for this type")

    @spec_meth("grtreq")
    def grtreq(self, ctx: NativeContext, _other: SafBaseObject) -> SafBool:
        raise SafulateValueError(
            "Greater than or equal to is not defined for this type"
        )

    @spec_meth("amp")
    def amp(self, ctx: NativeContext, other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("amp is not defined for this type")

    @spec_meth("pipe")
    def pipe(self, ctx: NativeContext, other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("pipe is not defined for this type")

    @spec_meth("not")
    def not_(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.bool_spec(ctx))

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> SafBool:
        return true

    if TYPE_CHECKING:
        altcall: Callable[Concatenate[Any, NativeContext, ...], SafBaseObject]
        call: Callable[Concatenate[Any, NativeContext, ...], SafBaseObject]
    else:

        @spec_meth("altcall")
        def altcall(
            self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
        ) -> SafBaseObject:
            raise SafulateValueError("Cannot altcall this type")

        @spec_meth("call")
        def call(
            self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
        ) -> SafBaseObject:
            raise SafulateValueError("Cannot call this type")

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> SafIterable:
        raise SafulateValueError("This type is not iterable")

    @spec_meth("get")
    def get_spec(self, ctx: NativeContext) -> SafBaseObject:
        return self

    @spec_meth("repr")
    @abstractmethod
    def repr(self, ctx: NativeContext) -> SafBaseObject: ...

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> SafBaseObject:
        return ctx.invoke_spec(self, "repr")

    @spec_meth("format")
    def format(self, ctx: NativeContext, val: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError(f"Unknown format type {val.repr_spec(ctx)}")

    @spec_meth("get_attr")
    def get_attr(self, ctx: NativeContext, name: SafBaseObject) -> SafBaseObject:
        if not isinstance(name, SafStr):
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
        self, spec_name: str, return_value: type[SafBaseObjectT], ctx: NativeContext
    ) -> SafBaseObjectT:
        value = ctx.invoke_spec(self, spec_name)
        if not isinstance(value, return_value):
            raise SafulateValueError(
                f"expected return for {spec_name!r} is str, not {value.repr_spec(ctx)}",
                ctx.token,
            )

        return value

    def repr_spec(self, ctx: NativeContext) -> str:
        return self.run_spec("repr", SafStr, ctx).value

    def str_spec(self, ctx: NativeContext) -> str:
        return self.run_spec("str", SafStr, ctx).value

    def bool_spec(self, ctx: NativeContext) -> bool:
        val = self.run_spec("bool", SafBool, ctx)
        if int(val.value) not in (1, 0):
            raise SafulateValueError(
                f"expected return for bool spec to be a bool, got {val.repr_spec(ctx)} instead"
            )
        return bool(val.value)


class SafType(SafBaseObject):
    def __init__(self, name: str) -> None:
        self.name = name

    def _attrs_hook(self, attrs: defaultdict[str, dict[str, SafBaseObject]]) -> None:
        attrs["%"]["type"] = SafType("type")

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"<type {self.name!r}>")

    @public_method("check")
    def check(self, ctx: NativeContext, obj: SafBaseObject) -> SafBool:
        obj_type = obj.specs["type"]
        return (
            true
            if isinstance(obj_type, SafType) and obj_type.name == self.name
            else false
        )


class SafObject(SafBaseObject):
    __saf_typename__: str
    __saf_init_attrs__: dict[str, SafBaseObject] | None

    def __init__(
        self, name: str, attrs: dict[str, SafBaseObject] | None = None
    ) -> None:
        self.__saf_typename__ = name
        self.__saf_init_attrs__ = attrs

    def _attrs_hook(self, attrs: defaultdict[str, dict[str, SafBaseObject]]) -> None:
        if self.__saf_init_attrs__:
            attrs[""].update(self.__saf_init_attrs__)
        attrs["%"]["type"] = SafType(self.__saf_typename__)

    @property
    def type(self) -> SafType:
        typ = self.specs["type"]
        assert isinstance(typ, SafType)
        return typ

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"<{self.type.name}>")


# region Atoms


class SafNull(SafObject):
    def __init__(self) -> None:
        super().__init__("null")

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr("null")

    @spec_meth("eq")
    def eq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        return SafBool(isinstance(other, SafNull))

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> SafBool:
        return false


class SafNum(SafObject):
    def __init__(self, value: float) -> None:
        super().__init__("num")

        self.value = value

    @spec_meth("add")
    def add(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Add is not defined for number and this type")

        return SafNum(self.value + other.value)

    @spec_meth("sub")
    def sub(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Subtract is not defined for number and this type")

        return SafNum(self.value - other.value)

    @spec_meth("mul")
    def mul(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Multiply is not defined for number and this type")

        return SafNum(self.value * other.value)

    @spec_meth("div")
    def div(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Divide is not defined for number and this type")
        return SafNum(self.value / other.value)

    @spec_meth("pow")
    def pow(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Exponentiation is not defined for number and this type"
            )

        return SafNum(self.value**other.value)

    @spec_meth("uadd")
    def uadd(self, ctx: NativeContext) -> SafNum:
        return SafNum(self.value)

    @spec_meth("neg")
    def neg(self, ctx: NativeContext) -> SafNum:
        return SafNum(-self.value)

    @spec_meth("eq")
    def eq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Equality is not defined for number and this type")

        return SafBool(self.value == other.value)

    @spec_meth("neq")
    def neq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Non-equality is not defined for number and this type"
            )

        return SafBool(self.value != other.value)

    @spec_meth("less")
    def less(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Less than is not defined for number and this type"
            )

        return SafBool(self.value < other.value)

    @spec_meth("grtr")
    def grtr(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Greater than is not defined for number and this type"
            )

        return SafBool(self.value > other.value)

    @spec_meth("lesseq")
    def lesseq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Less than or equal to is not defined for number and this type"
            )

        return SafBool(self.value <= other.value)

    @spec_meth("grtreq")
    def grtreq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Greater than or equal to is not defined for number and this type",
            )

        return SafBool(self.value >= other.value)

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value != 0)

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        if self.value % 1 == 0 and "e" not in str(self.value):
            return SafStr(str(int(self.value)))

        return SafStr(str(self.value))


class SafBool(SafNum):
    def __init__(self, status: Any) -> None:
        self.status: bool = bool(status)
        self.value = int(self.status)

        SafObject.__init__(self, str(self.status).lower())

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(self.type.name)

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> SafStr:
        return self.repr(ctx)

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> SafBool:
        return self


class SafStr(SafObject):
    def __init__(self, value: str) -> None:
        super().__init__("str")

        self.value = value.encode("ascii").decode("unicode_escape")

    @spec_meth("altcall")
    def altcall(self, ctx: NativeContext, idx: SafBaseObject) -> SafStr:
        if not isinstance(idx, SafNum):
            raise SafulateTypeError(f"Expected num, got {idx.repr_spec(ctx)} instead")

        return SafStr(self.value[int(idx.value)])

    @spec_meth("add")
    def add(self, ctx: NativeContext, other: SafBaseObject) -> SafStr:
        if not isinstance(other, SafStr):
            other = ctx.invoke_spec(other, "str")
        if not isinstance(other, SafStr):
            raise SafulateValueError(
                f"{other.repr_spec(ctx)} could not be converted into a string"
            )

        return SafStr(self.value + other.value)

    @spec_meth("mul")
    def mul(self, ctx: NativeContext, other: SafBaseObject) -> SafStr:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Multiply is not defined for string and this type")

        if other.value % 1 != 0:
            raise SafulateValueError(
                "Cannot multiply string by a float, must be integer"
            )

        return SafStr(self.value * int(other.value))

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> SafList:
        return SafList([SafStr(char) for char in self.value])

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> SafBool:
        return SafBool(len(self.value) != 0)

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(repr(self.value))

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> SafStr:
        return SafStr(self.value)

    @spec_meth("eq")
    def eq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        return SafBool(isinstance(other, SafStr) and other.value == self.value)

    @public_method("format")
    def format_(self, ctx: NativeContext, *args: SafBaseObject) -> SafBaseObject:
        val = self.value
        for arg in args:
            if not isinstance(arg, SafStr):
                raise SafulateTypeError("Format can only visit str values")

            val = val.replace("{}", arg.value, 1)

        return SafStr(val)

    @public_method("capitalize")
    def capitalize(self, ctx: NativeContext) -> SafBaseObject:
        return SafStr(self.value.capitalize())

    @public_method("title")
    def title(self, ctx: NativeContext) -> SafBaseObject:
        return SafStr(self.value.title())

    @public_method("upper")
    def upper(self, ctx: NativeContext) -> SafBaseObject:
        return SafStr(self.value.upper())

    @public_method("casefold")
    def casefold(self, ctx: NativeContext) -> SafBaseObject:
        return SafStr(self.value.casefold())

    @public_method("count")
    def count(
        self,
        ctx: NativeContext,
        char: SafBaseObject,
        start: SafBaseObject = SafNum(0),
        end: SafBaseObject = SafNum(-1),
    ) -> SafBaseObject:
        if not isinstance(char, SafStr):
            raise SafulateTypeError(
                f"Expected str for char, received {char.repr_spec(ctx)} instead"
            )
        if not isinstance(start, SafNum):
            raise SafulateTypeError(
                f"Expected num for start, received {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, SafNum):
            raise SafulateTypeError(
                f"Expected num for end, received {end.repr_spec(ctx)} instead"
            )
        return SafNum(self.value.count(char.value, int(start.value), int(end.value)))

    @public_method("endswith")
    def casendswithefold(self, ctx: NativeContext, sub: SafBaseObject) -> SafBool:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return SafBool(self.value.endswith(sub.value))

    @public_method("index")
    def index(self, ctx: NativeContext, sub: SafBaseObject) -> SafBaseObject:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return SafNum(int(self.value.index(sub.value)))

    @public_method("is_alnum")
    def isalnum(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.isalnum())

    @public_method("is_alpha")
    def isalpha(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.isalpha())

    @public_method("is_ascii")
    def isascii(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.isascii())

    @public_method("is_decimal")
    def isdecimal(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.isdecimal())

    @public_method("is_digit")
    def isdigit(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.isdigit())

    @public_method("is_lower")
    def islower(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.islower())

    @public_method("is_numeric")
    def isnumeric(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.isnumeric())

    @public_method("is_space")
    def isspace(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.isspace())

    @public_method("is_title")
    def istitle(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.istitle())

    @public_method("is_upper")
    def isupper(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.value.isupper())

    @public_method("lower")
    def lower(self, ctx: NativeContext) -> SafBaseObject:
        return SafStr(self.value.lower())

    @public_method("replace")
    def replace(
        self,
        ctx: NativeContext,
        before: SafBaseObject,
        after: SafBaseObject,
        count: SafBaseObject = SafNum(-1),
    ) -> SafBaseObject:
        if not isinstance(before, SafStr):
            raise SafulateTypeError(
                f"Expected str for before, received {before.repr_spec(ctx)} instead"
            )
        if not isinstance(after, SafStr):
            raise SafulateTypeError(
                f"Expected str for after, received {after.repr_spec(ctx)} instead"
            )
        if not isinstance(count, (SafNum)):
            raise SafulateTypeError(
                f"Expected int for cont, received {count.repr_spec(ctx)} instead"
            )
        return SafStr(self.value.replace(before.value, after.value, int(count.value)))

    @public_method("remove_prefix")
    def remove_prefix(self, ctx: NativeContext, prefix: SafBaseObject) -> SafBaseObject:
        if not isinstance(prefix, SafStr):
            raise SafulateTypeError(
                f"Expected str, received {prefix.repr_spec(ctx)} instead"
            )
        return SafStr(self.value.removeprefix(prefix.value))

    @public_method("remove_suffix")
    def remove_suffix(self, ctx: NativeContext, suffix: SafBaseObject) -> SafBaseObject:
        if not isinstance(suffix, SafStr):
            raise SafulateTypeError(
                f"Expected str, received {suffix.repr_spec(ctx)} instead"
            )
        return SafStr(self.value.removesuffix(suffix.value))

    @public_method("strip")
    def strip(self, ctx: NativeContext, sub: SafBaseObject) -> SafBaseObject:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return SafStr(self.value.strip(sub.value))

    @public_method("lstrip")
    def lstrip(self, ctx: NativeContext, sub: SafBaseObject) -> SafBaseObject:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return SafStr(self.value.lstrip(sub.value))

    @public_method("rstrip")
    def rstrip(self, ctx: NativeContext, sub: SafBaseObject) -> SafBaseObject:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return SafStr(self.value.rstrip(sub.value))

    @public_method("split")
    def split(self, ctx: NativeContext, delimiter: SafBaseObject) -> SafBaseObject:
        if not isinstance(delimiter, SafStr):
            raise SafulateTypeError(
                f"Expected str, received {delimiter.repr_spec(ctx)} instead"
            )
        return SafList([SafStr(part) for part in self.value.split(delimiter.value)])


# region Structures


class SafIterable(SafObject):
    value: list[SafBaseObject] | tuple[SafBaseObject, ...]

    def __patched_init(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("SafIterable should not be created directly")

    if not TYPE_CHECKING:
        __init__ = __patched_init

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> SafBool:
        return SafBool(len(self.value) != 0)

    @spec_meth("altcall")
    def altcall(self, ctx: NativeContext, idx: SafBaseObject) -> SafBaseObject:
        if not isinstance(idx, SafNum):
            raise SafulateTypeError(f"Expected num, got {idx.repr_spec(ctx)} instead.")

        try:
            return self.value[int(idx.value)]
        except IndexError:
            raise SafulateIndexError(f"Index {idx.repr_spec(ctx)} is out of range")

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> SafIterable:
        return self

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(
            "["
            + ", ".join(
                [
                    cast("SafStr", ctx.invoke_spec(val, "repr")).value
                    for val in self.value
                ]
            )
            + "]"
        )

    @public_property("len")
    def len(self, ctx: NativeContext) -> SafNum:
        return SafNum(len(self.value))


class SafTuple(SafIterable):
    def __init__(self, value: tuple[SafBaseObject, ...]) -> None:
        SafObject.__init__(self, "tuple")

        self.value = value


class SafList(SafIterable):
    value: list[SafBaseObject]

    def __init__(self, value: list[SafBaseObject]) -> None:
        SafObject.__init__(self, "list")

        self.value = value  # pyright: ignore[reportIncompatibleVariableOverride]

    @public_method("append")
    def append(self, ctx: NativeContext, item: SafBaseObject) -> SafBaseObject:
        self.value.append(item)
        return null

    @public_method("remove")
    def remove(self, ctx: NativeContext, item: SafBaseObject) -> SafBaseObject:
        self.value.remove(item)
        return null

    @public_method("pop")
    def pop(self, ctx: NativeContext, index: SafBaseObject) -> SafBaseObject:
        if not isinstance(index, SafNum):
            raise SafulateTypeError(f"expected num, got {index.repr_spec(ctx)} instead")
        if abs(index.value) > len(self.value):
            return null

        return self.value.pop(int(index.value))


class SafFunc(SafObject):
    def __init__(
        self,
        name: Token | None,
        params: list[ASTFuncDecl_Param],
        body: ASTBlock | Callable[Concatenate[NativeContext, ...], SafBaseObject],
        parent: SafBaseObject | None = None,
        extra_vars: dict[str, SafBaseObject] | None = None,
        partial_args: tuple[SafBaseObject, ...] | None = None,
        partial_kwargs: dict[str, SafBaseObject] | None = None,
    ) -> None:
        super().__init__("func")

        self.name = name
        self.params = params
        self.body = body
        self.parent = parent
        self.extra_vars = extra_vars or {}
        self.partial_args = partial_args or ()
        self.partial_kwargs = partial_kwargs or {}

    def _resolve_default(
        self,
        default: ASTNode | None | SafBaseObject,
        visitor: ASTVisitor,
        error_msg_callback: Callable[[], str],
    ) -> SafBaseObject:
        if default is None:
            raise SafulateValueError(error_msg_callback())

        return default if isinstance(default, SafBaseObject) else default.visit(visitor)

    def _validate_params(
        self, ctx: NativeContext, *init_args: SafBaseObject, **kwargs: SafBaseObject
    ) -> dict[str, SafBaseObject]:
        params = self.params.copy()
        args = list(init_args)
        passable_params: dict[str, SafBaseObject] = {}

        for param in params:
            if param.type is ParamType.vararg:
                passable_params[param.name.lexeme] = SafList(args)
                args = []
            elif param.type is ParamType.varkwarg:
                passable_params[param.name.lexeme] = SafDict(kwargs)
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
                    passable_params[param.name.lexeme] = self._resolve_default(
                        param.default,
                        ctx.interpreter,
                        lambda: f"Required positional argument was not passed: {param.name.lexeme!r}",
                    )
                else:
                    if param.name.lexeme not in kwargs:
                        passable_params[param.name.lexeme] = self._resolve_default(
                            param.default,
                            ctx.interpreter,
                            lambda: f"Required {param.type.to_arg_type_str()}argument was not passed: {param.name.lexeme!r}",
                        )
                    else:
                        passable_params[param.name.lexeme] = kwargs.pop(
                            param.name.lexeme
                        )
            else:
                passable_params[param.name.lexeme] = self._resolve_default(
                    param.default,
                    ctx.interpreter,
                    lambda: f"Required {param.type.to_arg_type_str()}argument was not passed: {param.name.lexeme!r}",
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

    def with_partial_params(
        self, args: tuple[SafBaseObject, ...], kwargs: dict[str, SafBaseObject]
    ) -> SafFunc:
        return SafFunc(
            name=self.name,
            params=self.params,
            body=self.body,
            parent=self.parent,
            extra_vars=self.extra_vars,
            partial_args=args,
            partial_kwargs=kwargs,
        )

    @public_method("without_partial_params")
    def without_partial_params(self, ctx: NativeContext) -> SafFunc:
        return self.with_partial_params((), {})

    @public_property("partial_args")
    def partial_args_prop(self, ctx: NativeContext) -> SafTuple:
        return SafTuple(self.partial_args)

    @spec_meth("neg")
    def neg(self, ctx: NativeContext) -> SafFunc:
        return self.with_partial_params(
            tuple(reversed(self.partial_args)), self.partial_kwargs
        )

    @spec_meth("altcall")
    def altcall(
        self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
    ) -> SafBaseObject:
        return self.with_partial_params(
            (*self.partial_args, *args), self.partial_kwargs | kwargs
        )

    @spec_meth("call")
    def call(
        self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
    ) -> SafBaseObject:
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
    def repr(self, ctx: NativeContext) -> SafStr:
        suffix = f" {self.name.lexeme!r}" if self.name else ""
        return SafStr(f"<func{suffix}>")

    @classmethod
    def from_native(
        cls,
        name: str,
        callback: Callable[Concatenate[NativeContext, ...], SafBaseObject],
    ) -> SafFunc:
        raw_params = list(inspect.signature(callback).parameters.values())

        return SafFunc(
            name=Token(TokenType.ID, name, -1),
            params=[
                ASTFuncDecl_Param(
                    name=Token(TokenType.ID, param.name, -1),
                    default=None if param.default is param.empty else param.default,
                    type={
                        param.VAR_POSITIONAL: ParamType.vararg,
                        param.VAR_KEYWORD: ParamType.varkwarg,
                        param.POSITIONAL_ONLY: ParamType.arg,
                        param.KEYWORD_ONLY: ParamType.kwarg,
                        param.POSITIONAL_OR_KEYWORD: ParamType.arg_or_kwarg,
                    }[param.kind],
                )
                for param in raw_params
            ][1:],
            body=callback,
        )


class SafProperty(SafObject):
    def __init__(self, func: SafFunc) -> None:
        super().__init__("property")

        self.func = func

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"<property {self.func.repr_spec(ctx)}>")

    @spec_meth("get")
    def get_spec(self, ctx: NativeContext) -> SafBaseObject:
        return ctx.invoke(self.func)

    @public_property("func")
    def func_prop(self, ctx: NativeContext) -> SafBaseObject:
        return self.func


MISSING: Any = object()
null = SafNull()
true = SafBool(True)
false = SafBool(False)


class SafDict(SafObject):
    def __init__(self, data: dict[str, SafBaseObject]) -> None:
        super().__init__("dict")

        self.data = data

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(
            "{"
            + ", ".join(
                f"{key!r}:{value.repr_spec(ctx)}" for key, value in self.data.items()
            )
            + "}"
        )

    @spec_meth("altcall")
    def altcall(
        self, ctx: NativeContext, key: SafBaseObject, default: SafBaseObject = MISSING
    ) -> SafBaseObject:
        return self.get(ctx, key, default)

    @public_method("get")
    def get(
        self, ctx: NativeContext, key: SafBaseObject, default: SafBaseObject = null
    ) -> SafBaseObject:
        try:
            return self.data[key.str_spec(ctx)]
        except KeyError:
            if default is MISSING:
                raise SafulateKeyError(f"Key {key.repr_spec(ctx)} was not found")
            return default

    @public_method("set")
    def set(
        self, ctx: NativeContext, key: SafBaseObject, value: SafBaseObject
    ) -> SafBaseObject:
        self.data[key.repr_spec(ctx)] = value
        return value

    @public_method("keys")
    def keys(self, ctx: NativeContext) -> SafList:
        return SafList([SafStr(x) for x in list(self.data.keys())])

    @public_method("values")
    def values(self, ctx: NativeContext) -> SafList:
        return SafList(list(self.data.values()))

    @public_method("items")
    def items(self, ctx: NativeContext) -> SafList:
        return SafList(
            [SafList([SafStr(key), value]) for key, value in self.data.items()]
        )

    @public_method("pop")
    def pop(
        self,
        ctx: NativeContext,
        key: SafBaseObject,
        default: SafBaseObject | None = None,
    ) -> SafBaseObject:
        try:
            return self.data.pop(key.repr_spec(ctx))
        except KeyError:
            if default is None:
                raise SafulateKeyError(f"Key {key.repr_spec(ctx)} was not found")
            return default

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> SafList:
        return self.keys(ctx)

    @spec_meth("has")
    def has(self, ctx: NativeContext, key: SafBaseObject) -> SafNum:
        return SafNum(int(key in self.data))

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.data)


# region Error


class SafPythonError(SafObject):
    def __init__(self, error: str, msg: str, obj: SafBaseObject = null) -> None:
        super().__init__(error, {"value": obj, "msg": SafStr(msg)})

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"{self.type.name}: {self.public_attrs['msg'].str_spec(ctx)}")

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(
            f"<{self.type.name} msg={self.public_attrs['msg'].repr_spec(ctx)} value={self.public_attrs['value'].repr_spec(ctx)}>"
        )
