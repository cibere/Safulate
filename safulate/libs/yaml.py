from __future__ import annotations

from safulate import NativeContext, SafModule, SafulateError
from safulate.libs._msgspec_wrapper import MsgspecWrapper


class SafulateYamlDecodeError(SafulateError): ...


class SafulateYamlEncodeError(SafulateError): ...


def load(ctx: NativeContext) -> SafModule:
    return MsgspecWrapper(
        "yaml",
        encode_error=SafulateYamlEncodeError,
        decode_error=SafulateYamlDecodeError,
        ctx=ctx,
    )
