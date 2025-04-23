from __future__ import annotations

from safulate import NativeContext, ObjectValue, SafulateError
from safulate.libs._msgspec_wrapper import MsgspecWrapper


class SafulateYamlDecodeError(SafulateError): ...


class SafulateYamlEncodeError(SafulateError): ...


def load(_: NativeContext) -> ObjectValue:
    return MsgspecWrapper(
        "yaml",
        encode_error=SafulateYamlEncodeError,
        decode_error=SafulateYamlDecodeError,
    )
