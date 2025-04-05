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
    ASTExprStmt,
    ASTFuncDecl,
    ASTIf,
    ASTImportReq,
    ASTNode,
    ASTPrivDecl,
    ASTProgram,
    ASTRaise,
    ASTReturn,
    ASTScopedBlock,
    ASTSpecDecl,
    ASTUnary,
    ASTVarDecl,
    ASTVersion,
    ASTVersionReq,
    ASTWhile,
)
from .errors import SafulateSyntaxError
from .tokens import Token, TokenType

if TYPE_CHECKING:
    from collections.abc import Callable


class Parser:
    """
    Formal Grammar

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

    def check(self, *types: TokenType) -> bool:
        return self.peek().type in types

    def check_next(self, *types: TokenType) -> bool:
        return self.peek_next().type in types

    def match(self, *types: TokenType) -> Token | None:
        if self.check(*types):
            return self.advance()

    def consume(self, type: TokenType, msg: str) -> Token:
        t = self.advance()

        if t.type != type:
            raise SafulateSyntaxError(msg, t)

        return t

    def binary_op(self, next_prec: Callable[[], ASTNode], *types: TokenType) -> ASTNode:
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
        if self.check(TokenType.VAR, TokenType.PRIV):
            return self.var_decl()
        if self.check(TokenType.FUNC, TokenType.SPEC):
            return self.func_decl()
        if self.check_next(TokenType.TILDE):
            return self.scoped_block()

        return self.stmt()

    def var_decl(self) -> ASTNode:
        kw_token = self.advance()
        match kw_token.type:
            case TokenType.VAR:
                cls = ASTVarDecl
            case TokenType.PRIV:
                cls = ASTPrivDecl
            case _ as other:
                raise ValueError(f"Unknown var declaration keyword type: {other!r}")

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
        match kw_token.type:
            case TokenType.FUNC:
                cls = ASTFuncDecl
            case TokenType.SPEC:
                cls = ASTSpecDecl
            case _ as other:
                raise ValueError(f"Unknown func declaration keyword type: {other!r}")

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

        return cls(name, params, body)

    def scoped_block(self) -> ASTNode:
        source = self.version()
        self.consume(TokenType.TILDE, "Expected '~'")

        body = self.block()

        return ASTScopedBlock(source, body)

    def stmt(self) -> ASTNode:
        if self.check(TokenType.LBRC):
            return self.block()
        if self.match(TokenType.IF):
            condition = self.expr()
            body = self.block()
            else_branch = None
            if self.match(TokenType.ELSE):
                else_branch = self.block()
            return ASTIf(condition, body, else_branch)
        if self.match(TokenType.WHILE):
            condition = self.expr()
            body = self.block()
            return ASTWhile(condition, body)
        if kwd := self.match(TokenType.RETURN):
            expr = None
            if not self.check(TokenType.SEMI):
                expr = self.expr()
            self.consume(TokenType.SEMI, "Expected ';'")
            return ASTReturn(kwd, expr)
        if kwd := self.match(TokenType.BREAK):
            expr = None if self.check(TokenType.SEMI) else self.expr()
            self.consume(TokenType.SEMI, "Expected ';'")
            return ASTBreak(kwd, expr)
        if kwd := self.match(TokenType.REQ):
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
        if kwd := self.match(TokenType.RAISE):
            expr = self.expr()
            self.consume(TokenType.SEMI, "Expected ';'")
            return ASTRaise(expr, kwd)

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
        # print(f"Assign: {self.peek()} - {self.peek_next()}")
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
        # print(f"{name=}")
        # print(f"{op=}")
        # print(f"{value=}")

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
                    ASTAtom(name), Token(TokenType.SLASHEQ, op.lexeme, op.start), value
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
        )

    def equality(self) -> ASTNode:
        return self.binary_op(self.sum, TokenType.EQEQ, TokenType.NEQ)

    def sum(self) -> ASTNode:
        return self.binary_op(self.product, TokenType.PLUS, TokenType.MINUS)

    def product(self) -> ASTNode:
        return self.binary_op(self.unary, TokenType.STAR, TokenType.SLASH)

    def unary(self) -> ASTNode:
        op = self.match(TokenType.PLUS, TokenType.MINUS)
        if not op:
            return self.power()

        right = self.unary()
        return ASTUnary(op, right)

    def power(self) -> ASTNode:
        return self.binary_op(self.call, TokenType.STARSTAR)

    def call(self) -> ASTNode:
        callee = self.version()

        while token := self.match(TokenType.LPAR, TokenType.DOT):
            if token.type != TokenType.LPAR:
                callee = ASTAttr(
                    callee, self.consume(TokenType.ID, "Expected attribute name")
                )
            else:
                args: list[ASTNode] = []

                if not self.match(TokenType.RPAR):
                    while True:
                        args.append(self.expr())
                        if self.match(TokenType.RPAR):
                            break
                        self.consume(TokenType.COMMA, "Expected ','")

                callee = ASTCall(callee, token, args)

        return callee

    def version(self) -> ASTNode:
        if not self.check(TokenType.VER):
            return self.atom()

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

    def atom(self) -> ASTNode:
        if self.match(TokenType.LPAR):
            expr = self.expr()
            self.consume(TokenType.RPAR, "Expected ')'")
            return expr

        if not self.check(TokenType.NUM, TokenType.STR, TokenType.ID, TokenType.NULL):
            raise SafulateSyntaxError("Expected expression", self.peek())

        return ASTAtom(self.advance())
