# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "msgspec",
# ]
# ///
from safulate.lexer import Lexer
from safulate.executer import Executer
from safulate.lib_exporter import LibraryExporter
from safulate.tokens import StringToken

# the custom library/module to add
exporter = LibraryExporter("custom_module")

# adding variables
exporter["author"] = StringToken("cibere")


# adding functions
@exporter("func_name")
def func_name(exe: Executer) -> StringToken:
    return StringToken("hi")


# safulate itself
code = """
set mod = import["custom_module"];
print[mod.author]; # prints 'cibere'
print[mod.func_name()]; # prints 'hi'
"""
lexer = Lexer(code)
lexer.start()

# turn our library/module into a container token
con = exporter.to_container()

# create an executer and give it our container
exe = Executer(additional_imports=[con])

exe.execute(*lexer.statements)
