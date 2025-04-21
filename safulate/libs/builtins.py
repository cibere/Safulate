from __future__ import annotations

from typing import Never

from safulate import (
    DictValue,
    Exporter,
    ListValue,
    NativeContext,
    NullValue,
    ObjectValue,
    SafulateAssertionError,
    SafulateTypeError,
    StrValue,
    Value,
    null,
)

exporter = Exporter("builtins")
exporter["null"] = null


@exporter("print")
def print_(ctx: NativeContext, *args: Value) -> Value:
    print(*[arg.str_spec(ctx) for arg in args])
    return null


@exporter("quit")
def quit_(_: NativeContext) -> Never:
    quit(1)


@exporter("list")
def list_(_: NativeContext, *values: Value) -> ListValue:
    return ListValue(list(values))


@exporter("dict")
def dict_(_: NativeContext) -> DictValue:
    return DictValue({})


@exporter("globals")
def get_globals(ctx: NativeContext) -> Value:
    return ObjectValue("globals", list(ctx.walk_envs())[-1].values)


@exporter("locals")
def get_locals(ctx: NativeContext) -> Value:
    return ObjectValue("locals", next(ctx.walk_envs()).values)


@exporter("object")
def create_object(ctx: NativeContext, name: Value = null) -> Value:
    match name:
        case StrValue():
            obj_name = name.value
        case NullValue():
            obj_name = f"Custom Object @ {ctx.token.start}"
        case _ as x:
            raise SafulateTypeError(
                f"Expected str or null for object name, received {x.repr_spec(ctx)} instead"
            )

    return ObjectValue(name=obj_name, attrs={})


@exporter("assert")
def assert_(ctx: NativeContext, obj: Value, msg: Value = null) -> Value:
    if not obj.bool_spec(ctx):
        raise SafulateAssertionError(msg.str_spec(ctx), obj=msg)
    return null


@exporter("dir")
def dir_(ctx: NativeContext, obj: Value) -> Value:
    return ListValue([StrValue(attr) for attr in obj.public_attrs])


@exporter("repr")
def repr_(ctx: NativeContext, obj: Value) -> Value:
    return obj.run_spec("repr", StrValue, ctx)


@exporter("str")
def str_(ctx: NativeContext, obj: Value) -> Value:
    return obj.run_spec("str", StrValue, ctx)


@exporter("kwtest")
def kwtest(
    ctx: NativeContext,
    first: Value = null,
    second: Value = null,
    third: Value = null,
    fourth: Value = null,
    fifth: Value = null,
    sixth: Value = null,
) -> Value:
    return ListValue([first, second, third, fourth, fifth, sixth])
