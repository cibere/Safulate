from __future__ import annotations

from typing import Never

from safulate import SafulateAssertionError
from safulate.interpreter import (
    NativeContext,
    SafBaseObject,
    SafDict,
    SafList,
    SafModule,
    SafNum,
    SafStr,
    SafTuple,
    SafType,
    false,
    null,
    public_method,
    true,
)


class Builtins(SafModule):
    def __init__(self) -> None:
        super().__init__(
            "builtins",
            {
                "null": null,
                "true": true,
                "false": false,
                "dict": SafDict().type,
                "list": SafList([]).type,
                "tuple": SafTuple(()).type,
                "str": SafStr("").type,
                "num": SafNum(0).type,
                "object": SafType.object_type(),
            },
        )

    @public_method("print")
    def print_(self, ctx: NativeContext, *args: SafBaseObject) -> SafBaseObject:
        print(*[arg.str_spec(ctx) for arg in args])
        return null

    @public_method("quit")
    def quit_(self, ctx: NativeContext) -> Never:
        quit(1)

    @public_method("globals")
    def get_globals(self, ctx: NativeContext) -> SafBaseObject:
        return SafDict.from_data(ctx, dict(list(ctx.walk_envs())[-1].values.items()))

    @public_method("locals")
    def get_locals(self, ctx: NativeContext) -> SafBaseObject:
        return SafDict.from_data(ctx, dict(next(ctx.walk_envs()).values.items()))

    @public_method("id")
    def get_id(self, ctx: NativeContext, obj: SafBaseObject) -> SafBaseObject:
        return SafNum(id(obj))

    @public_method("rollback_scope")
    def rollback_scope(self, ctx: NativeContext) -> SafBaseObject:
        if ctx.env.parent:
            ctx.interpreter.env = ctx.env.parent
        return null

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


def load(ctx: NativeContext) -> SafModule:
    return Builtins()
