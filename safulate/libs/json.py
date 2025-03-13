from __future__ import annotations
from typing import TYPE_CHECKING
from safulate.lib_exporter import LibraryExporter
from safulate.tokens import StringToken, Token, DictToken, python_to_token, ListToken
import json

if TYPE_CHECKING:
    from safulate.executer import Executer

exporter = LibraryExporter("hello")
exporter["author"] = StringToken("cibere")


@exporter("load")
def load_json(exe: Executer, content: StringToken) -> Token:
    data = json.loads(content.value)
    return python_to_token(data)


@exporter("dump")
def dump_json(exe: Executer, content: DictToken | ListToken) -> StringToken:
    return StringToken(json.dumps(content.to_python(exe)))


@exporter("dump_human_readable")
def dump_human_json(exe: Executer, content: DictToken | ListToken) -> StringToken:
    return StringToken(json.dumps(content.to_python(exe), indent=4))
