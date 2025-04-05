from __future__ import annotations

from safulate.lib_exporter import LibraryExporter
from safulate.values import StrValue

exporter = LibraryExporter("builtins")
exporter["hello"] = StrValue("world")
