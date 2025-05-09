from __future__ import annotations

from safulate import NativeContext, SafObject, SafulateError
from safulate.libs._msgspec_wrapper import MsgspecWrapper


class SafulateTomlDecodeError(SafulateError): ...


class SafulateTomlEncodeError(SafulateError): ...


def load(ctx: NativeContext) -> SafObject:
    return MsgspecWrapper(
        "toml",
        encode_error=SafulateTomlEncodeError,
        decode_error=SafulateTomlDecodeError,
        ctx=ctx,
    )
