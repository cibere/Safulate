from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NamedTuple, TypeVar, cast

from packaging.version import InvalidVersion
from packaging.version import Version as _PackagingVersion

from ..errors import SafulateSyntaxError
from ..lexer import SoftKeyword, Token, TokenType
from ..properties import cached_property
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
    ASTGetPriv,
    ASTIf,
    ASTImportReq,
    ASTList,
    ASTNode,
    ASTPar,
    ASTProgram,
    ASTProperty,
    ASTRaise,
    ASTRegex,
    ASTReturn,
    ASTSwitchCase,
    ASTTryCatch,
    ASTTryCatch_CatchBranch,
    ASTTypeDecl,
    ASTUnary,
    ASTVarDecl,
    ASTVersionReq,
    ASTWhile,
)
from .enums import ParamType
from .specs import (
    BinarySpec,
    CallSpec,
    UnarySpec,
    special_cased_binary_specs,
    special_cased_unary_specs,
)

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


__all__ = ("Parser",)

CaseCallbackT = TypeVar("CaseCallbackT", bound="Callable[[Parser], ASTNode]")
ANY = "any"


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
            _cases.append(RegisteredCase(callback=func, type=type_, check=check))
            return func

        return deco

    return deco_fact


reg_expr = _reg_deco_maker("expr")
reg_stmt = _reg_deco_maker("stmt")
_cases: list[RegisteredCase] = []


class Parser:
    __slots__ = "__cs_expr_cases__", "__cs_stmt_cases__", "current", "tokens"

    def __init__(self, tokens: list[Token]) -> None:
        self.current = 0
        self.tokens = tokens

    @cached_property("__cs_expr_cases__")
    def expr_cases(self) -> list[RegisteredCase]:
        return [case for case in _cases if case.type == "expr"]

    @cached_property("__cs_stmt_cases__")
    def stmt_cases(self) -> list[RegisteredCase]:
        return [case for case in _cases if case.type == "stmt"]

    def _execute_case(self, case: RegisteredCase) -> ASTNode | None:
        return case.callback(self) if case.check(self) else None

    def _execute_cases(self, cases: list[RegisteredCase]) -> ASTNode | None:
        for case in cases:
            if res := self._execute_case(case):
                return res

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
            return token.type is TokenType.ID and token.lexme == type.value

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
        consume: bool = False,
    ) -> Iterator[Token]:
        first_captured = bool(self.check(end))

        while first_captured is False or (self.check(delimiter)):
            if first_captured:
                self.consume(delimiter, None)
            first_captured = True

            if consume:
                yield self.advance()
            else:
                yield self.peek()

        self.consume(end, None)

    def _func_params(self) -> Iterator[ASTFuncDecl_Param]:
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

            if self.check(TokenType.COLON):
                self.annotation()

            default = None
            if self.match(TokenType.EQ):
                defaulted = True
                default = self.block() if self.check(TokenType.LBRC) else self.expr()
            elif defaulted:
                raise SafulateSyntaxError(
                    "Non-default arg following a default arg", self.peek()
                )

            yield ASTFuncDecl_Param(name=param_name, default=default, type=param_type)

    def _func_decl(self, *, kw_token: Token, name: Token | None) -> ASTNode:
        paren_token = self.consume(TokenType.LPAR, "Expected '('")
        params = list(self._func_params())

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

        func = ASTFuncDecl(
            name=name,
            params=params,
            body=self.block(),
            kw_token=kw_token,
            paren_token=paren_token,
        )
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
                                lexme="without_partials",
                                start=token.start,
                            ),
                            dot=Token.mock(TokenType.DOT, start=token.start),
                        ),
                        paren=Token(type=TokenType.LPAR, lexme="(", start=token.start),
                        params=[],
                    ),
                    paren=Token(type=TokenType.LSQB, lexme="[", start=token.start),
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
                                    lexme="partial_args",
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
                                    lexme="partial_kwargs",
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

    def annotation(self) -> ASTNode:
        self.consume(TokenType.COLON, "Expected ':' to start annotation")
        expr = self.expr()
        self.consume(TokenType.SEMI, "Expected ';' to end annotation")
        return expr

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
    )
    def type_decl(self) -> ASTNode:
        scope_token = self.match(TokenType.PUB, TokenType.PRIV)
        kw_token = self.consume(
            TokenType.TYPE,
            "Expected 'type' keyword to start a type declaration statement",
        )
        name_token = self.consume(TokenType.ID, "Expected name for new type")

        if not scope_token:
            scope_token = kw_token.with_type(TokenType.PUB)

        compare_func = body = init = None
        arity = 0

        if self.check(TokenType.LPAR):
            compare_func = self._func_decl(
                kw_token=scope_token,
                name=name_token,
            )

        if (
            self.match(TokenType.TILDE)
            if compare_func
            else self.check(TokenType.LSQB, TokenType.LBRC)
        ):
            if self.match(TokenType.LSQB):
                arity = len(
                    list(self.walk_split_tokens(end=TokenType.RSQB, consume=True))
                )
            body = self.block()

        if self.check_sequence(TokenType.MINUS, TokenType.GRTR):
            self.consume(TokenType.MINUS)
            self.consume(TokenType.GRTR)

            init = self._func_decl(
                kw_token=scope_token,
                name=name_token,
            )

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTVarDecl(
            name_token,
            value=ASTTypeDecl(
                body=body,
                compare_func=compare_func,
                init=cast("ASTFuncDecl", init),
                arity=arity,
                name=name_token,
            ),
            keyword=scope_token,
        )

    @reg_stmt(SoftKeyword.PROP, TokenType.ID, TokenType.LBRC)
    def prop_decl(self) -> ASTNode:
        kw_token = self.advance()
        name = self.advance()

        if self.check(TokenType.COLON):
            self.annotation()

        body = self.block()

        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTProperty(body=body, name=name, kw_token=kw_token)

    @reg_stmt(
        (
            TokenType.PUB,
            TokenType.PRIV,
            SoftKeyword.SPEC,
        ),
        TokenType.ID,
        TokenType.LPAR,
    )
    def func_decl_stmt(self) -> ASTNode:
        kw_token = self.advance()

        name = self.consume(TokenType.ID, "Expected function name")
        func = self._func_decl(kw_token=kw_token, name=name)
        self.consume(TokenType.SEMI, "Expected ';'")

        return ASTVarDecl(name=name, value=func, keyword=kw_token)

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
                f"##SAFULATE-SPECIFIC-REQ-BLOCK##:{source.lexme}",
                kwd.start,
            )
            return ASTProgram(
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
                f"{major.lexme.removeprefix('v')}{'' if minor.type is TokenType.STAR else ('.' + minor.lexme)}"
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
        return ASTSwitchCase(
            cases=cases, expr=switch_expr, else_branch=else_branch, kw=kwd
        )

    # region expr

    def expr(self) -> ASTNode:
        if expr := self._execute_cases(self.expr_cases):
            return self.consume_binary_op(self.consume_calls(expr))

        raise SafulateSyntaxError("Expected Expression", self.peek())

    @reg_expr((TokenType.PUB, TokenType.PRIV), TokenType.LPAR)
    def func_decl_expr(self) -> ASTNode:
        kw_token = self.consume(
            TokenType.PUB,
            "Expected 'pub' keyword for func declaration as an expression",
        )
        return self._func_decl(kw_token=kw_token, name=None)

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
                    ASTAtom(name), Token(TokenType.PLUS, op.lexme, op.start), value
                )
            case TokenType.MINUSEQ:
                value = ASTBinary(
                    ASTAtom(name), Token(TokenType.MINUS, op.lexme, op.start), value
                )
            case TokenType.STAREQ:
                value = ASTBinary(
                    ASTAtom(name), Token(TokenType.STAR, op.lexme, op.start), value
                )
            case TokenType.STARSTAREQ:
                value = ASTBinary(
                    ASTAtom(name), Token(TokenType.STARSTAR, op.lexme, op.start), value
                )
            case TokenType.SLASHEQ:
                value = ASTBinary(
                    ASTAtom(name), Token(TokenType.SLASH, op.lexme, op.start), value
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

    @reg_expr((*UnarySpec.all_values(), *special_cased_unary_specs))
    def unary_ops(self) -> ASTNode:
        return ASTUnary(op=self.advance(), right=self.expr())

    @reg_expr(TokenType.PAR)
    def par_atom(self) -> ASTPar:
        levels: list[Token] = []
        while self.check(TokenType.PAR):
            levels.append(self.advance())

        return ASTPar(levels)

    @reg_expr(TokenType.GET_PRIV)
    def get_priv(self) -> ASTNode:
        levels: list[Token] = []
        while self.check(TokenType.GET_PRIV):
            levels.append(self.advance())

        return ASTGetPriv(
            levels, self.consume(TokenType.ID, "Expected name of private var")
        )

    @reg_expr(TokenType.LESS, TokenType.COLON)
    def inline_type_decl(self) -> ASTNode:
        self.consume(TokenType.LESS)
        val = self.annotation()
        self.consume(TokenType.GRTR, "Expected '>' to end inline type definition")
        return val

    @reg_expr(
        (
            TokenType.NUM,
            TokenType.STR,
            TokenType.ID,
            TokenType.TYPE,
            TokenType.ELLIPSIS,
        )
    )
    def atom(self) -> ASTNode:
        return ASTAtom(self.advance())

    def consume_calls(self, callee: ASTNode) -> ASTNode:
        while token := self.match(
            *(val for val in CallSpec.all_values() if type(val) is TokenType)
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
                                        (ParamType.kwarg, expr.name.lexme, expr.value)
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
                        callee, self.consume(TokenType.ID, "Expected format input")
                    )
                case _:
                    raise RuntimeError(f"Unknown call parsing for {self.peek()}")

        return callee

    def _handle_comparison(self, *ops: TokenType) -> tuple[Token, ASTNode] | None:
        for op in ops:
            if token := self.match(op):
                return token, self.expr()

    def consume_binary_op(self, left: ASTNode) -> ASTNode:
        if self.match(TokenType.TILDE):
            return ASTEditObject(left, self.block())

        for op in (*BinarySpec.all_values(), *special_cased_binary_specs):
            if token := self.match(op):
                return ASTBinary(left=left, op=token, right=self.expr())

        return left
