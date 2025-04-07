from __future__ import annotations

import yaml

from safulate import (
    Exporter,
    NativeContext,
    NumValue,
    StrValue,
    Value,
)

exporter = Exporter("yaml")


@exporter("load")
def load_yaml(ctx: NativeContext, content: StrValue) -> Value:
    data = yaml.safe_load(content.value)
    return ctx.python_to_values(data)


@exporter("dump")
def dump_json(
    ctx: NativeContext, content: Value, indent: NumValue = NumValue(2.0)
) -> StrValue:
    return StrValue(
        yaml.safe_dump(ctx.value_to_python(content), indent=int(indent.value))
    )  # seems to be returning the repr of the dumped content for some reason``
