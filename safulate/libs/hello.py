from safulate.lib_exporter import LibraryExporter
from safulate.tokens import StringToken

exporter = LibraryExporter("hello")
exporter["author"] = StringToken("cibere")
