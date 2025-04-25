from __future__ import annotations

from typing import Never

from safulate import (
    NativeContext,
    SafBaseObject,
    SafDict,
    SafList,
    SafNum,
    SafObject,
    SafStr,
    SafulateAssertionError,
    false,
    null,
    true,
)
from safulate.objects import public_method


class Builtins(SafObject):
    def __init__(self) -> None:
        super().__init__("builtins", {"null": null, "true": true, "false": false})

    @public_method("print")
    def print_(self, ctx: NativeContext, *args: SafBaseObject) -> SafBaseObject:
        print(*[arg.str_spec(ctx) for arg in args])
        return null

    @public_method("quit")
    def quit_(self, ctx: NativeContext) -> Never:
        quit(1)

    @public_method("list")
    def list_(self, ctx: NativeContext, *values: SafBaseObject) -> SafList:
        return SafList(list(values))

    @public_method("dict")
    def dict_(self, ctx: NativeContext, **data: SafBaseObject) -> SafDict:
        return SafDict(data)

    @public_method("globals")
    def get_globals(self, ctx: NativeContext) -> SafBaseObject:
        return SafDict(dict(list(ctx.walk_envs())[-1].values.items()))

    @public_method("locals")
    def get_locals(self, ctx: NativeContext) -> SafBaseObject:
        return SafDict(dict(next(ctx.walk_envs()).values.items()))

    @public_method("rollback_scope")
    def rollback_scope(self, ctx: NativeContext) -> SafBaseObject:
        if ctx.env.parent:
            ctx.interpreter.env = ctx.env.parent
        return null

    @public_method("object")
    def create_object(
        self, ctx: NativeContext, name: SafBaseObject = null
    ) -> SafBaseObject:
        return SafObject(
            name=f"Custom Object @ {ctx.token.start}"
            if name is null
            else name.str_spec(ctx),
            attrs={},
        )

    @public_method("assert")
    def assert_(
        self, ctx: NativeContext, obj: SafBaseObject, msg: SafBaseObject = null
    ) -> SafBaseObject:
        if not obj.bool_spec(ctx):
            raise SafulateAssertionError(msg.str_spec(ctx), obj=msg)
        return null

    @public_method("dir")
    def dir_(
        self, ctx: NativeContext, obj: SafBaseObject, full: SafBaseObject = null
    ) -> SafBaseObject:
        attrs = obj.public_attrs
        if isinstance(full, SafNum) and int(full.value) == 1:
            attrs.update({f"${key}": val for key, val in obj.private_attrs.items()})
            attrs.update({f"%{key}": val for key, val in obj.specs.items()})

        return SafList([SafStr(attr) for attr in attrs])

    @public_method("type")
    def get_type(self, ctx: NativeContext, obj: SafBaseObject) -> SafBaseObject:
        return obj.specs["type"]


def load(ctx: NativeContext) -> SafObject:
    return Builtins()
