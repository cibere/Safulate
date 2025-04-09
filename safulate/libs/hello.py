from __future__ import annotations

from safulate import Exporter, StrValue

exporter = Exporter("builtins")
exporter["hello"] = StrValue("world")
