from __future__ import annotations

import re

from safulate import (
    NativeContext,
    SafObject,
    SafPattern,
    SafStr,
    SafBaseObject,
    public_method,
)

types_code = """
struct RegexTypes(){
    pub pattern = type(r"");
    pub match = type(r".*".match("hi"));
}

pub types = RegexTypes();
"""


class RegexModule(SafObject):
    def __init__(self, ctx: NativeContext) -> None:
        super().__init__(
            "regex",
            attrs={
                "types": ctx.eval(types_code, name="<builtin module regex>")["types"]
            },
        )

    @public_method("compile")
    def compile_(self, ctx: NativeContext, pattern: SafBaseObject) -> SafBaseObject:
        return SafPattern(re.compile(pattern.str_spec(ctx)))

    @public_method("escape")
    def escape(self, ctx: NativeContext, string: SafBaseObject) -> SafStr:
        return SafStr(re.escape(string.str_spec(ctx)))


def load(ctx: NativeContext) -> SafObject:
    return RegexModule(ctx)
