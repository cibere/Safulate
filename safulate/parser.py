from __future__ import annotations

from typing import TYPE_CHECKING

from .asts import (
    ASTAssign,
    ASTAtom,
    ASTAttr,
    ASTBinary,
    ASTBlock,
    ASTBreak,
    ASTCall,
    ASTContinue,
    ASTDel,
    ASTEditObject,
    ASTExprStmt,
    ASTForLoop,
    ASTFuncDecl,
    ASTIf,
    ASTImportReq,
    ASTList,
    ASTNode,
    ASTPrivDecl,
    ASTProgram,
    ASTRaise,
    ASTReturn,
    ASTSpecDecl,
    ASTStructDecl,
    ASTSwitchCase,
    ASTTryCatch,
    ASTUnary,
    ASTVarDecl,
    ASTVersion,
    ASTVersionReq,
    ASTWhile,
)
from .errors import SafulateSyntaxError
from .tokens import SoftKeyword, Token, TokenType

if TYPE_CHECKING:
    from collections.abc import Callable


class Parser:
    """
    (outdated) Formal Grammar

    ```
    program: decl*
    decl:
        | var-decl
        | func-decl
        | stmt
    var-decl: "var" name:ID "=" value:expr ";"
    func-decl: "func" name:ID "(" (params:ID ("," params:ID)*)? ")" body:block
    scoped-block: source:ID "~" body:block
    stmt:
        | block
        | "if" expr:expr body:block ("else" else:block)
        | "while" expr:expr body:block
        | "return" expr:expr? ";"
        | "break" ";"
        | expr:expr ";"
    block: "{" stmts:decl* "}"
    expr: assign
    assign:
        | target:ID op:aug-assign value:assign
        | comparison
    comparison:
        | left:equality (op:(">" | "<" | ">=" | "<=") right:equality)*
        | equality
    equality:
        | left:sum (op:("==" | "!=") right:sum)*
        | sum
    sum:
        | left:product (op:("+" | "-") right:product)*
        | product
    product:
        | left:unary (op:("*" | "/") right:unary)*
        | unary
    unary:
        | op:("+" | "-") right:unary
        | power
    power:
        | left:call ("**" right:call)*
        | call
    call:
        | callee:atom ("(" (args:expr ("," args:expr)*)? ")" | "." attr:ID)*
        | version
    version:
        | "v" major:NUM ("." minor:NUM)? ("." micro:NUM)?
        | atom
    atom: "(" expr:expr ")" | NUM | STR | ID
    aug-assign: "="
    ```
    """

    def __init__(self) -> None:
        self.current = 0

    def parse(self, tokens: list[Token]) -> ASTNode:
        self.tokens = tokens
        return self.program()

    def advance(self) -> Token:
        t = self.tokens[self.current]
        self.current += 1
        return t

    def peek(self) -> Token:
        return self.tokens[self.current]

    def peek_next(self) -> Token:
        return self.tokens[self.current + 1]

    def compare(self, token: Token, type: TokenType | SoftKeyword) -> bool:
        if isinstance(type, TokenType):
            return token.type is type
        else:
            return token.type is TokenType.ID and token.lexeme == type.value

    def check(self, *types: TokenType | SoftKeyword) -> bool:
        return any(self.compare(self.peek(), type) for type in types)

    def check_next(self, *types: TokenType | SoftKeyword) -> bool:
        return any(self.compare(self.peek_next(), type) for type in types)

    def match(self, *types: TokenType | SoftKeyword) -> Token | None:
        if self.check(*types):
            return self.advance()

    def consume(self, type: TokenType | SoftKeyword, msg: str) -> Token:
        token = self.advance()

        if not self.compare(token, type):
            raise SafulateSyntaxError(msg, token)

        return token

    def binary_op(
        self, next_prec: Callable[[], ASTNode], *types: TokenType | SoftKeyword
    ) -> ASTNode:
        left = next_prec()

        while True:
            op = self.match(*types)
            if op:
                right = next_prec()

                left = ASTBinary(left, op, right)
            else:
                return left

    def program(self) -> ASTNode:
        stmts: list[ASTNode] = []

        while not self.check(TokenType.EOF):
            stmts.append(self.decl())

        return ASTProgram(stmts)

    def decl(self) -> ASTNode:
        if self.check(SoftKeyword.VAR, SoftKeyword.PRIV) and self.check_next(
            TokenType.ID
        ):
            return self.var_decl()
        elif self.check(
            SoftKeyword.FUNC, SoftKeyword.SPEC, SoftKeyword.STRUCT
        ) and self.check_next(TokenType.ID):
            return self.func_decl()
        elif self.check_next(TokenType.TILDE):
            return self.edit_object()

        return self.stmt()

    def var_decl(self) -> ASTNode:
        kw_token = self.advance()

        try:
            soft_kw = SoftKeyword(kw_token.lexeme)
        except ValueError:
            raise RuntimeError(
                f"Unknown var declaration keyword type: {kw_token!r}"
            ) from None

        cls = {SoftKeyword.VAR: ASTVarDecl, SoftKeyword.PRIV: ASTPrivDecl}[soft_kw]

        name = self.consume(TokenType.ID, "Expected variable name")
        if not self.check(TokenType.EQ):
            self.consume(TokenType.SEMI, "Expected assignment or ';'")
            return cls(name, None)

        self.advance()  # Eat `=`
        value = self.expr()
        self.consume(TokenType.SEMI, "Expected ';'")

        return cls(name, value)

    def func_decl(self) -> ASTNode:
        kw_token = self.advance()

        try:
            soft_kw = SoftKeyword(kw_token.lexeme)
        except ValueError:
            raise RuntimeError(
                f"Unknown func declaration keyword type: {kw_token!r}"
            ) from None

        cls = {
            SoftKeyword.FUNC: ASTFuncDecl,
            SoftKeyword.SPEC: ASTSpecDecl,
            SoftKeyword.STRUCT: ASTStructDecl,
        }[soft_kw]

        name = self.consume(TokenType.ID, "Expected function name")
        self.consume(TokenType.LPAR, "Expected '('")

        params: list[Token] = []
        if self.check(TokenType.ID):
            params.append(self.advance())

        while self.check(TokenType.COMMA) and self.check_next(TokenType.ID):
            self.advance()
            params.append(self.advance())

        self.consume(TokenType.RPAR, "Expected ')'")
        body = self.block()

        return cls(name=name, params=params, body=body, kw=kw_token)

    def edit_object(self) -> ASTNode:
        obj = self.version()
        self.consume(TokenType.TILDE, "Expected '~'")
        body = self.block()

        return ASTEditObject(obj, body)

    def stmt(self) -> ASTNode:
        if self.check(TokenType.LBRC):
            return self.block()
        elif self.match(TokenType.IF):
            condition = self.expr()
            body = self.block()
            else_branch = None
            if self.match(SoftKeyword.ELSE):
                else_branch = self.block()
            return ASTIf(condition, body, else_branch)
        elif self.match(TokenType.WHILE):
            condition = self.expr()
            body = self.block()
            return ASTWhile(condition, body)
        elif self.match(TokenType.FOR):
            var = self.consume(
                TokenType.ID, "Expected name of variable for loop iteration"
            )
            in_token = self.consume(TokenType.ID, "Expected 'in'")
            if in_token.lexeme != "in":
                raise SafulateSyntaxError("Expected 'in'")
            src = self.expr()
            body = self.block()

            return ASTForLoop(var_name=var, source=src, body=body)
        elif kwd := self.match(TokenType.RETURN):
            expr = None
            if not self.check(TokenType.SEMI):
                expr = self.expr()
            self.consume(TokenType.SEMI, "Expected ';'")
            return ASTReturn(kwd, expr)
        elif kwd := self.match(TokenType.BREAK):
            expr = None if self.check(TokenType.SEMI) else self.expr()
            self.consume(TokenType.SEMI, "Expected ';'")
            return ASTBreak(kwd, expr)
        elif kwd := self.match(TokenType.CONTINUE):
            expr = None if self.check(TokenType.SEMI) else self.expr()
            self.consume(TokenType.SEMI, "Expected ';'")
            return ASTContinue(kwd, expr)
        elif kwd := self.match(TokenType.REQ):
            if not self.check(TokenType.ID):
                token = self.peek()
                version = self.expr()
                self.consume(TokenType.SEMI, "Expected ';'")
                return ASTVersionReq(version, token)

            name = self.match(TokenType.ID)
            if not name:
                raise SafulateSyntaxError("Expected name of import", self.peek())

            source: Token | None = None

            if self.match(TokenType.AT):
                source = self.match(TokenType.ID, TokenType.STR)
                if not source:
                    raise SafulateSyntaxError(
                        "Expected Source after @ symbol in req statement", self.peek()
                    )

            if source is None:
                source = name

            self.consume(TokenType.SEMI, "Expected ';'")
            return ASTImportReq(name=name, source=source)
        elif kwd := self.match(TokenType.RAISE):
            expr = self.expr()
            self.consume(TokenType.SEMI, "Expected ';'")
            return ASTRaise(expr, kwd)
        elif kwd := self.match(TokenType.DEL):
            var = self.consume(TokenType.ID, "Expected ID for deletion")
            self.consume(TokenType.SEMI, "Expected ';'")
            return ASTDel(var)
        elif kwd := self.match(TokenType.TRY):
            body = self.block()

            catch_branch = None
            error_var = None
            if self.match(SoftKeyword.CATCH):
                if self.match(SoftKeyword.AS):
                    error_var = self.consume(
                        TokenType.ID, "Expected variable name after 'catch as'"
                    )
                catch_branch = self.block()

            else_branch = None
            if self.match(SoftKeyword.ELSE):
                else_branch = self.block()
            return ASTTryCatch(
                body=body,
                catch_branch=catch_branch,
                error_var=error_var,
                else_branch=else_branch,
            )
        elif kwd := self.match(SoftKeyword.SWITCH):
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

            self.consume(TokenType.RBRC, "Expected '}'")
            return ASTSwitchCase(
                cases=cases, expr=switch_expr, else_branch=else_branch, kw=kwd
            )

        expr = self.expr()
        self.consume(TokenType.SEMI, "Expected ';'")
        return ASTExprStmt(expr)

    def block(self) -> ASTBlock:
        # Only using consume because rules like `if` and `while` use it directly,
        # `stmt` rule checks for `{` first
        self.consume(TokenType.LBRC, "Expected '{'")
        stmts: list[ASTNode] = []
        while not self.check(TokenType.RBRC):
            stmts.append(self.decl())

        self.consume(TokenType.RBRC, "Expected '}'")
        return ASTBlock(stmts)

    def expr(self) -> ASTNode:
        return self.assign()

    def assign(self) -> ASTNode:
        if not (
            self.check(TokenType.ID)
            and self.check_next(
                TokenType.EQ,
                TokenType.PLUSEQ,
                TokenType.MINUSEQ,
                TokenType.STAREQ,
                TokenType.STARSTAREQ,
                TokenType.SLASHEQ,
            )
        ):
            return self.comparison()

        name = self.advance()  # We know it's the right type b/c of check above
        op = self.advance()
        value = self.assign()

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

    def comparison(self) -> ASTNode:
        return self.binary_op(
            self.equality,
            TokenType.LESS,
            TokenType.GRTR,
            TokenType.LESSEQ,
            TokenType.GRTREQ,
            TokenType.AND,
            TokenType.OR,
            TokenType.HAS,
        )

    def equality(self) -> ASTNode:
        return self.binary_op(self.sum, TokenType.EQEQ, TokenType.NEQ)

    def sum(self) -> ASTNode:
        return self.binary_op(self.product, TokenType.PLUS, TokenType.MINUS)

    def product(self) -> ASTNode:
        return self.binary_op(self.unary, TokenType.STAR, TokenType.SLASH)

    def unary(self) -> ASTNode:
        op = self.match(TokenType.PLUS, TokenType.MINUS, TokenType.NOT)
        if not op:
            return self.power()

        right = self.unary()
        return ASTUnary(op, right)

    def power(self) -> ASTNode:
        return self.binary_op(self.call, TokenType.STARSTAR)

    def call(self) -> ASTNode:
        callee = self.version()

        while token := self.match(TokenType.LPAR, TokenType.DOT, TokenType.LSQB):
            match token.type:
                case TokenType.LPAR | TokenType.LSQB as open_paren:
                    args: list[ASTNode] = []
                    close_paren = {
                        TokenType.LPAR: TokenType.RPAR,
                        TokenType.LSQB: TokenType.RSQB,
                    }[open_paren]

                    if not self.match(close_paren):
                        while True:
                            args.append(self.expr())
                            if self.match(close_paren):
                                break
                            self.consume(TokenType.COMMA, "Expected ','")

                    callee = ASTCall(callee, token, args)
                case _:
                    callee = ASTAttr(
                        callee, self.consume(TokenType.ID, "Expected attribute name")
                    )

        return callee

    def version(self) -> ASTNode:
        if not self.check(TokenType.VER):
            return self.list_syntax()

        token = self.advance()
        parts = token.lexeme.removeprefix("v").split(".")

        major = int(parts[0])
        try:
            minor = int(parts[1])
        except IndexError:
            minor = None
        try:
            micro = int(parts[2])
        except IndexError:
            micro = None

        return ASTVersion(major=major, minor=minor, micro=micro)

    def list_syntax(self) -> ASTNode:
        if not self.check(TokenType.LSQB):
            return self.atom()

        self.advance()  # eat '['
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
        self.advance()  # eat ']'

        return ASTList(parts)

    def atom(self) -> ASTNode:
        if self.match(TokenType.LPAR):
            expr = self.expr()
            self.consume(TokenType.RPAR, "Expected ')'")
            return expr

        if self.check(TokenType.FSTR_START):
            return self.fstring()
        elif not self.check(TokenType.NUM, TokenType.STR, TokenType.ID):
            raise SafulateSyntaxError("Expected expression", self.peek())

        return ASTAtom(self.advance())

    def fstring(self) -> ASTNode:
        parts: list[ASTNode] = []
        start_token = self.peek()

        while 1:
            if (orig_type := self.peek().type) in (
                TokenType.FSTR_START,
                TokenType.FSTR_MIDDLE,
                TokenType.FSTR_END,
            ):
                self.tokens[self.current].type = TokenType.STR
                node = self.atom()
                parts.append(node)
                assert isinstance(node, ASTAtom)

                if orig_type is TokenType.FSTR_END:
                    node.token.lexeme = node.token.lexeme[-1] + node.token.lexeme
                    break
                elif orig_type is TokenType.FSTR_MIDDLE:
                    node.token.lexeme = f'"{node.token.lexeme}"'
                elif orig_type is TokenType.FSTR_START:
                    node.token.lexeme = node.token.lexeme[1:] + node.token.lexeme[1]
            else:
                parts.append(self.stmt())

        node = parts.pop(0)
        while parts:
            node = ASTBinary(
                node, Token(TokenType.PLUS, "", start_token.start), parts.pop(0)
            )

        return node
