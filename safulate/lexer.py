from __future__ import annotations

from typing import ClassVar

from .errors import ErrorManager, SafulateSyntaxError
from .tokens import Token, TokenType

__all__ = ("Lexer",)

_querty = "qwertyuiopasdfghjklzxcvbnm"
id_first_char_characters = f"_{_querty}{_querty.upper()}"
id_other_char_characters = f"1234567890{id_first_char_characters}"


class Lexer:
    __slots__ = (
        "current",
        "source",
        "start",
        "tokens",
    )
    symbol_tokens: ClassVar[dict[str, TokenType]] = {
        sym.value: sym
        for sym in (
            TokenType.LPAR,
            TokenType.RPAR,
            TokenType.LSQB,
            TokenType.RSQB,
            TokenType.LBRC,
            TokenType.RBRC,
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.STAR,
            TokenType.SLASH,
            TokenType.EQ,
            TokenType.LESS,
            TokenType.GRTR,
            TokenType.SEMI,
            TokenType.COMMA,
            TokenType.DOT,
            TokenType.TILDE,
            TokenType.AT,
            TokenType.NOT,
            TokenType.AND,
            TokenType.OR,
        )
    }
    bisymbol_tokens: ClassVar[dict[str, TokenType]] = {
        sym.value: sym
        for sym in (
            TokenType.STARSTAR,
            TokenType.EQEQ,
            TokenType.NEQ,
            TokenType.LESSEQ,
            TokenType.GRTREQ,
            TokenType.PLUSEQ,
            TokenType.MINUSEQ,
            TokenType.STAREQ,
            TokenType.SLASHEQ,
        )
    }
    trisymbol_tokens: ClassVar[dict[str, TokenType]] = {
        sym.value: sym for sym in (TokenType.STARSTAREQ,)
    }
    keyword_tokens: ClassVar[dict[str, TokenType]] = {
        sym.value: sym
        for sym in (
            TokenType.VAR,
            TokenType.FUNC,
            TokenType.NULL,
            TokenType.RETURN,
            TokenType.IF,
            TokenType.ELSE,
            TokenType.WHILE,
            TokenType.BREAK,
            TokenType.PRIV,
            TokenType.SPEC,
            TokenType.REQ,
            TokenType.RAISE,
            TokenType.FOR,
            TokenType.CONTAINS,
            TokenType.DEL,
            TokenType.TRY,
            TokenType.SWITCH,
            TokenType.CONTINUE,
        )
    }

    def __init__(self, source: str) -> None:
        self.tokens: list[Token] = []
        self.start = 0
        self.current = 0
        self.source = source

    def add_token(self, type: TokenType) -> None:
        self.tokens.append(
            Token(type, self.source[self.start : self.current], self.start)
        )

    def poll_char(self) -> bool:
        self.start = self.current
        if self.current >= len(self.source):
            self.add_token(TokenType.EOF)
            return False

        char = self.source[self.start : self.current + 1]

        match char:
            case " " | "\t" | "\n":
                self.current += 1
                return True
            case "#":
                while (
                    self.current < len(self.source)
                    and self.source[self.current] != "\n"
                ):
                    self.current += 1
                return True
            case '"' | "'" | "`" as enclosing_char:
                self.current += 1
                while (
                    self.current < len(self.source)
                    and self.source[self.current] != enclosing_char
                ):
                    self.current += 1

                if self.current >= len(self.source):
                    raise SafulateSyntaxError("Unterminated string")
                self.current += 1
                self.add_token(TokenType.STR)
            case _ as x if tok := self.trisymbol_tokens.get(
                self.source[self.start : self.current + 3]
            ):
                self.current += 3
                self.add_token(tok)
            case _ as x if tok := self.bisymbol_tokens.get(
                self.source[self.start : self.current + 2]
            ):
                self.current += 2
                self.add_token(tok)
            case _ as x if tok := self.symbol_tokens.get(x):
                self.current += 1
                self.add_token(tok)
            case "v" if self.source[self.current + 1].isdigit():
                self.current += 1
                temp = [""]

                while self.current < len(self.source) and (
                    self.source[self.current].isdigit()
                    or self.source[self.current] == "."
                ):
                    if self.source[self.current] == ".":
                        temp.append("")
                    else:
                        temp[-1] += self.source[self.current]
                    self.current += 1

                if len(temp) > 3:
                    raise SafulateSyntaxError("Version size too big")
                if temp[-1] == "":
                    self.start = self.current - 1
                    raise SafulateSyntaxError("Version can not end in a dot")

                self.add_token(TokenType.VER)
            case _ as x if x in id_first_char_characters or x == "$":
                if x == "$":
                    self.current = self.current + 1
                    last_char = self.source[self.current]
                    if last_char not in id_other_char_characters:
                        raise SafulateSyntaxError("Expected ID after '$'")
                else:
                    last_char = x

                while (
                    self.current < len(self.source)
                    and last_char in id_other_char_characters
                ):
                    char = self.source[self.start : self.current + 1]
                    last_char = char[-1]

                    self.current += 1
                if not char.isalnum():
                    self.current -= 1
                if self.source[self.start : self.current] in self.keyword_tokens:
                    self.add_token(
                        self.keyword_tokens[self.source[self.start : self.current]]
                    )
                else:
                    self.add_token(TokenType.ID)
            case _ as x if x.isdigit():
                dot_found = False
                while self.current < len(self.source) and (
                    char[-1].isdigit()
                    or (
                        char[-1] == "."
                        and self.source[self.current].isdigit()
                        and not dot_found
                    )
                ):
                    if char[-1] == ".":
                        dot_found = True
                    char = self.source[self.start : self.current + 1]
                    self.current += 1
                if not char[-1].isdigit():
                    self.current -= 1
                self.add_token(TokenType.NUM)
            case _:
                raise SafulateSyntaxError(
                    f"Unknown character {self.source[self.start]!r}"
                )
        return True

    def tokenize(self) -> list[Token]:
        with ErrorManager(start=lambda: self.start):
            while self.poll_char():
                pass

        return self.tokens
