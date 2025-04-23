from __future__ import annotations

TYPE_CHECKING = False
if TYPE_CHECKING:
    from safulate import NativeContext, Value

code = """
struct TypesModule(){
    pub str = type("");
    pub num = type(0);
    pub dict = type(dict());
    priv temp_func(){}
    pub func = type($temp_func);
    pub list = type([]);
    pub null = type(null);
    pub type = type(str);
}

pub types = TypesModule();
"""


def load(ctx: NativeContext) -> Value:
    return ctx.eval(code, name="<builtin module types>")["types"]
