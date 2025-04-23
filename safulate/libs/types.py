from __future__ import annotations

TYPE_CHECKING = False
if TYPE_CHECKING:
    from safulate import NativeContext, Value

code = """
pub get_type = type;

struct TypesModule(){
    pub str = get_type("");
    pub num = get_type(0);
    pub dict = get_type(dict());
    pub list = get_type([]);
    pub null = get_type(null);
    pub type = get_type(str);

    pub func;
    {
        pub temp_func(){}
        func = get_type(temp_func);
    }

    pub property;
    {
        prop temp_prop(){}
        property = get_type(temp_prop);
    }


    pub AssertionError = get_type(object("AssertionError"));
    pub BreakoutError = get_type(object("BreakoutError"));
    pub InvalidContinue = get_type(object("InvalidContinue"));
    pub InvalidReturn = get_type(object("InvalidReturn"));
    pub KeyError = get_type(object("KeyError"));
    pub NameError = get_type(object("NameError"));
    pub SyntaxError = get_type(object("SyntaxError"));
    pub TypeError = get_type(object("TypeError"));
    pub ValueError = get_type(object("ValueError"));
}

pub types = TypesModule();
"""


def load(ctx: NativeContext) -> Value:
    return ctx.eval(code, name="<builtin module types>")["types"]
