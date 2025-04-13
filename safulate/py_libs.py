from __future__ import annotations

import runpy
from pathlib import Path
from typing import TYPE_CHECKING, Concatenate

from .errors import SafulateImportError
from .values import FuncValue, ObjectValue, Value

if TYPE_CHECKING:
    from collections.abc import Callable

    from .native_context import NativeContext

__all__ = ("Exporter", "LibManager")


class LibManager:
    def __init__(self, *, load_builtin_libs: bool = True) -> None:
        self.libs: dict[str, ObjectValue] = {}

        if load_builtin_libs:
            self.load_builtin_libs()

    def __getitem__(self, key: str) -> ObjectValue | None:
        return self.libs.get(key)

    def __setitem__(self, key: str, value: ObjectValue) -> None:
        self.libs[key] = value

    def register_exporter(self, exporter: Exporter) -> None:
        self[exporter.name] = exporter.to_container()

    def load_lib(self, path: Path) -> None:
        globals = runpy.run_path(str(path.absolute()))
        exporter = globals.get("exporter")
        if exporter is None:
            raise SafulateImportError("Module does not have an exporter")
        if not isinstance(exporter, Exporter):
            raise RuntimeError("Module does not have a valid exporter")

        self.register_exporter(exporter)

    def load_builtin_libs(self) -> None:
        lib_folder = Path(__file__).parent / "libs"
        for file in lib_folder.glob("*.py"):
            if file.name.startswith("_"):
                continue

            self.load_lib(file)


class Exporter:
    def __init__(self, name: str) -> None:
        self.name = name
        self.exports: dict[str, Value] = {}

    def __getitem__(self, key: str) -> Value:
        return self.exports[key]

    def __setitem__(self, key: str, value: Value) -> None:
        self.exports[key] = value

    def export(
        self,
        name: str,
    ) -> Callable[[Callable[Concatenate[NativeContext, ...], Value]], FuncValue]:
        def deco(
            callback: Callable[Concatenate[NativeContext, ...], Value],
        ) -> FuncValue:
            func = FuncValue.from_native(name, callback)
            self[name] = func
            return func

        return deco

    __call__ = export

    def to_container(self) -> ObjectValue:
        return ObjectValue(self.name, self.exports)
