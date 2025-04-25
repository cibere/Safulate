from __future__ import annotations

import runpy
from inspect import isfunction
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import SafulateImportError
from .objects import SafObject

if TYPE_CHECKING:
    from .native_context import NativeContext

__all__ = ("LibManager",)


class LibManager:
    def __init__(self) -> None:
        self.libs: dict[str, SafObject] = {}

    def __getitem__(self, key: str) -> SafObject | None:
        return self.libs.get(key)

    def __setitem__(self, key: str, value: SafObject) -> None:
        self.libs[key] = value

    def load_lib(self, path: Path, *, ctx: NativeContext) -> SafObject:
        globals = runpy.run_path(str(path.absolute()))
        loader = globals.get("load")
        if loader is None or not isfunction(loader):
            raise SafulateImportError("Module is invalid and could not be loaded")

        try:
            obj = loader(ctx)
        except Exception as e:
            raise RuntimeError("Module does not have a valid exporter") from e

        if not isinstance(obj, SafObject):
            raise SafulateImportError("Module is invalid and could not be loaded")

        self[obj.type.name] = obj
        return obj

    def load_builtin_lib(self, name: str, *, ctx: NativeContext) -> SafObject:
        path = Path(__file__).parent / "libs" / f"{name}.py"
        if not path.exists():
            raise SafulateImportError(f"Module {name!r} could not be found")

        return self.load_lib(path, ctx=ctx)

    def get_or_load(self, name: str, *, ctx: NativeContext) -> SafObject | None:
        lib = self[name]
        if lib is None:
            lib = self.load_builtin_lib(name, ctx=ctx)
        return lib
