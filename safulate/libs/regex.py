from __future__ import annotations

import re
import sys

from safulate import (
    NativeContext,
    SafBaseObject,
    SafBool,
    SafDict,
    SafList,
    SafNull,
    SafNum,
    SafObject,
    SafStr,
    SafulateTypeError,
    null,
    public_method,
    public_property,
    spec_meth,
)

types_code = """
struct RegexTypes(){
    pub pattern = type(r"");
    pub match = type(r".*".match("hi"));
}

pub types = RegexTypes();
"""


class SafPattern(SafObject):
    def __init__(self, pattern: re.Pattern[str]) -> None:
        super().__init__("regex pattern")

        self.pattern = pattern

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"<regex pattern {self.pattern!r}>")

    @spec_meth("str")
    def str(self, ctx: NativeContext) -> SafStr:
        return self.get_pattern_prop(ctx)

    @public_property("pattern")
    def get_pattern_prop(self, ctx: NativeContext) -> SafStr:
        return SafStr(self.pattern.pattern)

    @public_method("search")
    def search(
        self,
        ctx: NativeContext,
        sub: SafBaseObject,
        start: SafBaseObject = null,
        end: SafBaseObject = null,
    ) -> SafMatch | SafNull:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str for substring, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(start, SafNull | SafNum):
            raise SafulateTypeError(
                f"Expected num or null for start pos, got {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, SafNull | SafNum):
            raise SafulateTypeError(
                f"Expected num or null for end pos, got {end.repr_spec(ctx)} instead"
            )

        match = self.pattern.search(
            sub.value,
            0 if isinstance(start, SafNull) else int(start.value),
            sys.maxsize if isinstance(end, SafNull) else int(end.value),
        )
        if match is None:
            return null

        return SafMatch(match, self)

    @public_method("match")
    def match(
        self,
        ctx: NativeContext,
        sub: SafBaseObject,
        start: SafBaseObject = null,
        end: SafBaseObject = null,
    ) -> SafMatch | SafNull:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str for substring, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(start, SafNull | SafNum):
            raise SafulateTypeError(
                f"Expected num or null for start pos, got {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, SafNull | SafNum):
            raise SafulateTypeError(
                f"Expected num or null for end pos, got {end.repr_spec(ctx)} instead"
            )

        match = self.pattern.match(
            sub.value,
            0 if isinstance(start, SafNull) else int(start.value),
            sys.maxsize if isinstance(end, SafNull) else int(end.value),
        )
        if match is None:
            return null

        return SafMatch(match, self)

    @public_method("fullmatch")
    def fullmatch(
        self,
        ctx: NativeContext,
        sub: SafBaseObject,
        start: SafBaseObject = null,
        end: SafBaseObject = null,
    ) -> SafMatch | SafNull:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str for substring, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(start, SafNull | SafNum):
            raise SafulateTypeError(
                f"Expected num or null for start pos, got {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, SafNull | SafNum):
            raise SafulateTypeError(
                f"Expected num or null for end pos, got {end.repr_spec(ctx)} instead"
            )

        match = self.pattern.fullmatch(
            sub.value,
            0 if isinstance(start, SafNull) else int(start.value),
            sys.maxsize if isinstance(end, SafNull) else int(end.value),
        )
        if match is None:
            return null

        return SafMatch(match, self)

    @public_method("find_all")
    def find_all(
        self,
        ctx: NativeContext,
        sub: SafBaseObject,
        start: SafBaseObject = null,
        end: SafBaseObject = null,
    ) -> SafList:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str for sub, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(start, SafNull | SafNum):
            raise SafulateTypeError(
                f"Expected num or null for start pos, got {start.repr_spec(ctx)} instead"
            )
        if not isinstance(end, SafNull | SafNum):
            raise SafulateTypeError(
                f"Expected num or null for end pos, got {end.repr_spec(ctx)} instead"
            )

        return SafList(
            [
                SafMatch(match, self)
                for match in self.pattern.findall(
                    sub.value,
                    0 if isinstance(start, SafNull) else int(start.value),
                    sys.maxsize if isinstance(end, SafNull) else int(end.value),
                )
            ]
        )

    @public_method("split")
    def split(
        self, ctx: NativeContext, sub: SafBaseObject, max: SafBaseObject = null
    ) -> SafBaseObject:
        if not isinstance(sub, SafStr):
            raise SafulateTypeError(
                f"Expected str for sub, got {sub.repr_spec(ctx)} instead"
            )
        if not isinstance(max, SafNum | SafNull):
            raise SafulateTypeError(
                f"Expected str for max, got {max.repr_spec(ctx)} instead"
            )

        return SafList(
            [
                SafStr(val)
                for val in self.pattern.split(
                    sub.value, 0 if isinstance(max, SafNull) else 1
                )
            ]
        )

    # @public_method("sub")
    # def sub(self, ctx: NativeContext, sub: SafBaseObject) -> SafBaseObject:
    #     if not isinstance(sub, SafStr):
    #         raise SafulateTypeError(f"Expected str for sub, got {sub.repr_spec(ctx)} instead")
    #     self.pattern.sub()

    @public_property("groups")
    def groups(self, ctx: NativeContext) -> SafList:
        return SafList([SafStr(group) for group in self.pattern.groupindex])


class SafMatch(SafObject):
    def __init__(self, match: re.Match[str], pattern: SafPattern) -> None:
        super().__init__("regex match")

        self.match = match
        self.pattern = pattern

    @spec_meth("repr")
    def repr(self, ctx: NativeContext) -> SafStr:
        return SafStr(f"<Match groups={self.groups(ctx).repr_spec(ctx)}>")

    @public_property("pattern")
    def get_pattern_prop(self, ctx: NativeContext) -> SafPattern:
        return self.pattern

    @public_property("start_pos")
    def start_pos(self, ctx: NativeContext) -> SafNum:
        return SafNum(self.match.pos)

    @public_property("end_pos")
    def end_pos(self, ctx: NativeContext) -> SafNum:
        return SafNum(self.match.endpos)

    @public_method("groups")
    def groups(self, ctx: NativeContext) -> SafList:
        return SafList(
            [
                SafStr(val) if isinstance(val, str) else null
                for val in self.match.groups()
            ]
        )

    @public_method("as_dict")
    def as_dict(self, ctx: NativeContext) -> SafDict:
        return SafDict(
            {
                item.value[0].str_spec(ctx): item.value[1]
                for item in self.groups(ctx).value
                if isinstance(item, SafList)
            }
        )

    @spec_meth("iter")
    def iter(self, ctx: NativeContext) -> SafList:
        return self.groups(ctx)

    @spec_meth("bool")
    def bool(self, ctx: NativeContext) -> SafBool:
        return SafBool(self.match)

    @spec_meth("altcall")
    def altcall(self, ctx: NativeContext, key: SafBaseObject) -> SafBaseObject:
        match key:
            case SafStr():
                val = self.match[key.value]
                return SafStr(val) if isinstance(val, str) else null
            case SafNum():
                return self.groups(ctx).value[int(key.value)]
            case _:
                raise SafulateTypeError(
                    f"Expected num or str, got {key.repr_spec(ctx)} instead"
                )


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
