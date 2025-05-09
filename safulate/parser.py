from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING, Literal, NamedTuple, TypeVar

from packaging.version import InvalidVersion
from packaging.version import Version as _PackagingVersion

from .asts import (
    ASTAssign,
    ASTAtom,
    ASTBinary,
    ASTBlock,
    ASTBreak,
    ASTCall,
    ASTContinue,
    ASTDel,
    ASTEditObject,
    ASTExprStmt,
    ASTForLoop,
    ASTFormat,
    ASTFuncDecl,
    ASTFuncDecl_Param,
    ASTIf,
    ASTImportReq,
    ASTList,
    ASTNode,
    ASTProgram,
    ASTProperty,
    ASTRaise,
    ASTRegex,
    ASTReturn,
    ASTSwitchCase,
    ASTTryCatch,
    ASTTryCatch_CatchBranch,
    ASTUnary,
    ASTVarDecl,
    ASTVersionReq,
    ASTWhile,
)
from .enums import ParamType, SoftKeyword, TokenType
from .errors import SafulateSyntaxError
from .properties import cached_property
from .tokens import Token

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Protocol

    class RegDecoFact(Protocol):
        def __call__(
            self,
            *sequence: TokenType
            | SoftKeyword
            | tuple[TokenType | SoftKeyword | None, ...]
            | Literal["any"],
            check: Callable[[Parser], bool] | None = None,
        ) -> Callable[[CaseCallbackT], CaseCallbackT]: ...


CaseCallbackT = TypeVar("CaseCallbackT", bound="Callable[[Parser], ASTNode]")
require_version_pattern = re.compile(
    r"v(?P<major>[0-9]+)\.(?P<minor>[0-9]+|x)(?:\.(?P<micro>[0-9]+))?"
)
ANY = "any"
SAFULATE_CASE_INFO_ATTR = "__safulate_case_info__"


class RegisteredCase(NamedTuple):
    callback: Callable[[Parser], ASTNode]
    check: Callable[[Parser], bool]
    type: Literal["expr", "stmt"]


def _reg_deco_maker(type_: Literal["expr", "stmt"], /) -> RegDecoFact:
    def deco_fact(
        *sequence: TokenType
        | SoftKeyword
        | tuple[TokenType | SoftKeyword | None, ...]
        | Literal["any"],
        check: Callable[[Parser], bool] | None = None,  # pyright: ignore[reportRedeclaration]
    ) -> Callable[[CaseCallbackT], CaseCallbackT]:
        if check is None:

            def check(parser: Parser) -> bool:
                return parser.check_sequence(*sequence)

        def deco(func: CaseCallbackT) -> CaseCallbackT:
            setattr(
                func,
                SAFULATE_CASE_INFO_ATTR,
                RegisteredCase(callback=func, type=type_, check=check),
            )
            return func

        return deco

    return deco_fact


reg_expr = _reg_deco_maker("expr")
reg_stmt = _reg_deco_maker("stmt")


class Parser:
    def __init__(self) -> None:
        self.current = 0
        self.cases: list[RegisteredCase] =  [
            getattr(func, SAFULATE_CASE_INFO_ATTR)
            for _name, func in inspect.getmembers(
                self, lambda obj: hasattr(obj, SAFULATE_CASE_INFO_ATTR)
            )
        ]

    @cached_property
    def expr_cases(self) -> list[RegisteredCase]:
        return [case for case in self.cases if case.type == "expr"]

    @cached_property
    def stmt_cases(self) -> list[RegisteredCase]:
        return [case for case in self.cases if case.type == "stmt"]

    def _execute_case(self, case: RegisteredCase) -> ASTNode | None:
        return case.callback(self) if case.check(self) else None

    def _execute_cases(self, cases: list[RegisteredCase]) -> ASTNode | None:
        for case in cases:
            if res := self._execute_case(case):
                return res

    def parse(self, tokens: list[Token]) -> ASTNode:
        self.tokens = tokens
        return self.program()

    def advance(self) -> Token:
        t = self.tokens[self.current]
        self.current += 1
        return t

    def peek(self) -> Token:
        return self.tokens[self.current]

    def compare(self, token: Token, type: TokenType | SoftKeyword) -> bool:
        if isinstance(type, TokenType):
            return token.type is type
        else:
            return token.type is TokenType.ID and token.lexeme == type.value

    def check(self, *types: TokenType | SoftKeyword) -> bool:
        return any(self.compare(self.peek(), type) for type in types)

    def _validate_sequence_token(
        self, entry: tuple[TokenType | SoftKeyword | None, ...], token: Token
    ) -> bool:
        for typ in entry:
            if typ is None:
                continue

            if self.compare(token, typ):
                return True
        return False

    def _get_sequence(
        self,
        *types: TokenType
        | SoftKeyword
        | tuple[TokenType | SoftKeyword | None, ...]
        | Literal["any"],
        consume: bool,
    ) -> list[Token | None] | None:
        tokens: list[Token | None] = []
        idx = 0

        try:
            for entry in types:
                token = self.tokens[self.current + idx]

                if entry == ANY:
                    tokens.append(token)
                    continue
                if not isinstance(entry, tuple):
                    entry = (entry,)

                if self._validate_sequence_token(entry, token):
                    tokens.append(token)
                elif None in entry:
                    tokens.append(None)
                    idx -= 1
                else:
                    return None
                idx += 1
        except IndexError:
            pass

        if consume:
            for _ in range(idx):
                self.tokens.pop(0)
        return tokens

    def check_sequence(
        self,
        *types: TokenType
        | SoftKeyword
        | tuple[TokenType | SoftKeyword | None, ...]
        | Literal["any"],
    ) -> bool:
        return self._get_sequence(*types, consume=False) is not None

    def match_sequence(
        self,
        *types: TokenType
        | SoftKeyword
        | tuple[TokenType | SoftKeyword | None, ...]
        | Literal["any"],
    ) -> list[Token | None] | None:
        return self._get_sequence(*types, consume=True)

    def match(self, *types: TokenType | SoftKeyword) -> Token | None:
        if self.check(*types):
            return self.advance()

    def consume(
        self,
        types: TokenType | SoftKeyword | tuple[TokenType | SoftKeyword, ...],
        msg: str | None = None,
    ) -> Token:
        token = self.advance()

        if not isinstance(types, tuple):
            types = (types,)

        for typ in types:
            if self.compare(token, typ):
                return token

        if msg is None:
            if len(types) == 1:
                msg = f"Expected {types[0].value!r}"
            else:
                msg = f"Expected one of the following: {', '.join(repr(typ) for typ in types)}"

        raise SafulateSyntaxError(msg, token)

    def walk_split_tokens(
        self,
        *,
        delimiter: TokenType | SoftKeyword = TokenType.COMMA,
        end: TokenType | SoftKeyword,
    ) -> Iterator[Token]:
        first_captured = bool(self.check(end))

        while first_captured is False or (self.check(delimiter)):
            if first_captured:
                self.consume(delimiter, None)
            first_captured = True

            yield self.peek()

        self.consume(end, None)

    def _func_decl(
        self, *, scope_token: Token, kw_token: Token, name: Token | None
    ) -> ASTNode:
        paren_token = self.consume(TokenType.LPAR, "Expected '('")

        params: list[ASTFuncDecl_Param] = []
        defaulted = False
        vararg_reached = varkwarg_reached = False

        for _ in self.walk_split_tokens(end=TokenType.RPAR):
            if varkwarg_reached:
                raise SafulateSyntaxError("No params can follow varkwarg", self.peek())

            param_type = ParamType.kwarg if vararg_reached else ParamType.arg_or_kwarg
            if self.match_sequence(TokenType.DOT, TokenType.DOT):
                vararg_reached = True
                param_type = ParamType.vararg
            elif self.match(TokenType.ELLIPSIS):
                param_type = ParamType.varkwarg
                varkwarg_reached = True

            param_name = self.consume(TokenType.ID, "Expected name of arg")
            default = None
            if self.match(TokenType.EQ):
                defaulted = True
                default = self.expr()
            elif defaulted:
                raise SafulateSyntaxError(
                    "Non-default arg following a default arg", self.peek()
                )

            params.append(
                ASTFuncDecl_Param(name=param_name, default=default, type=param_type)
            )

        decos: list[tuple[Token, ASTNode]] = (
            [
                (start_token, self.expr())
                for start_token in self.walk_split_tokens(end=TokenType.RSQB)
            ]
            if self.match(TokenType.LSQB)
            else []
        )

        if self.check(TokenType.COLON):
            self.annotation()

        body = self.block()

        try:
            decl_kw = SoftKeyword(kw_token.lexeme)
        except ValueError:
            decl_kw = kw_token.type

        match decl_kw:
            case SoftKeyword.STRUCT:
                if name is None:
                    raise SafulateSyntaxError("structs must have a name")
                func = self._type_creation(
                    kw_token=kw_token,
                    name_token=name,
                    constructor=ASTFuncDecl(
                        name=name,
                        params=params,
                        scope_token=scope_token,
                        kw_token=kw_token,
                        paren_token=paren_token,
                        body=ASTBlock(
                            [
                                ASTReturn(
                                    keyword=kw_token.with_type(TokenType.RETURN),
                                    expr=ASTEditObject(
                                        obj=ASTCall(
                                            callee=ASTAtom(
                                                kw_token.with_type(
                                                    TokenType.ID, lexme="object"
                                                )
                                            ),
                                            paren=kw_token.with_type(TokenType.LPAR),
                                            params=[
                                                (
                                                    ParamType.arg,
                                                    None,
                                                    ASTAtom(
                                                        name.with_type(
                                                            TokenType.STR,
                                                            lexme=name.lexeme,
                                                        )
                                                    ),
                                                )
                                            ]
                                            if name
                                            else [],
                                        ),
                                        block=body,
                                    ),
                                ),
                            ]
                        ),
                    ),
                )

                if self.match(TokenType.TILDE):
                    func = ASTEditObject(func, self.block())
            case SoftKeyword.PROP:
                if params:
                    raise SafulateSyntaxError("Properties can't take arguments")
                if decos:
                    raise SafulateSyntaxError("Properties can't take decorators")
                if name is None:
                    raise SafulateSyntaxError("Properties must have a name")
                return ASTProperty(body=body, name=name)
            case TokenType.PRIV | SoftKeyword.SPEC | TokenType.PUB:
                func = ASTFuncDecl(
                    name=name,
                    params=params,
                    body=body,
                    scope_token=scope_token,
                    kw_token=kw_token,
                    paren_token=paren_token,
                )
            case _:
                raise RuntimeError(f"Unknown keyword for func declaration: {decl_kw!r}")

        if not decos:
            return func

        for token, deco in decos:
            func = ASTCall(
                callee=ASTCall(
                    callee=ASTCall(
                        callee=ASTCall.get_attr(
                            expr=deco,
                            attr=Token(
                                type=TokenType.ID,
                                lexeme="without_partials",
                                start=token.start,
                            ),
                            dot=Token.mock(TokenType.DOT, start=token.start),
                        ),
                        paren=Token(type=TokenType.LPAR, lexeme="(", start=token.start),
                        params=[],
                    ),
                    paren=Token(type=TokenType.LSQB, lexeme="[", start=token.start),
                    params=[
                        (
                            ParamType.arg,
                            None,
                            func,
                        ),
                        (
                            ParamType.vararg,
                            None,
                            ASTCall.get_attr(
                                expr=deco,
                                attr=Token(
                                    type=TokenType.ID,
                                    lexeme="partial_args",
                                    start=token.start,
                                ),
                                dot=Token.mock(TokenType.DOT, start=token.start),
                            ),
                        ),
                        (
                            ParamType.varkwarg,
                            None,
                            ASTCall.get_attr(
                                expr=deco,
                                attr=Token(
                                    type=TokenType.ID,
                                    lexeme="partial_kwargs",
                                    start=token.start,
                                ),
                                dot=Token.mock(TokenType.DOT, start=token.start),
                            ),
                        ),
                    ],
                ),
                paren=token.with_type(TokenType.LPAR),
                params=[],
            )

        return func

    def _type_creation(
        self, *, kw_token: Token, name_token: Token, constructor: ASTNode | None
    ) -> ASTNode:
        params: list[tuple[ParamType, str | None, ASTNode]] = [
            (
                ParamType.arg,
                None,
                ASTAtom(Token(TokenType.STR, name_token.lexeme, name_token.start)),
            )
        ]
        if constructor is not None:
            params.append((ParamType.kwarg, "constructor", constructor))
        return ASTCall(
            callee=ASTAtom(kw_token.with_type(TokenType.TYPE)),
            paren=kw_token.with_type(TokenType.LPAR),
            params=params,
        )

    def annotation(self) -> ASTNode:
        self.consume(TokenType.COLON, "Expected ':' to start annotation")
        return self.expr()

    def program(self) -> ASTNode:
        stmts: list[ASTNode] = []

        while not self.check(TokenType.EOF):
            stmts.append(self.stmt())

        return ASTProgram(stmts)

    # region Stmts

    def stmt(self) -> ASTNode:
        if node := self._execute_cases(self.stmt_cases):
            return node

        expr = self.expr()
        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTExprStmt(expr)

    @reg_stmt(TokenType.LBRC)
    def block(self) -> ASTBlock:
        # Only using consume because rules like `if` and `while` use it directly,
        # `stmt` rule checks for `{` first
        self.consume(TokenType.LBRC, "Expected '{'")
        stmts: list[ASTNode] = []
        while not self.check(TokenType.RBRC):
            stmts.append(self.stmt())

        self.consume(TokenType.RBRC, "Expected '}'")
        return ASTBlock(stmts)

    @reg_stmt(
        (TokenType.PRIV, TokenType.PUB, None),
        TokenType.TYPE,
        TokenType.ID,
        TokenType.LBRC,
    )
    def type_decl(self) -> ASTNode:
        scope_token = self.match(TokenType.PUB, TokenType.PRIV)
        kw_token = self.consume(
            TokenType.TYPE,
            "Expected 'type' keyword to start a type declaration statement",
        )
        name_token = self.consume(TokenType.ID, "Expected name for new type")
        body = self.block()

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTVarDecl(
            name_token,
            value=ASTEditObject(
                obj=self._type_creation(
                    kw_token=kw_token, name_token=name_token, constructor=None
                ),
                block=body,
            ),
            keyword=scope_token or kw_token.with_type(TokenType.PUB),
        )

    @staticmethod
    def func_decl_stmt_checker(parser: Parser) -> bool:
        return parser.check_sequence(
            (
                TokenType.PUB,
                TokenType.PRIV,
                SoftKeyword.SPEC,
                SoftKeyword.STRUCT,
                SoftKeyword.PROP,
                TokenType.TYPE,
            ),
            TokenType.ID,
            TokenType.LPAR,
        ) or parser.check_sequence(
            (
                TokenType.PUB,
                TokenType.PRIV,
            ),
            (SoftKeyword.STRUCT, SoftKeyword.PROP, TokenType.TYPE),
            TokenType.ID,
            TokenType.LPAR,
        )

    @reg_stmt(check=func_decl_stmt_checker)
    def func_decl_stmt(self) -> ASTNode:
        scope_token = self.match(TokenType.PUB, TokenType.PRIV, SoftKeyword.SPEC)
        kw_token = self.match(SoftKeyword.STRUCT, SoftKeyword.PROP, TokenType.TYPE)

        match (scope_token, kw_token):
            case (None, None):
                raise SafulateSyntaxError(
                    "Scope keyword and declaration keyword both missing"
                )
            case (Token(), None):
                kw_token = scope_token
            case (None, Token()):
                scope_token = Token(TokenType.PUB, "pub", kw_token.start)
            case (Token(), Token()):
                pass

        name = self.consume(TokenType.ID, "Expected function name")
        func = self._func_decl(scope_token=scope_token, kw_token=kw_token, name=name)
        self.consume(TokenType.SEMI, "Expected ';'")

        return ASTVarDecl(name=name, value=func, keyword=scope_token)

    @reg_stmt(TokenType.WHILE)
    def while_stmt(self) -> ASTNode:
        kw_token = self.consume(TokenType.WHILE)
        condition = self.expr()
        body = self.block()

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTWhile(condition=condition, body=body, kw_token=kw_token)

    @reg_stmt(TokenType.FOR)
    def for_stmt(self) -> ASTNode:
        self.consume(TokenType.FOR)
        var = self.consume(TokenType.ID, "Expected name of variable for loop iteration")
        self.consume(SoftKeyword.IN)
        src = self.expr()
        body = self.block()

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTForLoop(var_name=var, source=src, body=body)

    @reg_stmt(TokenType.RETURN)
    def return_stmt(self) -> ASTNode:
        kwd = self.consume(TokenType.RETURN)
        expr = None
        if not self.check(TokenType.SEMI):
            expr = self.expr()

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTReturn(kwd, expr)

    @reg_stmt((TokenType.BREAK, TokenType.CONTINUE))
    def continue_break_stmt(self) -> ASTNode:
        kwd = self.consume((TokenType.BREAK, TokenType.CONTINUE))
        expr = None if self.check(TokenType.SEMI) else self.expr()

        self.consume(TokenType.SEMI, "Expected ';'")
        return {TokenType.CONTINUE: ASTContinue, TokenType.BREAK: ASTBreak}[kwd.type](
            kwd, expr
        )

    @reg_stmt(TokenType.REQ)
    def require_stmt(self) -> ASTNode:
        kwd = self.consume(TokenType.REQ, "Expected 'req'")

        if node := self.require_version_stmt(kwd):
            return node

        names: list[Token] | Token | None = None
        specific_import_open_paren = self.peek()
        if specific_import_open_paren := self.match(TokenType.LPAR):
            names = []
            names.append(self.consume(TokenType.ID, "Expected ID"))

            while self.check_sequence(TokenType.COMMA, TokenType.ID):
                self.advance()
                names.append(self.consume(TokenType.ID, "Expected ID"))

            self.consume(TokenType.RPAR, "Expected ')'")
        else:
            names = self.match(TokenType.ID)
            if not names:
                raise SafulateSyntaxError("Expected name of import", self.peek())

        source: Token | None = None
        if self.match(TokenType.AT):
            source = self.match(TokenType.ID, TokenType.STR)
            if not source:
                raise SafulateSyntaxError(
                    "Expected Source after @ symbol in req statement", self.peek()
                )

        self.consume(TokenType.SEMI, "Expected ';'")

        if isinstance(names, Token):
            if source is None:
                source = names

            return ASTImportReq(name=names, source=source)
        else:
            if source is None:
                raise SafulateSyntaxError(
                    "Expected '@ source' for specific imports",
                    specific_import_open_paren,
                )

            name_token = Token(
                TokenType.ID,
                f"##SAFULATE-SPECIFIC-REQ-BLOCK##:{source.lexeme}",
                kwd.start,
            )
            return ASTBlock(
                [
                    ASTImportReq(source=source, name=name_token),
                    *[
                        ASTVarDecl(
                            name=name,
                            keyword=Token(TokenType.PUB, "pub", kwd.start),
                            value=ASTCall.get_attr(
                                expr=ASTAtom(name_token),
                                attr=name,
                                dot=Token.mock(TokenType.DOT, start=kwd.start),
                            ),
                        )
                        for name in names
                    ],
                    ASTDel(name_token),
                ],
                force_unscoped=True,
            )

    def require_version_stmt(self, kwd: Token) -> ASTNode | None:
        version_sequence = (
            TokenType.ID,
            TokenType.DOT,
            (TokenType.NUM, TokenType.STAR),
        )
        left: _PackagingVersion | None = None
        right: _PackagingVersion | None = None
        op: Token | None = None

        if self.check_sequence(TokenType.MINUS, *version_sequence):
            op = self.consume(TokenType.MINUS, "Expected '-'")
            left = self._get_version()
        elif self.check_sequence(*version_sequence, TokenType.PLUS):
            left = self._get_version()
            op = self.consume(TokenType.PLUS, "Expected '+")
        elif self.check_sequence(*version_sequence, TokenType.MINUS, *version_sequence):
            left = self._get_version()
            op = self.consume(TokenType.MINUS, "Expected '-'")
            right = self._get_version()
        elif self.check_sequence(*version_sequence):
            left = self._get_version()
        else:
            return

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTVersionReq(keyword=kwd, left=left, op=op, right=right)

    def _get_version(self) -> _PackagingVersion:
        major = self.consume(TokenType.ID, "Expected major value")
        self.consume(TokenType.DOT, "Expected '.'")
        minor = self.consume((TokenType.NUM, TokenType.STAR), "Expected minor value")
        try:
            return _PackagingVersion(
                f"{major.lexeme.removeprefix('v')}{'' if minor.type is TokenType.STAR else ('.' + minor.lexeme)}"
            )
        except InvalidVersion:
            raise SafulateSyntaxError("Invalid Verson", major) from None

    @reg_stmt(TokenType.RAISE)
    def raise_stmt(self) -> ASTNode:
        kwd = self.consume(TokenType.RAISE)
        expr = self.expr()

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTRaise(expr, kwd)

    @reg_stmt(TokenType.DEL)
    def del_stmt(self) -> ASTNode:
        self.consume(TokenType.DEL)
        var = self.consume(TokenType.ID, "Expected ID for deletion")

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTDel(var)

    @reg_stmt(TokenType.TRY)
    def try_catch_stmt(self) -> ASTNode:
        self.consume(TokenType.TRY)
        body = self.block()

        catch_branches: list[ASTTryCatch_CatchBranch] = []
        while self.match(SoftKeyword.CATCH):
            error_var: Token | None = None
            target: tuple[Token, ASTNode] | None = None

            while not self.check(TokenType.LBRC):
                if self.check_sequence(SoftKeyword.AS, TokenType.ID, TokenType.LBRC):
                    self.consume(SoftKeyword.AS)
                    error_var = self.consume(TokenType.ID, "Expected error var name")
                else:
                    target = (self.peek(), self.expr())

            catch_branches.append(
                ASTTryCatch_CatchBranch(
                    body=self.block(), target=(target), var=error_var
                )
            )

        else_branch = None
        if self.match(SoftKeyword.ELSE):
            else_branch = self.block()

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTTryCatch(
            body=body, catch_branches=catch_branches, else_branch=else_branch
        )

    @reg_stmt(SoftKeyword.SWITCH)
    def switch_case_stmt(self) -> ASTNode:
        kwd = self.consume(SoftKeyword.SWITCH)
        switch_expr = self.expr()
        self.consume(TokenType.LBRC, "Expected '{'")
        cases: list[tuple[ASTNode, ASTBlock]] = []
        else_branch = None

        while 1:
            if not self.match(SoftKeyword.CASE):
                break

            if self.check(TokenType.LBRC):
                if else_branch is not None:
                    raise SafulateSyntaxError(
                        "A plain case has already been registered", self.peek()
                    )
                else_branch = self.block()
            else:
                cases.append((self.expr(), self.block()))

        if len(cases) == 0:
            raise SafulateSyntaxError("Switch/Case requires at least 1 case", kwd)

        self.consume(TokenType.SEMI, "Expected ';'")
        self.consume(TokenType.RBRC, "Expected '}'")
        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTSwitchCase(
            cases=cases, expr=switch_expr, else_branch=else_branch, kw=kwd
        )

    # region expr

    def expr(self) -> ASTNode:
        if expr := self._execute_cases(self.expr_cases):
            return expr

        raise SafulateSyntaxError("Expected Expression", self.peek())

    @reg_expr((TokenType.PUB, TokenType.PRIV), TokenType.LPAR)
    def func_decl_expr(self) -> ASTNode:
        kw_token = self.consume(
            TokenType.PUB,
            "Expected 'pub' keyword for func declaration as an expression",
        )
        return self._func_decl(scope_token=kw_token, kw_token=kw_token, name=None)

    @reg_expr((TokenType.PUB, TokenType.PRIV))
    def var_decl(self) -> ASTNode:
        keyword = self.consume(
            (TokenType.PUB, TokenType.PRIV), "Expected var decl keyword"
        )
        name = self.consume(TokenType.ID, "Expected variable name")

        if self.check(TokenType.COLON):
            self.annotation()

        return ASTVarDecl(
            keyword=keyword,
            name=name,
            value=self.expr() if self.match(TokenType.EQ) else None,
        )

    @reg_expr(TokenType.IF)
    def if_expr(self) -> ASTNode:
        kw_token = self.consume(TokenType.IF)
        condition = self.expr()
        body = self.block()
        else_branch = None
        if self.match(SoftKeyword.ELSE):
            else_branch = self.block()

        return ASTIf(
            condition=condition,
            body=body,
            else_branch=else_branch,
            kw_token=kw_token,
        )

    @reg_expr(
        TokenType.ID,
        (
            TokenType.EQ,
            TokenType.PLUSEQ,
            TokenType.MINUSEQ,
            TokenType.STAREQ,
            TokenType.STARSTAREQ,
            TokenType.SLASHEQ,
        ),
    )
    def assign(self) -> ASTNode:
        name = self.advance()  # We know it's the right type b/c of check above
        op = self.advance()
        value = self.expr()

        match op.type:
            case TokenType.PLUSEQ:
                value = ASTBinary(
                    ASTAtom(name), Token(TokenType.PLUS, op.lexeme, op.start), value
                )
            case TokenType.MINUSEQ:
                value = ASTBinary(
                    ASTAtom(name), Token(TokenType.MINUS, op.lexeme, op.start), value
                )
            case TokenType.STAREQ:
                value = ASTBinary(
                    ASTAtom(name), Token(TokenType.STAR, op.lexeme, op.start), value
                )
            case TokenType.STARSTAREQ:
                value = ASTBinary(
                    ASTAtom(name), Token(TokenType.STARSTAR, op.lexeme, op.start), value
                )
            case TokenType.SLASHEQ:
                value = ASTBinary(
                    ASTAtom(name), Token(TokenType.SLASH, op.lexeme, op.start), value
                )
            case _:
                pass
        return ASTAssign(name, value)

    @reg_expr(TokenType.LSQB)
    def list_syntax(self) -> ASTNode:
        self.consume(TokenType.LSQB)
        parts: list[ASTBlock] = []
        temp: list[ASTNode] = []

        while not self.check(TokenType.RSQB):
            if self.check(TokenType.COMMA):
                parts.append(ASTBlock(temp))
                temp = []
                self.advance()
            else:
                temp.append(self.expr())

        parts.append(ASTBlock(temp))
        self.consume(TokenType.RSQB, "Expected ']'")

        return ASTList(parts)

    @reg_expr(TokenType.LPAR)
    def expr_group_syntax(self) -> ASTNode:
        self.consume(TokenType.LPAR)
        expr = self.expr()
        self.consume(TokenType.RPAR)
        return expr

    @reg_expr(TokenType.FSTR_START)
    def fstring(self) -> ASTNode:
        parts: list[ASTNode] = []
        start_token = self.peek()
        end_reached = False

        while 1:
            if self.check(TokenType.FSTR_START, TokenType.FSTR_MIDDLE) or (
                end_reached := self.check(TokenType.FSTR_END)
            ):
                self.tokens[self.current].type = TokenType.STR
                parts.append(self.atom())
            else:
                parts.append(self.expr())
            if end_reached:
                break

        node = parts.pop(0)
        while parts:
            node = ASTBinary(
                node, Token(TokenType.PLUS, "", start_token.start), parts.pop(0)
            )
        return node

    @reg_expr(TokenType.RSTRING)
    def rstring(self) -> ASTNode:
        return ASTRegex(value=self.consume(TokenType.RSTRING))

    @reg_expr((TokenType.PLUS, TokenType.MINUS, TokenType.NOT))
    def unary_ops(self) -> ASTNode:
        return ASTUnary(op=self.advance(), right=self.expr())

    @reg_expr(
        (
            TokenType.NUM,
            TokenType.STR,
            TokenType.ID,
            TokenType.PRIV_ID,
            TokenType.TYPE,
            TokenType.ELLIPSIS,
        )
    )
    def atom(self) -> ASTNode:
        return self.consume_binary_op(self.consume_calls(ASTAtom(self.advance())))

    def consume_calls(self, callee: ASTNode) -> ASTNode:
        while token := self.match(
            TokenType.LPAR, TokenType.DOT, TokenType.LSQB, TokenType.COLON
        ):
            match token.type:
                case TokenType.LPAR | TokenType.LSQB as open_paren:
                    params: list[tuple[ParamType, str | None, ASTNode]] = []
                    has_kwargs = False
                    close_paren = {
                        TokenType.LPAR: TokenType.RPAR,
                        TokenType.LSQB: TokenType.RSQB,
                    }[open_paren]

                    if not self.match(close_paren):
                        while True:
                            if self.match(TokenType.ELLIPSIS):
                                params.append((ParamType.varkwarg, None, self.expr()))
                            elif self.match_sequence(TokenType.DOT, TokenType.DOT):
                                params.append((ParamType.vararg, None, self.expr()))
                            else:
                                expr = self.expr()
                                if isinstance(expr, ASTAssign):
                                    has_kwargs = True
                                    params.append(
                                        (ParamType.kwarg, expr.name.lexeme, expr.value)
                                    )
                                elif has_kwargs:
                                    raise SafulateSyntaxError(
                                        "Positional argument follows keyword argument",
                                        self.peek(),
                                    )
                                else:
                                    params.append((ParamType.arg, None, expr))

                            if self.match(close_paren):
                                break
                            self.consume(TokenType.COMMA, "Expected ','")

                    callee = ASTCall(callee=callee, paren=token, params=params)
                case TokenType.DOT:
                    callee = ASTCall.get_attr(
                        expr=callee,
                        attr=self.consume(TokenType.ID, "Expected attribute name"),
                        dot=Token.mock(TokenType.DOT, start=token.start),
                    )
                case TokenType.COLON:
                    callee = ASTFormat(
                        callee, self.consume(TokenType.ID, "Expected spec abbreviation")
                    )
                case _:
                    raise RuntimeError(f"Unknown call parsing for {self.peek()}")

        return callee

    def _handle_comparison(self, *ops: TokenType) -> tuple[Token, ASTNode] | None:
        for op in ops:
            if token := self.match(op):
                return token, self.expr()

    def consume_binary_op(self, left: ASTNode) -> ASTNode:
        res = self._handle_comparison(
            TokenType.EQEQ,
            TokenType.NEQ,
            TokenType.EQEQEQ,
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.STAR,
            TokenType.SLASH,
            TokenType.STARSTAR,
        )
        if res:
            return ASTBinary(left=left, op=res[0], right=res[1])
        return left
