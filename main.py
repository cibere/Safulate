from safulate.lexer import Lexer
import msgspec
from safulate.executer import Executer
from pathlib import Path

file = Path("test.saf")
l = Lexer(file.read_text())
l.start()
print("--- statements ---")
print(
    msgspec.json.format(
        msgspec.json.encode(
            [t.to_dict() for s in l.statements for t in s],
            enc_hook=lambda v: getattr(v, "to_dict", repr)(v),
        )
    ).decode()
)

if input("continue?: ") == "y":
    exe = Executer()
    exe.execute(*l.statements)
