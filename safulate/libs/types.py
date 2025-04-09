from __future__ import annotations

from safulate import Exporter, TypeValue, ValueTypeEnum

exporter = Exporter("types")

for enum in ValueTypeEnum:
    exporter[enum.name] = TypeValue(enum)
