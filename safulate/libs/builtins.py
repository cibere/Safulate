from __future__ import annotations
from typing import TYPE_CHECKING
from safulate.tokens import NullToken, StringToken, ContainerToken, Token, ListToken
import msgspec
import runpy
from pathlib import Path
from safulate.lib_exporter import LibraryExporter

if TYPE_CHECKING:
    from ..executer import Executer

libs_folder = Path(__file__).parent

exporter = LibraryExporter("builtins")


@exporter("print")
def print_func(exe: Executer, content: Token) -> NullToken:
    print(content.to_str(exe).value)
    return NullToken()


@exporter("_dump")
def dump_vars(exe: Executer) -> NullToken:
    print(
        msgspec.json.format(
            msgspec.json.encode(
                {key: val for key, val in exe.variables.items()},
                enc_hook=lambda v: repr(v),
            )
        ).decode()
    )
    return NullToken()


@exporter("import")
def import_lib(exe: Executer, location: StringToken) -> ContainerToken:
    for module in libs_folder.glob("*.py"):
        if module.name.removesuffix(".py") == location.value:
            globals = runpy.run_path(str(module.absolute()))
            exporter = globals.get("exporter")
            if exporter is None:
                raise RuntimeError(
                    f"Module {location.value!r} does not have an exporter"
                )
            if not isinstance(exporter, LibraryExporter):
                raise RuntimeError(
                    f"Module {location.value!r} does not have a valid exporter"
                )
            return exporter.to_container()

    raise RuntimeError(f"Module {location.value!r} was not found")


@exporter("dir")
def dir_func(exe: Executer, obj: Token) -> ListToken:
    return ListToken(
        value=[StringToken(name) for name in obj.public_attrs.keys()],
    )
