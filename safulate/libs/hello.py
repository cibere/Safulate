from __future__ import annotations

from safulate.init import LibraryExporter, StrValue

exporter = LibraryExporter("builtins")
exporter["hello"] = StrValue("world")
