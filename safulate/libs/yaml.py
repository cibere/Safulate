from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from safulate.lib_exporter import LibraryExporter
from safulate.values import (
    NumValue,
    StrValue,
    Value,
)

if TYPE_CHECKING:
    from safulate.native_context import NativeContext

exporter = LibraryExporter("yaml")


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
