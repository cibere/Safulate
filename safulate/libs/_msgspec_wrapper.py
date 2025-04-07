from __future__ import annotations

from typing import Literal

from msgspec import json, toml, yaml

from safulate import (
    Exporter,
    NativeContext,
    NumValue,
    StrValue,
    Value,
)


def make_exporter(module_name: Literal["json", "toml", "yaml"]) -> Exporter:
    exporter = Exporter(module_name)

    match module_name:
        case "json":
            decode = json.decode
            encode = json.encode
        case "toml":
            encode = toml.encode
            decode = toml.decode
        case "yaml":
            encode = yaml.encode
            decode = yaml.decode

    @exporter("load")
    def _load(ctx: NativeContext, content: StrValue) -> Value:  # pyright: ignore[reportUnusedFunction]
        data = decode(content.value)
        return ctx.python_to_values(data)

    if module_name == "json":

        @exporter("dump")
        def _dump(  # pyright: ignore[reportUnusedFunction]
            ctx: NativeContext,
            content: Value,
            convert_reprs: NumValue = NumValue(0),
            indentation: NumValue = NumValue(2),
        ) -> StrValue:
            return StrValue(
                json.format(
                    encode(
                        ctx.value_to_python(
                            content, repr_fallback=convert_reprs.bool_spec(ctx)
                        )
                    ),
                    indent=int(indentation.value),
                ).decode()
            )
    else:

        @exporter("dump")
        def _dump(  # pyright: ignore[reportUnusedFunction]
            ctx: NativeContext, content: Value, convert_reprs: NumValue = NumValue(0)
        ) -> StrValue:
            return StrValue(
                encode(
                    ctx.value_to_python(
                        content,
                        repr_fallback=convert_reprs.bool_spec(ctx),
                        ignore_null_attrs=module_name == "toml",
                    )
                ).decode()
            )

    return exporter
