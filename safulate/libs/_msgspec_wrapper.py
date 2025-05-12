from __future__ import annotations

from typing import Literal

from msgspec import DecodeError, json, toml, yaml
from safulate import (
    NativeContext,
    SafBaseObject,
    SafFunc,
    SafModule,
    SafNum,
    SafStr,
    SafulateError,
    public_method,
)

types_code = """
pub {decode_error} = type(object("{decode_error}"));
pub {encode_error} = type(object("{encode_error}"));
"""


class MsgspecWrapper(SafModule):
    def __init__(
        self,
        module_name: Literal["json", "toml", "yaml"],
        *,
        encode_error: type[SafulateError],
        decode_error: type[SafulateError],
        ctx: NativeContext,
    ) -> None:
        super().__init__(
            module_name,
            attrs={
                "dump": SafFunc.from_native(
                    "dump",
                    self.dump_json_method
                    if module_name == "json"
                    else self.dump_method,
                ),
                "types": ctx.eval(
                    types_code.format(
                        decode_error=decode_error.__new__(decode_error).name,
                        encode_error=encode_error.__new__(encode_error).name,
                    ),
                    name=f"<builtin module {module_name}>",
                ).module_obj,
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
    def load_method(self, ctx: NativeContext, content: SafStr) -> SafBaseObject:
        try:
            data = self.decode(content.value)
        except DecodeError as e:
            raise self.decode_error(str(e)) from None

        return ctx.python_to_values(data)

    def dump_json_method(
        self,
        ctx: NativeContext,
        content: SafBaseObject,
        convert_reprs: SafNum = SafNum(0),
        indentation: SafNum = SafNum(2),
    ) -> SafStr:
        try:
            return SafStr(
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
        self,
        ctx: NativeContext,
        content: SafBaseObject,
        convert_reprs: SafNum = SafNum(0),
    ) -> SafStr:
        try:
            return SafStr(
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
