from __future__ import annotations

from safulate import NativeContext, ObjectValue, SafulateError
from safulate.libs._msgspec_wrapper import MsgspecWrapper


class SafulateJsonDecodeError(SafulateError): ...


class SafulateJsonEncodeError(SafulateError): ...


def load(_: NativeContext) -> ObjectValue:
    return MsgspecWrapper(
        "json",
        encode_error=SafulateJsonEncodeError,
        decode_error=SafulateJsonDecodeError,
    )
