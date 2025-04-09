from safulate import SafulateError
from safulate.libs._msgspec_wrapper import make_exporter


class SafulateJsonDecodeError(SafulateError): ...


class SafulateJsonEncodeError(SafulateError): ...


exporter = make_exporter(
    "json", encode_error=SafulateJsonEncodeError, decode_error=SafulateJsonDecodeError
)
