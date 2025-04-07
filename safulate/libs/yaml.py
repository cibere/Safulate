from safulate import SafulateError
from safulate.libs._msgspec_wrapper import make_exporter


class SafulateYamlDecodeError(SafulateError): ...


class SafulateYamlEncodeError(SafulateError): ...


exporter = make_exporter(
    "yaml", encode_error=SafulateYamlEncodeError, decode_error=SafulateYamlDecodeError
)
