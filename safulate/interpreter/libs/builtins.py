from __future__ import annotations

from typing import Any, Never

from safulate import SafulateAssertionError, SafulateTypeError
from safulate.interpreter import (
    NativeContext,
    SafBaseObject,
    SafDict,
    SafFunc,
    SafList,
    SafModule,
    SafNum,
    SafProperty,
    SafStr,
    SafTuple,
    SafType,
    false,
    null,
    public_method,
    true,
)

_MOCK_ANY: Any = 0


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
        return SafDict.from_data(
            ctx, dict(list(ctx.env.walk_parents())[-1].public_attrs.items())
        )

    @public_method("id")
    def get_id(self, ctx: NativeContext, obj: SafBaseObject) -> SafBaseObject:
        return SafNum(id(obj))

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

    @public_method("property")
    def property(self, ctx: NativeContext, func: SafBaseObject) -> SafBaseObject:
        if not isinstance(func, SafFunc):
            raise SafulateTypeError(
                f"Expected func, received {func.repr_spec(ctx)} instead"
            )

        return SafProperty(func)


def load(ctx: NativeContext) -> SafModule:
    return Builtins()
