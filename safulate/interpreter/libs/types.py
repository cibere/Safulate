from __future__ import annotations

TYPE_CHECKING = False
if TYPE_CHECKING:
    from safulate.interpreter import NativeContext, SafModule

code = """
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
"""


def load(ctx: NativeContext) -> SafModule:
    return ctx.eval(code, name="<builtin module types>").module_obj
