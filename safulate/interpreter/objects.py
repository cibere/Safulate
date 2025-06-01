from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Iterator
from functools import partial as partial_func
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Self,
    TypedDict,
    TypeVar,
    cast,
    final,
)

from ..errors import (
    SafulateAttributeError,
    SafulateBreakoutError,
    SafulateIndexError,
    SafulateInvalidReturn,
    SafulateKeyError,
    SafulateTypeError,
    SafulateValueError,
)
from ..lexer import Token, TokenType
from ..parser import (
    ASTBlock,
    ASTFuncDecl_Param,
    ASTNode,
    ASTVisitor,
    AttrSpec,
    BinarySpec,
    CallSpec,
    FormatSpec,
    ParamType,
    SpecName,
    UnarySpec,
    spec_name_from_str,
)
from ..properties import cached_property
from ..utils import FallbackDict

if TYPE_CHECKING:
    from .native_context import NativeContext

SafBaseObjectT = TypeVar("SafBaseObjectT")
NativeMethodT = TypeVar(
    "NativeMethodT",
    bound=Callable[Concatenate[Any, "NativeContext", ...], "SafBaseObject"],
)
DefaultSpecT = TypeVar(
    "DefaultSpecT",
    bound=Callable[Concatenate["SafBaseObject", "NativeContext", ...], "SafBaseObject"],
)

__all__ = (
    "SafBaseObject",
    "SafBool",
    "SafDict",
    "SafEllipsis",
    "SafFunc",
    "SafIterator",
    "SafList",
    "SafModule",
    "SafNull",
    "SafNum",
    "SafObject",
    "SafProperty",
    "SafPythonError",
    "SafStr",
    "SafTuple",
    "SafType",
    "SafTypeUnion",
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


def __spec_deco(
    *, is_prop: bool
) -> Callable[[SpecName], Callable[[NativeMethodT], NativeMethodT]]:
    def deco(name: SpecName) -> Callable[[NativeMethodT], NativeMethodT]:
        def decorator(func: NativeMethodT) -> NativeMethodT:
            setattr(func, "__safulate_native_method__", ("spec", name, is_prop))
            return func

        return decorator

    return deco


public_method = __method_deco("pub", is_prop=False)
public_property = __method_deco("pub", is_prop=True)
private_method = __method_deco("priv", is_prop=False)
private_property = __method_deco("priv", is_prop=True)
spec_meth = __spec_deco(is_prop=False)
spec_prop = __spec_deco(is_prop=True)


class _DefaultSpecs:
    def __init__(self) -> None:
        self.raw_specs: dict[
            SpecName,
            Callable[Concatenate[SafBaseObject, NativeContext, ...], SafBaseObject],
        ] = {FormatSpec.repr: lambda obj, ctx: SafStr(f"<{obj.__class__.__name__}>")}

    def get(self, key: SpecName, *, obj: SafBaseObject) -> SafFunc:
        raw_spec = self.raw_specs[key]
        return SafFunc.from_native(key.name, partial_func(raw_spec, obj))

    def get_from_str(self, key: str, *, obj: SafBaseObject) -> SafFunc:
        return self.get(key=spec_name_from_str(key), obj=obj)

    def register(self, name: SpecName) -> Callable[[DefaultSpecT], DefaultSpecT]:
        def replacement(
            self: SafBaseObject,
            ctx: NativeContext,
            *args: SafBaseObject,
            **kwargs: SafBaseObject,
        ) -> SafBaseObject:
            return ctx.invoke_spec(self, name, *args, **kwargs)

        def deco(func: DefaultSpecT) -> DefaultSpecT:
            self.raw_specs[name] = func
            return replacement  # type: ignore[reportReturnType]

        return deco


_default_specs = _DefaultSpecs()

# region Base


class _RawAttrs(TypedDict):
    pub: dict[str, SafBaseObject]
    priv: dict[str, SafBaseObject]
    spec: dict[SpecName, SafBaseObject]


class SafBaseObject(ABC):
    __safulate_public_attrs__: dict[str, SafBaseObject] | None = None
    __safulate_private_attrs__: dict[str, SafBaseObject] | None = None
    __safulate_specs__: dict[SpecName, SafBaseObject] | None = None
    init: Callable[Concatenate[NativeContext, ...], Self] | SafBaseObject | None = None

    def _attrs_hook(self, attrs: _RawAttrs) -> None:
        return

    @cached_property
    def _attrs(self) -> _RawAttrs:
        data: _RawAttrs = defaultdict(dict)  # pyright: ignore[reportAssignmentType, reportUnknownVariableType]
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

        self.__safulate_public_attrs__.update(self._attrs["pub"])
        return self.__safulate_public_attrs__

    @cached_property
    def private_attrs(self) -> dict[str, SafBaseObject]:
        if self.__safulate_private_attrs__ is None:
            self.__safulate_private_attrs__ = {}

        self.__safulate_private_attrs__.update(self._attrs["priv"])
        return self.__safulate_private_attrs__

    @cached_property
    def specs(self) -> dict[SpecName, SafBaseObject]:
        if self.__safulate_specs__ is None:
            self.__safulate_specs__ = {}

        self.__safulate_specs__.update(self._attrs["spec"])
        return FallbackDict(
            self.__safulate_specs__, partial_func(_default_specs.get, obj=self)
        )

    def __getitem__(self, key: str) -> SafBaseObject:
        try:
            return self.public_attrs[key]
        except KeyError:
            raise SafulateAttributeError(f"Attribute {key!r} not found")

    def __setitem__(self, key: str, value: SafBaseObject) -> None:
        self.public_attrs[key] = value

    @private_method("get_specs")
    def get_specs(self, ctx: NativeContext) -> SafBaseObject:
        return SafDict.from_data(
            ctx, {key.name: value for key, value in self.specs.items()}
        )

    @_default_specs.register(BinarySpec.add)
    def add(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Add is not defined for this type")

    @_default_specs.register(BinarySpec.sub)
    def sub(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Subtract is not defined for this type")

    @_default_specs.register(BinarySpec.mul)
    def mul(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Multiply is not defined for this type")

    @_default_specs.register(BinarySpec.div)
    def div(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Divide is not defined for this type")

    @_default_specs.register(BinarySpec.pow)
    def pow(self, ctx: NativeContext, _other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("Exponentiation is not defined for this type")

    @_default_specs.register(UnarySpec.uadd)
    def uadd(self, ctx: NativeContext) -> SafBaseObject:
        raise SafulateValueError("Unary add is not defined for this type")

    @_default_specs.register(UnarySpec.neg)
    def neg(self, ctx: NativeContext) -> SafBaseObject:
        raise SafulateValueError("Unary minus is not defined for this type")

    @_default_specs.register(BinarySpec.less)
    def less(self, ctx: NativeContext, _other: SafBaseObject) -> SafBool:
        raise SafulateValueError("Less than is not defined for this type")

    @_default_specs.register(BinarySpec.grtr)
    def grtr(self, ctx: NativeContext, _other: SafBaseObject) -> SafBool:
        raise SafulateValueError("Greater than is not defined for this type")

    @_default_specs.register(BinarySpec.lesseq)
    def lesseq(self, ctx: NativeContext, _other: SafBaseObject) -> SafBool:
        raise SafulateValueError("Less than or equal to is not defined for this type")

    @_default_specs.register(BinarySpec.grtreq)
    def grtreq(self, ctx: NativeContext, _other: SafBaseObject) -> SafBool:
        raise SafulateValueError(
            "Greater than or equal to is not defined for this type"
        )

    @_default_specs.register(BinarySpec.amp)
    def amp(self, ctx: NativeContext, other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("amp is not defined for this type")

    @_default_specs.register(BinarySpec.pipe)
    def pipe(self, ctx: NativeContext, other: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError("pipe is not defined for this type")

    @_default_specs.register(BinarySpec.eq)
    def eq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        return true if self == other else false

    @_default_specs.register(BinarySpec.neq)
    def neq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        val = ctx.invoke_spec(self, BinarySpec.eq, other).bool_spec(ctx)
        return true if not val else false

    @_default_specs.register(CallSpec.iter)
    def iter(self, ctx: NativeContext) -> SafIterator:
        raise SafulateValueError("This type is not iterable")

    @_default_specs.register(CallSpec.next)
    def next(self, ctx: NativeContext) -> SafBaseObject:
        raise SafulateValueError("next is not defined for this type")

    @_default_specs.register(BinarySpec.has_item)
    def has_item(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        raise SafulateValueError("has_item is not defined for this type")

    @_default_specs.register(UnarySpec.bool)
    def bool(self, ctx: NativeContext) -> SafBool:
        return true

    if TYPE_CHECKING:
        altcall: Callable[Concatenate[Any, NativeContext, ...], SafBaseObject]
        call: Callable[Concatenate[Any, NativeContext, ...], SafBaseObject]
    else:

        @_default_specs.register(CallSpec.altcall)
        def altcall(
            self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
        ) -> SafBaseObject:
            raise SafulateValueError(f"{self.repr_spec(ctx)} is not altcallable")

        @_default_specs.register(CallSpec.call)
        def call(
            self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
        ) -> SafBaseObject:
            raise SafulateValueError(f"{self.repr_spec(ctx)} is not callable")

    @_default_specs.register(CallSpec.get)
    def get_spec(self, ctx: NativeContext) -> SafBaseObject:
        return self

    @spec_meth(FormatSpec.repr)
    @abstractmethod
    def repr(self, ctx: NativeContext) -> SafBaseObject: ...

    @_default_specs.register(FormatSpec.str)
    def str(self, ctx: NativeContext) -> SafBaseObject:
        return ctx.invoke_spec(self, FormatSpec.repr)

    @_default_specs.register(FormatSpec.hash)
    def hash(self, ctx: NativeContext) -> SafNum:
        return SafNum(hash((self.__class__, id(self))))

    @_default_specs.register(CallSpec.format)
    def format(self, ctx: NativeContext, val: SafBaseObject) -> SafBaseObject:
        raise SafulateValueError(f"Unknown format type {val.repr_spec(ctx)}")

    @_default_specs.register(CallSpec.get_attr)
    def get_attr(self, ctx: NativeContext, name: SafBaseObject) -> SafBaseObject:
        if not isinstance(name, SafStr):
            raise SafulateValueError(f"Expected str, got {name.repr_spec(ctx)} instead")
        val = self.public_attrs.get(name.value)
        if val is None:
            raise SafulateAttributeError(f"Attribute Not Found: {name.repr_spec(ctx)}")
        return ctx.invoke_spec(val, CallSpec.get)

    @final
    def __str__(self) -> str:
        raise RuntimeError("use str_spec instead")

    @final
    def __repr__(self) -> str:
        raise RuntimeError("use repr_spec instead")

    def run_spec(
        self,
        spec_name: SpecName,
        return_value: type[SafBaseObjectT],
        ctx: NativeContext,
    ) -> SafBaseObjectT:
        value = ctx.invoke_spec(self, spec_name)
        if not isinstance(value, return_value):
            raise SafulateValueError(
                f"expected return for {spec_name!r} is str, not {value.repr_spec(ctx)}",
                ctx.token,
            )

        return value

    def repr_spec(self, ctx: NativeContext) -> str:
        return self.run_spec(FormatSpec.repr, SafStr, ctx).value

    def str_spec(self, ctx: NativeContext) -> str:
        return self.run_spec(FormatSpec.str, SafStr, ctx).value

    def hash_spec(self, ctx: NativeContext) -> int | float:
        return self.run_spec(FormatSpec.hash, SafNum, ctx).value

    def bool_spec(self, ctx: NativeContext) -> bool:
        val = self.run_spec(UnarySpec.bool, SafBool, ctx)
        if int(val.value) not in (1, 0):
            raise SafulateValueError(
                f"expected return for bool spec to be a bool, got {val.repr_spec(ctx)} instead"
            )
        return bool(val.value)

    def iter_spec(self, ctx: NativeContext) -> Iterator[SafBaseObject]:
        iterator = ctx.invoke_spec(self, CallSpec.iter)
        try:
            while 1:
                yield ctx.invoke_spec(iterator, CallSpec.next)
        except SafulateBreakoutError as e:
            e.check()

    @property
    def parent(self) -> SafBaseObject | None:
        if AttrSpec.parent in self.specs:
            return self.specs[AttrSpec.parent]

    def set_parent(self, parent: SafBaseObject | None) -> None:
        if parent:
            self.specs[AttrSpec.parent] = parent
        else:
            self.specs.pop(AttrSpec.parent, None)


class SafType(SafBaseObject):
    def __init__(
        self,
        name: str,
        *,
        init: SafBaseObject | type[SafBaseObject] | None = None,
        arity: tuple[int, int] | int = 0,
    ) -> None:
        self.name = name
        self.init_obj = init
        self.arity: tuple[int, int] = (
            (arity, arity) if isinstance(arity, int) else arity
        )

    @spec_meth(CallSpec.altcall)
    def altcall(
        self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
    ) -> SafBaseObject:
        if kwargs:
            raise SafulateValueError("Type params does not accept kwargs")
        if self.arity[0] < len(args) < self.arity[1]:
            msg = (
                f"Expected between {self.arity[0]} and {self.arity[1]} params"
                if self.arity[0] != self.arity[1]
                else f"Expected {self.arity[0]} params"
            )
            raise SafulateValueError(f"{msg} but received {len(args)} instead")
        if any(not isinstance(child, SafType) for child in args):
            raise SafulateTypeError("Type params must be types")

        obj = SafType(self.name, init=self.init_obj, arity=self.arity)
        obj.private_attrs["args"] = SafTuple(args)
        return obj

    @classmethod
    def base_type(cls) -> Self:
        def _init(
            ctx: NativeContext, inp: SafBaseObject, *, init: SafBaseObject = null
        ) -> SafType:
            if init is null:
                return cast("SafType", inp.specs[AttrSpec.type])
            return cls(inp.str_spec(ctx), init=init)

        self = cls("type", init=SafFunc.from_native("type", _init))
        return self

    @classmethod
    def object_type(cls) -> Self:
        def _init(ctx: NativeContext, name: SafBaseObject = null) -> SafObject:
            return SafObject(
                name=f"Custom Object @ {ctx.token.start}"
                if name is null
                else name.str_spec(ctx),
                attrs={},
            )

        return cls("object", init=SafFunc.from_native("object", _init))

    def _attrs_hook(self, attrs: _RawAttrs) -> None:
        attrs["spec"][AttrSpec.type] = self.base_type()
        if isinstance(self.init_obj, SafBaseObject):
            attrs["spec"][CallSpec.init] = self.init_obj
        elif self.init_obj and isinstance(self.init_obj.init, Callable):
            attrs["spec"][CallSpec.call] = SafFunc.from_native(
                "call", self.init_obj.init
            )

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"<type {self.name!r}>")

    @public_method("check")
    def check(self, ctx: NativeContext, obj: SafBaseObject) -> SafBool:
        obj_type = obj.specs[AttrSpec.type]
        return (
            true
            if isinstance(obj_type, SafType) and obj_type.name == self.name
            else false
        )

    @spec_meth(CallSpec.init)
    def init_spec(
        self,
        ctx: NativeContext,
        *args: SafBaseObject,
        **kwargs: SafBaseObject,
    ) -> SafBaseObject:
        raise SafulateTypeError(f"The {self.name!r} type can not be initialized")

    @spec_meth(CallSpec.call)
    def call(
        self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
    ) -> SafBaseObject:
        obj = SafObject(self.name)
        obj.set_parent(self)

        init = self.specs[CallSpec.init]
        assert isinstance(init, SafFunc)

        original_get_scope = init.get_scope
        init.get_scope = lambda ctx: obj

        ctx.invoke(init, *args, **kwargs)

        init.get_scope = original_get_scope
        return obj

    @spec_meth(BinarySpec.pipe)
    def pipe(self, ctx: NativeContext, other: SafBaseObject) -> SafBaseObject:
        if not isinstance(other, SafType | SafStr):
            raise SafulateTypeError(
                f"Expected type for type union, recieved {other.repr_spec(ctx)} instead"
            )

        return SafTypeUnion(self, other)


class SafTypeUnion(SafType):
    def __init__(self, *types: SafType | SafStr) -> None:
        self.types = types

        super().__init__("union")

    @property
    def args(self) -> SafTuple:
        return SafTuple(self.types)

    @spec_meth(BinarySpec.pipe)
    def pipe(self, ctx: NativeContext, other: SafBaseObject) -> SafBaseObject:
        if isinstance(other, SafTypeUnion):
            return SafTypeUnion(*self.types, *other.types)
        if isinstance(other, SafType | SafStr):
            return SafTypeUnion(*self.types, other)

        raise SafulateTypeError(
            f"Expected type for type union, recieved {other.repr_spec(ctx)} instead"
        )


class SafObject(SafBaseObject):
    __saf_typename__: str
    __saf_init_attrs__: dict[str, SafBaseObject] | None

    def __init__(
        self, name: str, attrs: dict[str, SafBaseObject] | None = None
    ) -> None:
        self.__saf_typename__ = name
        self.__saf_init_attrs__ = attrs

    def _attrs_hook(self, attrs: _RawAttrs) -> None:
        if self.__saf_init_attrs__:
            attrs["pub"].update(self.__saf_init_attrs__)

        attrs["spec"][AttrSpec.type] = SafType(
            self.__saf_typename__, init=self.__class__
        )

    @property
    def type(self) -> SafType:
        typ = self.specs[AttrSpec.type]
        assert isinstance(typ, SafType)
        return typ

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"<{self.type.name}>")


class SafModule(SafObject):
    def __init__(
        self, name: str, attrs: dict[str, SafBaseObject] | None = None
    ) -> None:
        super().__init__("module", attrs)
        self.name = name

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"<module {self.name}>")


# region Atoms


class SafNull(SafObject):
    def __init__(self) -> None:
        raise RuntimeError("null should not be constructed directly")

    @classmethod
    def _create(cls) -> SafNull:
        self = super().__new__(cls)
        SafObject.__init__(self, "null")
        return self

    @spec_meth(FormatSpec.str)
    def str(self, ctx: NativeContext) -> SafStr:
        return SafStr("")

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr("null")

    @spec_meth(BinarySpec.eq)
    def eq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        return true if (isinstance(other, SafNull)) else false

    @spec_meth(UnarySpec.bool)
    def bool(self, ctx: NativeContext) -> SafBool:
        return false


class SafNum(SafObject):
    def __init__(self, value: float) -> None:
        super().__init__("num")

        self.value = value

    @staticmethod
    def init(ctx: NativeContext, inp: SafBaseObject) -> SafNum:
        string = inp.str_spec(ctx)
        try:
            return SafNum(float(string))
        except ValueError:
            raise SafulateValueError(f"Could not convert {string!r} into a number")

    @spec_meth(FormatSpec.hash)
    def hash(self, ctx: NativeContext) -> SafNum:
        return SafNum(hash((self.__class__, self.value)))

    @spec_meth(BinarySpec.add)
    def add(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Add is not defined for number and this type")

        return SafNum(self.value + other.value)

    @spec_meth(BinarySpec.sub)
    def sub(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Subtract is not defined for number and this type")

        return SafNum(self.value - other.value)

    @spec_meth(BinarySpec.mul)
    def mul(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Multiply is not defined for number and this type")

        return SafNum(self.value * other.value)

    @spec_meth(BinarySpec.div)
    def div(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Divide is not defined for number and this type")
        return SafNum(self.value / other.value)

    @spec_meth(BinarySpec.pow)
    def pow(self, ctx: NativeContext, other: SafBaseObject) -> SafNum:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Exponentiation is not defined for number and this type"
            )

        return SafNum(self.value**other.value)

    @spec_meth(UnarySpec.uadd)
    def uadd(self, ctx: NativeContext) -> SafNum:
        return SafNum(self.value)

    @spec_meth(UnarySpec.neg)
    def neg(self, ctx: NativeContext) -> SafNum:
        return SafNum(-self.value)

    @spec_meth(BinarySpec.eq)
    def eq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        return (
            true if isinstance(other, SafNum) and (self.value == other.value) else false
        )

    @spec_meth(BinarySpec.less)
    def less(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Less than is not defined for number and this type"
            )

        return true if (self.value < other.value) else false

    @spec_meth(BinarySpec.grtr)
    def grtr(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Greater than is not defined for number and this type"
            )

        return true if (self.value > other.value) else false

    @spec_meth(BinarySpec.lesseq)
    def lesseq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Less than or equal to is not defined for number and this type"
            )

        return true if (self.value <= other.value) else false

    @spec_meth(BinarySpec.grtreq)
    def grtreq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        if not isinstance(other, SafNum):
            raise SafulateValueError(
                "Greater than or equal to is not defined for number and this type",
            )

        return true if (self.value >= other.value) else false

    @spec_meth(UnarySpec.bool)
    def bool(self, ctx: NativeContext) -> SafBool:
        return true if (self.value != 0) else false

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        if self.value % 1 == 0 and "e" not in str(self.value):
            return SafStr(str(int(self.value)))

        return SafStr(str(self.value))


class SafBool(SafNum):
    status: bool

    def __init__(self) -> None:
        raise RuntimeError("SafBool should not be invoked directly")

    @staticmethod
    def init(ctx: NativeContext, inp: SafBaseObject) -> SafBool:
        return cast("SafBool", ctx.invoke_spec(inp, UnarySpec.bool))

    @classmethod
    def _create(cls, value: bool) -> SafBool:
        self = cls.__new__(cls)
        self.status = value
        self.value = int(self.status)

        SafObject.__init__(self, str(self.status).lower())
        return self

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(self.type.name)

    @spec_meth(FormatSpec.str)
    def str(self, ctx: NativeContext) -> SafStr:
        return self.repr(ctx)

    @spec_meth(UnarySpec.bool)
    def bool(self, ctx: NativeContext) -> SafBool:
        return self


class SafStr(SafObject):
    def __init__(self, value: str) -> None:
        super().__init__("str")

        self.value = value.encode("ascii").decode("unicode_escape")

    @staticmethod
    def init(ctx: NativeContext, inp: SafBaseObject) -> SafStr:
        try:
            return SafStr(inp.str_spec(ctx))
        except UnicodeDecodeError as e:
            raise SafulateValueError(str(e)) from None

    @spec_meth(FormatSpec.hash)
    def hash(self, ctx: NativeContext) -> SafNum:
        return SafNum(hash((self.__class__, self.value)))

    @spec_meth(CallSpec.altcall)
    def altcall(self, ctx: NativeContext, idx: SafBaseObject) -> SafStr:
        if not isinstance(idx, SafNum):
            raise SafulateTypeError(f"Expected num, got {idx.repr_spec(ctx)} instead")

        return SafStr(self.value[int(idx.value)])

    @spec_meth(BinarySpec.add)
    def add(self, ctx: NativeContext, other: SafBaseObject) -> SafStr:
        if not isinstance(other, SafStr):
            other = ctx.invoke_spec(other, FormatSpec.str)
        if not isinstance(other, SafStr):
            raise SafulateValueError(
                f"{other.repr_spec(ctx)} could not be converted into a string"
            )

        return SafStr(self.value + other.value)

    @spec_meth(BinarySpec.mul)
    def mul(self, ctx: NativeContext, other: SafBaseObject) -> SafStr:
        if not isinstance(other, SafNum):
            raise SafulateValueError("Multiply is not defined for string and this type")

        if other.value % 1 != 0:
            raise SafulateValueError(
                "Cannot multiply string by a float, must be integer"
            )

        return SafStr(self.value * int(other.value))

    @spec_meth(CallSpec.iter)
    def iter(self, ctx: NativeContext) -> SafIterator:
        return SafIterator(SafStr(char) for char in self.value)

    @spec_meth(UnarySpec.bool)
    def bool(self, ctx: NativeContext) -> SafBool:
        return true if (len(self.value) != 0) else false

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(repr(self.value))

    @spec_meth(FormatSpec.str)
    def str(self, ctx: NativeContext) -> SafStr:
        return SafStr(self.value)

    @spec_meth(BinarySpec.eq)
    def eq(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        return (
            true if (isinstance(other, SafStr) and other.value == self.value) else false
        )

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
        return true if (self.value.endswith(sub.value)) else false

    @public_method("index")
    def index(self, ctx: NativeContext, sub: SafBaseObject) -> SafBaseObject:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str, received {sub.repr_spec(ctx)} instead"
            )
        return SafNum(int(self.value.index(sub.value)))

    @public_method("is_alnum")
    def isalnum(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.isalnum()) else false

    @public_method("is_alpha")
    def isalpha(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.isalpha()) else false

    @public_method("is_ascii")
    def isascii(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.isascii()) else false

    @public_method("is_decimal")
    def isdecimal(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.isdecimal()) else false

    @public_method("is_digit")
    def isdigit(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.isdigit()) else false

    @public_method("is_lower")
    def islower(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.islower()) else false

    @public_method("is_numeric")
    def isnumeric(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.isnumeric()) else false

    @public_method("is_space")
    def isspace(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.isspace()) else false

    @public_method("is_title")
    def istitle(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.istitle()) else false

    @public_method("is_upper")
    def isupper(self, ctx: NativeContext) -> SafBool:
        return true if (self.value.isupper()) else false

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


class SafEllipsis(SafObject):
    def __init__(self) -> None:
        super().__init__("ellipsis")

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr("<ellipsis>")


# region Structures


class SafIterator(SafObject):
    def __init__(self, value: Iterator[SafBaseObject]) -> None:
        super().__init__("generator")

        self.value = value

    @spec_meth(CallSpec.next)
    def next(self, ctx: NativeContext) -> SafBaseObject:
        try:
            return next(self.value)
        except StopIteration:
            raise SafulateBreakoutError(1, ctx.token)

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr("<generator>")


class _SafIterable(SafObject):
    value: list[SafBaseObject] | tuple[SafBaseObject]

    @spec_meth(FormatSpec.hash)
    def hash(self, ctx: NativeContext) -> SafNum:
        return SafNum(hash((self.__class__, self.value)))

    @spec_meth(UnarySpec.bool)
    def bool(self, ctx: NativeContext) -> SafBool:
        return true if (len(self.value) != 0) else false

    @spec_meth(CallSpec.altcall)
    def altcall(self, ctx: NativeContext, idx: SafBaseObject) -> SafBaseObject:
        if not isinstance(idx, SafNum):
            raise SafulateTypeError(f"Expected num, got {idx.repr_spec(ctx)} instead.")

        try:
            return self.value[int(idx.value)]
        except IndexError:
            raise SafulateIndexError(f"Index {idx.repr_spec(ctx)} is out of range")

    @spec_meth(CallSpec.iter)
    def iter(self, ctx: NativeContext) -> SafIterator:
        return SafIterator(obj for obj in self.value)

    @public_property("len")
    def len(self, ctx: NativeContext) -> SafNum:
        return SafNum(len(self.value))

    @spec_meth(BinarySpec.has_item)
    def has_item(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        return true if other in self.value else false


class SafTuple(_SafIterable):
    value: tuple[SafBaseObject, ...]

    def __init__(self, value: tuple[SafBaseObject, ...]) -> None:
        super().__init__("tuple")

        self.value = value  # pyright: ignore[reportIncompatibleVariableOverride]

    @staticmethod
    def init(ctx: NativeContext, *items: SafBaseObject) -> SafTuple:
        return SafTuple(items)

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(
            "("
            + ", ".join(
                [
                    cast("SafStr", ctx.invoke_spec(val, FormatSpec.repr)).value
                    for val in self.value
                ]
            )
            + ")"
        )


class SafList(_SafIterable):
    def __init__(self, value: list[SafBaseObject]) -> None:
        super().__init__("list")

        self.value: list[SafBaseObject] = value  # pyright: ignore[reportIncompatibleVariableOverride]

    @staticmethod
    def init(ctx: NativeContext, *items: SafBaseObject) -> SafList:
        return SafList(list(items))

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

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(
            "["
            + ", ".join(
                [
                    cast("SafStr", ctx.invoke_spec(val, FormatSpec.repr)).value
                    for val in self.value
                ]
            )
            + "]"
        )


class SafFunc(SafObject):
    def __init__(
        self,
        name: Token | None | SafBaseObject,
        params: list[ASTFuncDecl_Param],
        body: ASTBlock | Callable[Concatenate[NativeContext, ...], SafBaseObject],
        parent: SafBaseObject | None = None,
        partial_args: tuple[SafBaseObject, ...] | None = None,
        partial_kwargs: dict[str, SafBaseObject] | None = None,
    ) -> None:
        match name:
            case SafBaseObject():
                name_value = name
            case Token():
                name_value = SafStr(name.lexme)
            case None:
                name_value = null

        super().__init__("func", {"name": name_value})

        self.params = params
        self.body = body
        self.partial_args = partial_args or ()
        self.partial_kwargs = partial_kwargs or {}
        self.__parent__ = parent

    @staticmethod
    def _resolve_default(
        default: ASTNode | None | SafBaseObject,
        visitor: ASTVisitor,
        error_msg_callback: Callable[[], str],
    ) -> SafBaseObject:
        if default is None:
            raise SafulateValueError(error_msg_callback())

        if isinstance(default, SafBaseObject):
            return default
        if type(default) is ASTBlock:
            try:
                return default.visit(visitor)
            except SafulateInvalidReturn as e:
                return e.value

        return default.visit(visitor)

    def validate_params(
        self, ctx: NativeContext, *init_args: SafBaseObject, **kwargs: SafBaseObject
    ) -> dict[str, SafBaseObject]:
        return self._validate_params(ctx, self.params, init_args, kwargs)

    @classmethod
    def _validate_params(
        cls,
        ctx: NativeContext,
        params: list[ASTFuncDecl_Param],
        init_args: tuple[SafBaseObject, ...],
        kwargs: dict[str, SafBaseObject],
    ) -> dict[str, SafBaseObject]:
        args = list(init_args)
        passable_params: dict[str, SafBaseObject] = {}

        for param in params:
            if param.type is ParamType.vararg:
                passable_params[param.name.lexme] = SafList(args)
                args = []
            elif param.type is ParamType.varkwarg:
                passable_params[param.name.lexme] = SafDict.from_data(ctx, kwargs)
                kwargs = {}
            elif args:
                if not param.is_arg:
                    raise SafulateValueError(
                        f"Extra positional argument was passed: {args[0].repr_spec(ctx)}"
                    )
                arg = args.pop(0)
                passable_params[param.name.lexme] = arg
            elif kwargs:
                if not param.is_kwarg:
                    passable_params[param.name.lexme] = cls._resolve_default(
                        param.default,
                        ctx.interpreter,
                        lambda: f"Required positional argument was not passed: {param.name.lexme!r}",
                    )
                else:
                    if param.name.lexme not in kwargs:
                        passable_params[param.name.lexme] = cls._resolve_default(
                            param.default,
                            ctx.interpreter,
                            lambda: f"Required {param.type.to_arg_type_str()}argument was not passed: {param.name.lexme!r}",
                        )
                    else:
                        passable_params[param.name.lexme] = kwargs.pop(param.name.lexme)
            else:
                passable_params[param.name.lexme] = cls._resolve_default(
                    param.default,
                    ctx.interpreter,
                    lambda: f"Required {param.type.to_arg_type_str()}argument was not passed: {param.name.lexme!r}",
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
            name=self.public_attrs["name"],
            params=self.params,
            body=self.body,
            parent=self.public_attrs["parent"],
            partial_args=args,
            partial_kwargs=kwargs,
        )

    @spec_meth(FormatSpec.hash)
    def hash(self, ctx: NativeContext) -> SafNum:
        return SafNum(
            hash(
                (
                    self.__class__,
                    self.params,
                    self.body,
                    self.partial_args,
                    self.partial_kwargs,
                )
            )
        )

    @spec_meth(CallSpec.altcall)
    def altcall(
        self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
    ) -> SafBaseObject:
        return self.with_partial_params(
            (*self.partial_args, *args), self.partial_kwargs | kwargs
        )

    def get_scope(self, ctx: NativeContext) -> SafObject:
        scope = SafObject(f"function scope @ {self.repr_spec(ctx)}")
        scope.set_parent(self.__parent__)
        return scope

    @spec_meth(CallSpec.call)
    def call(
        self, ctx: NativeContext, *args: SafBaseObject, **kwargs: SafBaseObject
    ) -> SafBaseObject:
        params = self.validate_params(
            ctx,
            *self.partial_args,
            *args,
            **self.partial_kwargs,
            **kwargs,
        )

        if isinstance(self.body, Callable):
            return self.body(ctx, *args, **kwargs)

        ret_value = null
        with ctx.interpreter.scope(self.get_scope(ctx)):
            for param, value in params.items():
                ctx.interpreter.env.declare(param)
                ctx.interpreter.env[param] = value

            try:
                ctx.interpreter.visit_program(self.body)
            except SafulateInvalidReturn as r:
                ret_value = r.value

        return ret_value

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        name = self.public_attrs["name"]
        suffix = f" {name.repr_spec(ctx)}" if isinstance(name, SafStr) else ""
        return SafStr(f"<func{suffix}>")

    @public_property("partial_args")
    def partial_args_prop(self, ctx: NativeContext) -> SafTuple:
        return SafTuple(self.partial_args)

    @public_property("partial_kwargs")
    def partial_kwargs_prop(self, ctx: NativeContext) -> SafDict:
        return SafDict.from_data(ctx, self.partial_kwargs)

    @public_method("without_partials")
    def without_partials(self, ctx: NativeContext) -> SafFunc:
        return self.with_partial_params((), {})

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

    @staticmethod
    def init(ctx: NativeContext, func: SafBaseObject) -> SafProperty:
        if not isinstance(func, SafFunc):
            raise SafulateTypeError(
                f"Expected func, got {func.repr_spec(ctx)} instead."
            )

        return SafProperty(func)

    @spec_meth(FormatSpec.hash)
    def hash(self, ctx: NativeContext) -> SafNum:
        return SafNum(hash((self.__class__, self.func)))

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"<property {self.func.repr_spec(ctx)}>")

    @spec_meth(CallSpec.get)
    def get_spec(self, ctx: NativeContext) -> SafBaseObject:
        return ctx.invoke(self.func)

    @public_property("func")
    def func_prop(self, ctx: NativeContext) -> SafBaseObject:
        return self.func


MISSING: Any = object()
null = SafNull._create()
true = SafBool._create(True)
false = SafBool._create(False)


class SafDict(SafObject):
    data: dict[
        int | float, tuple[SafBaseObject, SafBaseObject]
    ]  # dict[hash, (key, value)]

    def __init__(self) -> None:
        super().__init__("dict")

        self.data = {}

    @staticmethod
    def init(ctx: NativeContext, **items: SafBaseObject) -> SafDict:
        return SafDict.from_data(ctx, items)

    @classmethod
    def from_data(
        cls,
        ctx: NativeContext,
        initial: dict[SafBaseObject, SafBaseObject] | dict[str, SafBaseObject],
    ) -> Self:
        self = cls()
        for key, value in initial.items():
            key = SafStr(key) if isinstance(key, str) else key
            self.set(ctx, key, value)
        return self

    @spec_meth(FormatSpec.hash)
    def hash(self, ctx: NativeContext) -> SafNum:
        return SafNum(hash((self.__class__, self.data)))

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(
            "{"
            + ", ".join(
                f"{key.repr_spec(ctx)}:{value.repr_spec(ctx)}"
                for _, (key, value) in self.data.items()
            )
            + "}"
        )

    @spec_meth(CallSpec.altcall)
    def altcall(
        self, ctx: NativeContext, key: SafBaseObject, default: SafBaseObject = null
    ) -> SafBaseObject:
        return self.get(ctx, key, default)

    @public_method("get")
    def get(
        self, ctx: NativeContext, key: SafBaseObject, default: SafBaseObject = null
    ) -> SafBaseObject:
        try:
            return self.data[key.hash_spec(ctx)][1]
        except KeyError:
            return default

    @public_method("set")
    def set(
        self, ctx: NativeContext, key: SafBaseObject, value: SafBaseObject
    ) -> SafBaseObject:
        self.data[key.hash_spec(ctx)] = (key, value)
        return value

    @public_method("keys")
    def keys(self, ctx: NativeContext) -> SafList:
        return SafList([key for (key, _) in list(self.data.values())])

    @public_method("values")
    def values(self, ctx: NativeContext) -> SafList:
        return SafList([value for (_, value) in list(self.data.values())])

    @public_method("items")
    def items(self, ctx: NativeContext) -> SafList:
        return SafList([SafTuple(entry) for entry in list(self.data.values())])

    @public_method("pop")
    def pop(
        self,
        ctx: NativeContext,
        key: SafBaseObject,
        default: SafBaseObject | None = None,
    ) -> SafBaseObject:
        try:
            return self.data.pop(key.hash_spec(ctx))[1]
        except KeyError:
            if default is None:
                raise SafulateKeyError(f"Key {key.repr_spec(ctx)} was not found")
            return default

    @spec_meth(CallSpec.iter)
    def iter(self, ctx: NativeContext) -> SafIterator:
        return SafIterator(obj for obj in self.keys(ctx).value)

    @spec_meth(BinarySpec.has_item)
    def has_item(self, ctx: NativeContext, other: SafBaseObject) -> SafBool:
        return true if other.hash_spec(ctx) in self.data else false

    @spec_meth(UnarySpec.bool)
    def bool(self, ctx: NativeContext) -> SafBool:
        return true if (self.data) else false


# region Error


class SafPythonError(SafObject):
    def __init__(self, error: str, msg: str, obj: SafBaseObject = null) -> None:
        super().__init__(error, {"value": obj, "msg": SafStr(msg)})

    @spec_meth(FormatSpec.str)
    def str(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"{self.type.name}: {self.public_attrs['msg'].str_spec(ctx)}")

    @spec_meth(FormatSpec.repr)
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(
            f"<{self.type.name} msg={self.public_attrs['msg'].repr_spec(ctx)} value={self.public_attrs['value'].repr_spec(ctx)}>"
        )
