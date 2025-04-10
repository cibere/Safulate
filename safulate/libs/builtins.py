from __future__ import annotations

from typing import Never

from safulate import (
    Exporter,
    ListValue,
    NativeContext,
    NullValue,
    ObjectValue,
    SafulateAssertionError,
    SafulateTypeError,
    StrValue,
    Value,
)

exporter = Exporter("builtins")
exporter["null"] = NullValue()


@exporter("print")
def print_(_: NativeContext, *args: Value) -> Value:
    print(*[str(arg) for arg in args])
    return NullValue()


@exporter("quit")
def quit_(_: NativeContext) -> Never:
    quit(1)


@exporter("list")
def list_(_: NativeContext, *values: Value) -> ListValue:
    return ListValue(list(values))


@exporter("globals")
def get_globals(ctx: NativeContext) -> Value:
    return ObjectValue("globals", list(ctx.walk_envs())[-1].values)


@exporter("locals")
def get_locals(ctx: NativeContext) -> Value:
    return ObjectValue("locals", next(ctx.walk_envs()).values)


@exporter("object")
def create_object(ctx: NativeContext, name: Value = NullValue()) -> Value:
    match name:
        case StrValue():
            obj_name = name.value
        case NullValue():
            obj_name = f"Custom Object @ {ctx.token.start}"
        case _ as x:
            raise SafulateTypeError(
                f"Expected str or null for object name, received {x.repr_spec(ctx)} instead"
            )

    return ObjectValue(name=obj_name)


@exporter("assert")
def assert_(ctx: NativeContext, obj: Value, message: Value = NullValue()) -> Value:
    if not obj.truthy():
        raise SafulateAssertionError(message)
    return NullValue()


@exporter("dir")
def dir_(ctx: NativeContext, obj: Value) -> Value:
    return ListValue([StrValue(attr) for attr in obj.public_attrs])
