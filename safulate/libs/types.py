from __future__ import annotations

TYPE_CHECKING = False
if TYPE_CHECKING:
    from safulate import NativeContext, SafBaseObject

code = """
struct TypesModule(){
    pub func;
    {
        pub temp_func(){};
        func = type(temp_func);
    }

    pub property;
    {
        prop temp_prop(){};
        property = type(temp_prop);
    }

    pub AssertionError = type(object("AssertionError"));
    pub BreakoutError = type(object("BreakoutError"));
    pub InvalidContinue = type(object("InvalidContinue"));
    pub InvalidReturn = type(object("InvalidReturn"));
    pub KeyError = type(object("KeyError"));
    pub NameError = type(object("NameError"));
    pub SyntaxError = type(object("SyntaxError"));
    pub TypeError = type(object("TypeError"));
    pub ValueError = type(object("ValueError"));
    pub IndexError = type(object("IndexError"));
};

pub types = TypesModule();
"""


def load(ctx: NativeContext) -> SafBaseObject:
    return ctx.eval(code, name="<builtin module types>")["types"]
