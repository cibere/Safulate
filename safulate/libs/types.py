from __future__ import annotations

from safulate import NativeContext, SafBaseObject, SafIterable, Environment, SafFunc, SafBool, true, false

code = """
pub get_type = type;

struct TypesModule(py_is_iterable){
    pub str = get_type("");
    pub num = get_type(0);
    pub dict = get_type(dict());
    pub list = get_type(list());
    pub tuple = get_type(tuple());
    pub null = get_type(null);
    pub type = get_type(str);

    pub func;
    {
        pub temp_func(){};
        func = get_type(temp_func);
    }

    pub property;
    {
        prop temp_prop(){};
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
    pub IndexError = get_type(object("IndexError"));

    priv py_is_iterable = py_is_iterable;
    pub is_iterable(obj){
        return $py_is_iterable(obj);
    };
};

pub types = TypesModule(_py_is_iterable);
"""

def _py_is_iterable(ctx: NativeContext, obj: SafBaseObject) -> SafBool:
    return true if isinstance(obj, SafIterable) else false

def load(ctx: NativeContext) -> SafBaseObject:
    env = Environment()
    env.add_builtins()
    env['_py_is_iterable'] = SafFunc.from_native("_py_is_iterable", _py_is_iterable)
    return ctx.eval(code, name="<builtin module types>", env=env)["types"]
