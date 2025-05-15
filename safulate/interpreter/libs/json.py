from __future__ import annotations

from safulate import SafulateError
from safulate.interpreter.libs._msgspec_wrapper import MsgspecWrapper

TYPE_CHECKING = False
if TYPE_CHECKING:
    from safulate.interpreter import NativeContext, SafModule


class SafulateJsonDecodeError(SafulateError): ...


class SafulateJsonEncodeError(SafulateError): ...


def load(ctx: NativeContext) -> SafModule:
    return MsgspecWrapper(
        "json",
        encode_error=SafulateJsonEncodeError,
        decode_error=SafulateJsonDecodeError,
        ctx=ctx,
    )
