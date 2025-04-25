from __future__ import annotations

from typing import Never

from safulate import (
    DictValue,
    ListValue,
    NativeContext,
    NumValue,
    ObjectValue,
    SafulateAssertionError,
    StrValue,
    Value,
    false,
    null,
    true,
)
from safulate.values import public_method


class Builtins(ObjectValue):
    def __init__(self) -> None:
        super().__init__("builtins", {"null": null, "true": true, "false": false})

    @public_method("print")
    def print_(self, ctx: NativeContext, *args: Value) -> Value:
        print(*[arg.str_spec(ctx) for arg in args])
        return null

    @public_method("quit")
    def quit_(self, ctx: NativeContext) -> Never:
        quit(1)

    @public_method("list")
    def list_(self, ctx: NativeContext, *values: Value) -> ListValue:
        return ListValue(list(values))

    @public_method("dict")
    def dict_(self, ctx: NativeContext, **data: Value) -> DictValue:
        return DictValue(data)

    @public_method("globals")
    def get_globals(self, ctx: NativeContext) -> Value:
        return DictValue(dict(list(ctx.walk_envs())[-1].values.items()))

    @public_method("locals")
    def get_locals(self, ctx: NativeContext) -> Value:
        return DictValue(dict(next(ctx.walk_envs()).values.items()))

    @public_method("rollback_scope")
    def rollback_scope(self, ctx: NativeContext) -> Value:
        if ctx.env.parent:
            ctx.interpreter.env = ctx.env.parent
        return null

    @public_method("object")
    def create_object(self, ctx: NativeContext, name: Value = null) -> Value:
        return ObjectValue(
            name=f"Custom Object @ {ctx.token.start}"
            if name is null
            else name.str_spec(ctx),
            attrs={},
        )

    @public_method("assert")
    def assert_(self, ctx: NativeContext, obj: Value, msg: Value = null) -> Value:
        if not obj.bool_spec(ctx):
            raise SafulateAssertionError(msg.str_spec(ctx), obj=msg)
        return null

    @public_method("dir")
    def dir_(self, ctx: NativeContext, obj: Value, full: Value = null) -> Value:
        attrs = obj.public_attrs
        if isinstance(full, NumValue) and int(full.value) == 1:
            attrs.update({f"${key}": val for key, val in obj.private_attrs.items()})
            attrs.update({f"%{key}": val for key, val in obj.specs.items()})

        return ListValue([StrValue(attr) for attr in attrs])

    @public_method("type")
    def get_type(self, ctx: NativeContext, obj: Value) -> Value:
        return obj.specs["type"]


def load(ctx: NativeContext) -> ObjectValue:
    return Builtins()
