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


@exporter("print_globals")
def print_globals(ctx: NativeContext) -> Value:
    env = ctx.interpreter.env
    while env.parent is not None:
        env = env.parent

    print(env.values.keys())
    return NullValue()


@exporter("print_privates")
def print_privates(ctx: NativeContext, obj: Value) -> Value:
    print(obj.private_attrs.keys())
    return NullValue()


@exporter("print_specs")
def print_specs(ctx: NativeContext, obj: Value) -> Value:
    print(obj.specs.keys())
    return NullValue()


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

    return ObjectValue(obj_name)


@exporter("assert")
def assert_(ctx: NativeContext, obj: Value, message: Value = NullValue()) -> Value:
    if not obj.truthy():
        raise SafulateAssertionError(message)
    return NullValue()
