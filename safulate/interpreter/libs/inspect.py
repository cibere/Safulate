from __future__ import annotations

from safulate import SafulateTypeError
from safulate.interpreter import (
    NativeContext,
    SafBaseObject,
    SafFunc,
    SafModule,
    SafStr,
    null,
    public_method,
)
from safulate.parser import ParamType


class InspectModule(SafModule):
    def __init__(self) -> None:
        super().__init__(
            "inspect",
        )

    @public_method("get_signature")
    def get_sig(self, ctx: NativeContext, func: SafBaseObject) -> SafBaseObject:
        if not isinstance(func, SafFunc):
            raise SafulateTypeError(
                f"Expected func, got {func.repr_spec(ctx)} instead."
            )

        sig = ""

        name = func.public_attrs["name"]
        if name is not null:
            sig += name.str_spec(ctx)

        sig += (
            "("
            + ", ".join(
                (".." if param.type is ParamType.vararg else "")
                + ("..." if param.type is ParamType.varkwarg else "")
                + param.name.lexme
                + ("" if param.default is None else " = ...")
                for param in func.params
            )
            + ")"
        )

        return SafStr(sig)


def load(ctx: NativeContext) -> SafModule:
    return InspectModule()
