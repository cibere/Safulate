from typing import List, Callable
import logging
from .tokens import Token, TokenType
from ._types import Loc
from .errors import EOF

log = logging.getLogger(__name__)


class Lexer:
    char_tokens = {
        "+": TokenType.plus,
        ";": TokenType.eos,
    }

    def __init__(self, source: str) -> None:
        self.tokens: list[Token] = []
        self.curr: Loc = (0, -1)
        self.start_loc: Loc = (0, 0)
        self.source: list[str] = source.splitlines()

    def __getitem__(self, loc: Loc) -> str:
        return self.source[loc[0]][loc[1]]

    def __add__(self, args: tuple[TokenType, str]) -> Token:
        return Token(type=args[0], value=args[1], loc=self.start_loc)

    def __sub__(self, msg: str) -> Token:
        return Token(type=TokenType.error, value=msg, loc=self.start_loc)

    def __xor__(self, check: Callable[[str], bool]) -> str:
        temp = ""
        log.debug("%r | ----- start greedy processing -----", self.curr)
        while 1:
            next_char, char = self.next()
            log.debug("%r | Polling greedy char: %s", self.curr, next_char)
            if check(next_char):
                temp += next_char
            else:
                break
        log.debug("%r | ----- end greedy processing -----", self.curr)
        return temp

    @property
    def next_char_loc(self) -> Loc:
        return (self.curr[0], self.curr[1] + 1)

    @property
    def next_line_loc(self) -> Loc:
        return (self.curr[0] + 1, 0)

    def next(self) -> str:
        for loc in (self.next_char_loc, self.next_line_loc):
            try:
                char = self[loc]
            except IndexError:
                pass
            else:
                log.debug("%r | Got next char: %s", loc, char)
                self.curr = loc
                return char
        raise EOF()

    def poll_char(self, char: str | None) -> Token | None:
        self.start_loc = self.curr
        if char is None:
            return

        log.debug("%r | Processing %s", self.curr, char)

        match char:
            case " " | "\t" | "\n":
                pass
            case "#":
                self.curr = self.next_line_loc
            case _ as x if x in self.char_tokens.keys():
                return self + (self.char_tokens[x], x)
            case '"':
                return self + (TokenType.str, self ^ (lambda c: c != '"'))
            case _ as x if x.isalpha():
                temp = self ^ (lambda c: c.isalnum())
                return self + (TokenType.id, x + temp)
            case _ as x if x.isdigit():
                value = x + (self ^ (lambda c: c.isdigit() or c == "."))
                if value.count(".") > 1:
                    return self - ("Too many dots in int/float")
                else:
                    return self + (TokenType.num, value)
            case _:
                return self - ("Unknown character")

    def start(self) -> List[Token]:
        try:
            while 1:
                char = self.next()
                token = self.poll_char(char)
                if token:
                    self.tokens.append(token)
        except EOF:
            if self.tokens[-1].type != TokenType.eos:
                raise RuntimeError("File does not end with a statement ending char")
        return self.tokens
