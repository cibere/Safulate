from __future__ import annotations

import json
from typing import TYPE_CHECKING

from safulate.lib_exporter import LibraryExporter
from safulate.values import (
    NumValue,
    StrValue,
    Value,
)

if TYPE_CHECKING:
    from safulate.native_context import NativeContext

exporter = LibraryExporter("json")


@exporter("load")
def load_json(ctx: NativeContext, content: StrValue) -> Value:
    data = json.loads(content.value)
    return ctx.python_to_values(data)


@exporter("dump")
def dump_json(
    ctx: NativeContext, content: Value, indent: NumValue = NumValue(2.0)
) -> StrValue:
    return StrValue(json.dumps(ctx.value_to_python(content), indent=int(indent.value))) # seems to be returning the repr of the dumped content for some reason