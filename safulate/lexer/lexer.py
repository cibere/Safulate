from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar, TypeAlias, TypeVar, overload

from ..errors import ErrorManager, SafulateSyntaxError
from .enums import TokenType
from .tokens import Token

__all__ = ("Lexer",)

T = TypeVar("T")
CASE_INFO_ATTR = "__safulate_case_info__"
_querty = "qwertyuiopasdfghjklzxcvbnm"
id_first_char_characters = f"_{_querty}{_querty.upper()}"
id_other_char_characters = f"1234567890{id_first_char_characters}"

LexerCase: TypeAlias = tuple[
    tuple[str, ...],
    Callable[["Lexer", str], Any | None] | None,
    Callable[["Lexer"], None] | Callable[["Lexer", Any], None],
]
_cases: list[LexerCase] = []


class Lexer:
    __slots__ = ("current", "source", "start", "tokens")
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
            TokenType.AMP,
            TokenType.PIPE,
            TokenType.BOOL,
            TokenType.PAR,
            TokenType.GET_PRIV,
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
        sym.value: sym
        for sym in (TokenType.STARSTAREQ, TokenType.EQEQEQ, TokenType.ELLIPSIS)
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
            TokenType.PUB,
            TokenType.PRIV,
            TokenType.TYPE,
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

    @overload
    @staticmethod
    def _(
        *chars: str,
    ) -> Callable[
        [Callable[[Lexer], None]],
        Callable[[Lexer], None],
    ]: ...
    @overload
    @staticmethod
    def _(
        *chars: str, condition: Callable[[Lexer, str], T | None]
    ) -> Callable[
        [Callable[[Lexer, T], None]],
        Callable[[Lexer, T], None],
    ]: ...
    @staticmethod
    def _(
        *chars: str, condition: Callable[[Lexer, str], T | None] | None = None
    ) -> Any:
        def deco(
            func: Callable[[Lexer, T], None] | Callable[[Lexer], None],
        ) -> Callable[[Lexer, T], None] | Callable[[Lexer], None]:
            _cases.append((chars, condition, func))
            return func

        return deco

    def poll_char(self) -> None:
        self.start = self.current
        if self.is_eof():
            return self.add_token(TokenType.EOF)

        for chars, condition, func in _cases:
            args: list[Any] = [self]

            if chars and self.snippit_next not in chars:
                continue
            if condition:
                val = condition(self, self.snippit_next)
                if val is None:
                    continue
                args.append(val)
            return func(*args)

        raise SafulateSyntaxError(f"Unknown character {self.source[self.start]!r}")

    def tokenize(self) -> list[Token]:
        with ErrorManager(start=lambda: self.start):
            while (not self.tokens) or (self.tokens[-1].type is not TokenType.EOF):
                self.poll_char()

        return self.tokens

    # region cases

    @staticmethod
    def _mod_str_cond(lexer: Lexer, _: str) -> str | None:
        if (idx := lexer.current + 1) < len(lexer.source) and (
            enclosing_char := lexer.source[idx]
        ) in "\"'`":
            return enclosing_char
        return None

    @_(" ", "\t", "\n")
    def handle_whitespace(self) -> None:
        self.current += 1

    @_("#")
    def handle_comment(self) -> None:
        while self.not_eof() and self.char != "\n":
            self.current += 1

    @_("f", "F", condition=_mod_str_cond)
    def handle_fstring(self, enclosing_char: str) -> None:
        self.current += 2
        start_token_added = False

        while self.not_eof() and self.char != enclosing_char:
            if self.char == "\\":
                self.current += 2
            elif self.char == "{":
                if start_token_added:
                    self.add_token(TokenType.FSTR_MIDDLE)
                else:
                    self.start += 2
                    self.add_token(TokenType.FSTR_START)
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

        if start_token_added:
            token_type = TokenType.FSTR_END
        else:
            self.start += 1
            token_type = TokenType.STR

        self.add_token(token_type)
        self.current += 1

    @_("r", "R", condition=_mod_str_cond)
    def handle_rstring(self, enclosing_char: str) -> None:
        self.current += 2
        while self.not_eof() and self.char != enclosing_char:
            self.current += 1

        if self.is_eof():
            raise SafulateSyntaxError("Unterminated string")

        self.current += 1
        self.add_token(TokenType.RSTRING)

    @_(
        '"',
        "'",
        "`",
    )
    def handle_str(self) -> None:
        enclosing_char = self.snippit_next
        self.current += 1
        self.start += 1

        while self.not_eof() and self.char != enclosing_char:
            self.current += 1

        if self.is_eof():
            raise SafulateSyntaxError("Unterminated string")

        self.add_token(TokenType.STR)
        self.current += 1

    @staticmethod
    def _sym_cond(lex: Lexer, txt: str) -> TokenType | None:
        return (
            lex.trisymbol_tokens.get(lex.source[lex.start : lex.current + 3])
            or lex.bisymbol_tokens.get(lex.source[lex.start : lex.current + 2])
            or lex.symbol_tokens.get(txt)
        )

    @_(condition=_sym_cond)
    def handle_token_symbols(self, tok: TokenType) -> None:
        self.current += len(tok.value)
        self.add_token(tok)

    @_(condition=lambda _lex, txt: txt if txt in id_first_char_characters else None)
    def handle_id(self, char: str) -> None:
        last_char = char

        while self.not_eof() and last_char in id_other_char_characters:
            char = self.snippit_next
            last_char = char[-1]

            self.current += 1

        if not char.isalnum():
            self.current -= 1

        self.add_token(self.hard_keywords.get(self.snippit, TokenType.ID))

    @_(condition=lambda _lex, txt: txt if txt.isdigit() else None)
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
