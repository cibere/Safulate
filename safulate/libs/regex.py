from __future__ import annotations

import re

from safulate import Exporter, NativeContext, PatternValue, StrValue, Value

exporter = Exporter("regex")


@exporter("compile")
def compile_(ctx: NativeContext, pattern: Value) -> Value:
    return PatternValue(re.compile(pattern.str_spec(ctx)))


@exporter("escape")
def escape(ctx: NativeContext, string: Value) -> StrValue:
    return StrValue(re.escape(string.str_spec(ctx)))
