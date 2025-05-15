from __future__ import annotations

from safulate import SafulateError
from safulate.interpreter.libs._msgspec_wrapper import MsgspecWrapper

TYPE_CHECKING = False
if TYPE_CHECKING:
    from safulate.interpreter import NativeContext, SafModule


class SafulateTomlDecodeError(SafulateError): ...


class SafulateTomlEncodeError(SafulateError): ...


def load(ctx: NativeContext) -> SafModule:
    return MsgspecWrapper(
        "toml",
        encode_error=SafulateTomlEncodeError,
        decode_error=SafulateTomlDecodeError,
        ctx=ctx,
    )
