from __future__ import annotations

import re

from safulate import (
    NativeContext,
    ObjectValue,
    PatternValue,
    StrValue,
    Value,
    public_method,
)

types_code = """
struct RegexTypes(){
    pub pattern = type(r"");
    pub match = type(r".*".match("hi"));
}

pub types = RegexTypes();
"""


class RegexModule(ObjectValue):
    def __init__(self, ctx: NativeContext) -> None:
        super().__init__(
            "regex",
            attrs={
                "types": ctx.eval(types_code, name="<builtin module regex>")["types"]
            },
        )

    @public_method("compile")
    def compile_(self, ctx: NativeContext, pattern: Value) -> Value:
        return PatternValue(re.compile(pattern.str_spec(ctx)))

    @public_method("escape")
    def escape(self, ctx: NativeContext, string: Value) -> StrValue:
        return StrValue(re.escape(string.str_spec(ctx)))


def load(ctx: NativeContext) -> ObjectValue:
    return RegexModule(ctx)
