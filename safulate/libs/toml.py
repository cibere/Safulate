from __future__ import annotations

from safulate import NativeContext, ObjectValue, SafulateError
from safulate.libs._msgspec_wrapper import MsgspecWrapper


class SafulateTomlDecodeError(SafulateError): ...


class SafulateTomlEncodeError(SafulateError): ...


def load(_: NativeContext) -> ObjectValue:
    return MsgspecWrapper(
        "toml",
        encode_error=SafulateTomlEncodeError,
        decode_error=SafulateTomlDecodeError,
    )
