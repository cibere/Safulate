from __future__ import annotations

from typing import TYPE_CHECKING, Concatenate, Never

from .values import ListValue, NativeFunc, NullValue, ObjValue, Value

if TYPE_CHECKING:
    from collections.abc import Callable

    from .native_context import NativeContext

natives: list[NativeFunc] = []


def native_func(
    name: str, arity: int | None
) -> Callable[[Callable[Concatenate[NativeContext, ...], Value]], Callable[..., Value]]:
    def inner(func: Callable[..., Value]) -> Callable[..., Value]:
        natives.append(NativeFunc(name, arity, func))
        return func

    return inner


@native_func("print", None)
def print_(_: NativeContext, *args: Value) -> Value:
    print(*[str(arg) for arg in args])
    return NullValue()


@native_func("quit", 0)
def quit_(_: NativeContext) -> Never:
    quit(1)


@native_func("list", None)
def list_(_: NativeContext, *values: Value) -> ListValue:
    return ListValue(list(values))


@native_func("print_globals", 0)
def print_globals(ctx: NativeContext) -> Value:
    env = ctx.interpreter.env
    while env.parent is not None:
        env = env.parent

    print(env.values.keys())
    return NullValue()


@native_func("print_privates", 1)
def print_privates(ctx: NativeContext, obj: Value) -> Value:
    print(obj.private_attrs.keys())
    return NullValue()


@native_func("print_specs", 1)
def print_specs(ctx: NativeContext, obj: Value) -> Value:
    print(obj.specs.keys())
    return NullValue()


@native_func("object", 0)
def create_object(ctx: NativeContext) -> Value:
    return ObjValue(ctx.token)
