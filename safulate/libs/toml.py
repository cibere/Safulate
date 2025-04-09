from safulate import SafulateError
from safulate.libs._msgspec_wrapper import make_exporter


class SafulateTomlDecodeError(SafulateError): ...


class SafulateTomlEncodeError(SafulateError): ...


exporter = make_exporter(
    "toml", encode_error=SafulateTomlEncodeError, decode_error=SafulateTomlDecodeError
)
