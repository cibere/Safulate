from __future__ import annotations

from typing import Literal

from msgspec import DecodeError, json, toml, yaml

from safulate import (
    FuncValue,
    NativeContext,
    NumValue,
    ObjectValue,
    SafulateError,
    StrValue,
    Value,
    public_method,
)


class MsgspecWrapper(ObjectValue):
    def __init__(
        self,
        module_name: Literal["json", "toml", "yaml"],
        encode_error: type[SafulateError],
        decode_error: type[SafulateError],
    ) -> None:
        super().__init__(
            module_name,
            attrs={
                "dump": FuncValue.from_native(
                    "dump",
                    self.dump_json_method
                    if module_name == "json"
                    else self.dump_method,
                )
            },
        )

        self.module_name = module_name
        self.encode_error = encode_error
        self.decode_error = decode_error

        match module_name:
            case "json":
                self.decode = json.decode
                self.encode = json.encode
            case "toml":
                self.encode = toml.encode
                self.decode = toml.decode
            case "yaml":
                self.encode = yaml.encode
                self.decode = yaml.decode

    @public_method("load")
    def load_method(self, ctx: NativeContext, content: StrValue) -> Value:
        try:
            data = self.decode(content.value)
        except DecodeError as e:
            raise self.decode_error(str(e)) from None

        return ctx.python_to_values(data)

    def dump_json_method(
        self,
        ctx: NativeContext,
        content: Value,
        convert_reprs: NumValue = NumValue(0),
        indentation: NumValue = NumValue(2),
    ) -> StrValue:
        try:
            return StrValue(
                json.format(
                    self.encode(
                        ctx.value_to_python(
                            content, repr_fallback=convert_reprs.bool_spec(ctx)
                        )
                    ),
                    indent=int(indentation.value),
                ).decode()
            )
        except DecodeError as e:
            raise self.encode_error(str(e)) from None

    def dump_method(
        self, ctx: NativeContext, content: Value, convert_reprs: NumValue = NumValue(0)
    ) -> StrValue:
        try:
            return StrValue(
                self.encode(
                    ctx.value_to_python(
                        content,
                        repr_fallback=convert_reprs.bool_spec(ctx),
                        ignore_null_attrs=self.module_name == "toml",
                    )
                ).decode()
            )
        except DecodeError as e:
            raise self.encode_error(str(e)) from None
