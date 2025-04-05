from __future__ import annotations

from typing import TYPE_CHECKING, Never

from safulate.lib_exporter import LibraryExporter
from safulate.values import ListValue, NullValue, ObjValue, Value

if TYPE_CHECKING:
    from safulate.native_context import NativeContext


exporter = LibraryExporter("builtins")


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
def create_object(ctx: NativeContext) -> Value:
    return ObjValue(ctx.token)
