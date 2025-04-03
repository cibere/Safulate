from dataclasses import dataclass
from enum import Enum
from ._types import Loc


class TokenType(Enum):
    error = -1
    str = 1
    id = 2
    num = 3
    plus = 4
    eos = 5


@dataclass
class Token:
    type: TokenType
    value: str
    loc: Loc

    def __repr__(self) -> str:
        return f"<{self.type.name}@{self.loc}:{self.value!r}>"
