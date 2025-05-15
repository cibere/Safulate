from __future__ import annotations

from safulate import SafulateError
from safulate.interpreter.libs._msgspec_wrapper import MsgspecWrapper

TYPE_CHECKING = False
if TYPE_CHECKING:
    from safulate.interpreter import NativeContext, SafModule


class SafulateYamlDecodeError(SafulateError): ...


class SafulateYamlEncodeError(SafulateError): ...


def load(ctx: NativeContext) -> SafModule:
    return MsgspecWrapper(
        "yaml",
        encode_error=SafulateYamlEncodeError,
        decode_error=SafulateYamlDecodeError,
        ctx=ctx,
    )
