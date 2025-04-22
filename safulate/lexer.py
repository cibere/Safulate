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
            TokenType.COLON,
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
    hard_keywords: ClassVar[dict[str, TokenType]] = {
        sym.value: sym
        for sym in (
            TokenType.RETURN,
            TokenType.IF,
            TokenType.REQ,
            TokenType.WHILE,
            TokenType.BREAK,
            TokenType.DEL,
            TokenType.RAISE,
            TokenType.FOR,
            TokenType.TRY,
            TokenType.CONTINUE,
            TokenType.HAS,
        )
    }

    def __init__(self, source: str) -> None:
        self.tokens: list[Token] = []
        self.start = 0
        self.current = 0
        self.source = source

    @property
    def char(self) -> str:
        return self.source[self.current]

    @property
    def char_next(self) -> str:
        return self.source[self.current + 1]

    @property
    def snippit(self) -> str:
        return self.source[self.start : self.current]

    @property
    def snippit_next(self) -> str:
        return self.source[self.start : self.current + 1]

    def not_eof(self) -> bool:
        return self.current < len(self.source)

    def is_eof(self) -> bool:
        return self.current >= len(self.source)

    def add_token(self, type: TokenType) -> None:
        self.tokens.append(
            Token(type, self.source[self.start : self.current], self.start)
        )

    def handle_whitespace(self) -> None:
        self.current += 1

    def handle_comment(self) -> None:
        while self.not_eof() and self.char != "\n":
            self.current += 1

    def handle_fstring(self, enclosing_char: str) -> None:
        self.current += 2
        start_token_added = False

        while self.not_eof() and self.char != enclosing_char:
            if self.char == "\\":
                self.current += 2
            elif self.char == "{":
                self.add_token(
                    TokenType.FSTR_MIDDLE if start_token_added else TokenType.FSTR_START
                )
                start_token_added = True
                self.current += 1
                parens = 1

                while self.not_eof():
                    if self.char == "{":
                        parens += 1
                    elif self.char == "}":
                        parens -= 1
                        if parens == 0:
                            break
                    self.poll_char()

                self.current += 1
                self.start = self.current
            else:
                self.current += 1

        if self.is_eof():
            raise SafulateSyntaxError("Unterminated string")
        self.current += 1

        if start_token_added:
            token_type = TokenType.FSTR_END
        else:
            self.start += 1
            token_type = TokenType.STR

        self.add_token(token_type)

    def handle_rstring(self, enclosing_char: str) -> None:
        self.current += 2
        while self.not_eof() and self.char != enclosing_char:
            self.current += 1

        if self.is_eof():
            raise SafulateSyntaxError("Unterminated string")

        self.current += 1
        self.add_token(TokenType.RSTRING)

    def handle_str(self, enclosing_char: str) -> None:
        self.current += 1
        self.start += 1
        while self.not_eof() and self.char != enclosing_char:
            self.current += 1

        if self.is_eof():
            raise SafulateSyntaxError("Unterminated string")

        self.add_token(TokenType.STR)
        self.current += 1

    def handle_token_symbols(self, tok: TokenType) -> None:
        self.current += len(tok.value)
        self.add_token(tok)

    def handle_version(self) -> None:
        self.current += 1
        temp = [""]

        while self.not_eof() and (self.char.isdigit() or self.char == "."):
            if self.char == ".":
                temp.append("")
            else:
                temp[-1] += self.char
            self.current += 1

        if len(temp) > 3:
            raise SafulateSyntaxError("Version size too big")
        if temp[-1] == "":
            self.start = self.current - 1
            raise SafulateSyntaxError("Version can not end in a dot")

        self.add_token(TokenType.VER)

    def handle_id(self, char: str) -> None:
        if char == "$":
            self.current = self.current + 1
            last_char = self.char
            self.start += 1
            token_type = TokenType.PRIV_ID
            if last_char not in id_other_char_characters:
                raise SafulateSyntaxError("Expected ID after '$'")
        else:
            last_char = char
            token_type = TokenType.ID

        while self.not_eof() and last_char in id_other_char_characters:
            char = self.snippit_next
            last_char = char[-1]

            self.current += 1

        if not char.isalnum():
            self.current -= 1

        self.add_token(self.hard_keywords.get(self.snippit, token_type))

    def handle_num(self, char: str) -> None:
        dot_found = False
        while self.not_eof() and (
            char[-1].isdigit()
            or (char[-1] == "." and self.char.isdigit() and not dot_found)
        ):
            if char[-1] == ".":
                dot_found = True
            char = self.snippit_next
            self.current += 1
        if not char[-1].isdigit():
            self.current -= 1
        self.add_token(TokenType.NUM)

    def poll_char(self) -> None:
        self.start = self.current
        if self.is_eof():
            return self.add_token(TokenType.EOF)

        match self.snippit_next:
            case " " | "\t" | "\n":
                return self.handle_whitespace()
            case "#":
                return self.handle_comment()
            case "f" | "F" if (idx := self.current + 1) < len(self.source) and (
                enclosing_char := self.source[idx]
            ) in "\"'`":
                return self.handle_fstring(enclosing_char)
            case "r" | "R" if (idx := self.current + 1) < len(self.source) and (
                enclosing_char := self.source[idx]
            ) in "\"'`":
                return self.handle_rstring(enclosing_char)
            case '"' | "'" | "`" as enclosing_char:
                return self.handle_str(enclosing_char)
            case _ as x if tok := self.trisymbol_tokens.get(
                self.source[self.start : self.current + 3]
            ):
                return self.handle_token_symbols(tok)
            case _ as x if tok := self.bisymbol_tokens.get(
                self.source[self.start : self.current + 2]
            ):
                return self.handle_token_symbols(tok)
            case _ as x if tok := self.symbol_tokens.get(x):
                return self.handle_token_symbols(tok)
            case "v" if self.source[self.current + 1].isdigit():
                return self.handle_version()
            case _ as x if x in id_first_char_characters or x == "$":
                return self.handle_id(x)
            case _ as x if x.isdigit():
                return self.handle_num(x)
            case _:
                raise SafulateSyntaxError(
                    f"Unknown character {self.source[self.start]!r}"
                )

    def tokenize(self) -> list[Token]:
        with ErrorManager(start=lambda: self.start):
            while (not self.tokens) or (self.tokens[-1].type is not TokenType.EOF):
                self.poll_char()

        return self.tokens
