from __future__ import annotations

import re
from contextlib import contextmanager
from typing import TYPE_CHECKING

from packaging.version import Version

from ._version import __version__
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
    ASTFormat,
    ASTFuncDecl,
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
    ASTUnary,
    ASTVarDecl,
    ASTVersion,
    ASTVersionReq,
    ASTVisitor,
    ASTWhile,
)
from .environment import Environment
from .errors import (
    ErrorManager,
    SafulateAttributeError,
    SafulateBreakoutError,
    SafulateError,
    SafulateImportError,
    SafulateInvalidContinue,
    SafulateInvalidReturn,
    SafulateScopeError,
    SafulateTypeError,
    SafulateValueError,
    # SafulateVersionConflict,
)
from .native_context import NativeContext
from .py_libs import LibManager
from .tokens import SoftKeyword, Token, TokenType
from .values import (
    FuncValue,
    ListValue,
    NumValue,
    ObjectValue,
    PatternValue,
    PropertyValue,
    StrValue,
    TypeValue,
    Value,
    null,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ("TreeWalker",)


class TreeWalker(ASTVisitor):
    __slots__ = ("env", "import_cache")

    def __init__(
        self, *, env: Environment | None = None, lib_manager: LibManager | None = None
    ) -> None:
        self.version = Version(__version__)
        self.import_cache: dict[str, ObjectValue] = {}

        self.libs = lib_manager or LibManager()

        if env:
            self.env = env
        else:
            self.env = Environment().add_builtins()

    def ctx(self, token: Token) -> NativeContext:
        return NativeContext(self, token)

    @contextmanager
    def scope(self, source: Value | None = None) -> Iterator[Environment]:
        old_env = self.env
        self.env = Environment(self.env, scope=source)
        yield self.env
        self.env = old_env

    def visit_program(self, node: ASTProgram) -> Value:
        if len(node.stmts) <= 0:
            return null
        for stmt in node.stmts[:-1]:
            stmt.visit(self)

        return node.stmts[-1].visit(self)

    def visit_unscoped_block(self, node: ASTBlock) -> Value:
        if len(node.stmts) <= 0:
            return null

        for stmt in node.stmts[:-1]:
            stmt.visit(self)
        res = node.stmts[-1].visit(self)

        return res

    def visit_block(self, node: ASTBlock) -> Value:
        with self.scope():
            return self.visit_unscoped_block(node)

    def visit_edit_object(self, node: ASTEditObject) -> Value:
        src = node.obj.visit(self)
        with self.scope(source=src):
            self.visit_unscoped_block(node.block)
        return src

    def visit_if(self, node: ASTIf) -> Value:
        if node.condition.visit(self).bool_spec(self.ctx(node.kw_token)):
            return node.body.visit(self)
        elif node.else_branch:
            return node.else_branch.visit(self)
        return null

    def visit_while(self, node: ASTWhile) -> Value:
        val = null

        while node.condition.visit(self).bool_spec(self.ctx(node.kw_token)):
            try:
                val = node.body.visit(self)
            except SafulateBreakoutError as e:
                e.check()
                break
            except SafulateInvalidContinue:
                pass

        return val

    def visit_for_loop(self, node: ASTForLoop) -> Value:
        src = node.source.visit(self)
        if not isinstance(src, ListValue):
            with ErrorManager(token=node.var_name):
                src = self.ctx(node.var_name).invoke_spec(src, "iter")
                if not isinstance(src, ListValue):
                    raise SafulateValueError(
                        f"{src.repr_spec(self.ctx(node.var_name))} is not iterable"
                    )

        loops = src.value.copy()
        val = null
        while loops:
            item = loops.pop(0)

            try:
                with self.scope() as env:
                    env.declare(node.var_name)
                    env[node.var_name] = item
                    val = node.body.visit(self)
            except SafulateInvalidContinue as e:
                e.handle_skips(loops)
            except SafulateBreakoutError as e:
                e.check()
                break

        return val

    def visit_return(self, node: ASTReturn) -> Value:
        if node.expr:
            value = node.expr.visit(self)
            raise SafulateInvalidReturn(value, node.keyword)

        raise SafulateInvalidReturn(null, node.keyword)

    def _visit_continue_and_break(self, node: ASTBreak | ASTContinue) -> Value:
        is_break = isinstance(node, ASTBreak)

        with ErrorManager(token=node.keyword):
            if node.amount is None:
                amount = 1
            else:
                amount_node = node.amount.visit(self)
                if not isinstance(amount_node, NumValue):
                    raise SafulateTypeError(
                        f"Expected a number for {'break' if is_break else 'continue'} amount, got {amount_node.repr_spec(self.ctx(node.keyword))} instead.",
                    )
                amount = int(amount_node.value)

            if amount == 0:
                return null
            elif amount < 0:
                msg = (
                    "You can't breakout of a negative number of loops"
                    if is_break
                    else "You can't skip a negative number of loops"
                )
                raise SafulateValueError(msg)

            if is_break:
                raise SafulateBreakoutError(amount)
            raise SafulateInvalidContinue(amount)

    def visit_break(self, node: ASTBreak) -> Value:
        return self._visit_continue_and_break(node)

    def visit_continue(self, node: ASTContinue) -> Value:
        return self._visit_continue_and_break(node)

    def visit_expr_stmt(self, node: ASTExprStmt) -> Value:
        value = node.expr.visit(self)
        return value

    def visit_var_decl(self, node: ASTVarDecl) -> Value:
        value = null if node.value is None else node.value.visit(self)
        match node.kw:
            case SoftKeyword.PUB:
                self.env.declare(node.name)
                self.env[node.name] = value
            case SoftKeyword.PRIV:
                self.env.set_priv(node.name, value)
            case _:
                raise RuntimeError(f"Unknown var decl keyword: {node.kw!r}")
        return value

    def visit_func_decl(self, node: ASTFuncDecl) -> Value:
        value = FuncValue(
            name=node.name,
            params=node.params,  # pyright: ignore[reportArgumentType]
            body=node.body,
            extra_vars=self.env.values.copy(),
        )
        self.env._set_parent(value)

        match node.soft_kw:
            case SoftKeyword.PUB:
                self.env.declare(node.name)
                self.env[node.name] = value
            case SoftKeyword.PRIV:
                self.env.set_priv(node.name, value)
            case SoftKeyword.SPEC:
                if self.env.scope is None:
                    raise SafulateScopeError(
                        "specs can only be set in an edit object statement",
                        node.kw_token,
                    )

                try:
                    current_spec = self.env.scope.specs[node.name.lexeme]
                    assert isinstance(current_spec, FuncValue)
                except KeyError:
                    raise SafulateValueError(
                        f"there is no spec named {node.name.lexeme!r}", node.name
                    ) from None

                if node.name.lexeme != "call" and value.arity != current_spec.arity:
                    raise SafulateValueError(
                        f"number of params for {node.name.lexeme!r} spec do not compare",
                        node.paren_token,
                    )

                self.env.scope.specs[node.name.lexeme] = value
                return value
            case _:
                raise RuntimeError(f"Unknown func decl keyword: {node.soft_kw!r}")
        return value

    def visit_assign(self, node: ASTAssign) -> Value:
        value = node.value.visit(self)
        self.env[node.name] = value
        return value

    def visit_binary(self, node: ASTBinary) -> Value:
        left = node.left.visit(self)
        right = node.right.visit(self)

        spec_name = {
            TokenType.PLUS: "add",
            TokenType.MINUS: "sub",
            TokenType.STAR: "mul",
            TokenType.STARSTAR: "pow",
            TokenType.SLASH: "div",
            TokenType.EQEQ: "eq",
            TokenType.NEQ: "neq",
            TokenType.LESS: "less",
            TokenType.GRTR: "grtr",
            TokenType.LESSEQ: "lesseq",
            TokenType.GRTREQ: "grtreq",
            TokenType.AMP: "amp",
            TokenType.PIPE: "pipe",
            TokenType.HAS: "has_item",
        }.get(node.op.type)

        ctx = self.ctx(node.op)
        if spec_name is None:
            match node.op.type:
                case TokenType.OR:
                    if left.bool_spec(ctx):
                        return left
                    if right.bool_spec(ctx):
                        return right
                    return null
                case TokenType.AND:
                    return NumValue(
                        1 if left.bool_spec(ctx) and right.bool_spec(ctx) else 0
                    )
                case _:
                    raise ValueError(
                        f"Invalid token type {node.op.type.name} for binary operator"
                    )

        with ErrorManager(token=node.op):
            return ctx.invoke_spec(left, spec_name, right)

    def visit_unary(self, node: ASTUnary) -> Value:
        right = node.right.visit(self)

        spec_name = {
            TokenType.PLUS: "uadd",
            TokenType.MINUS: "neg",
            TokenType.NOT: "not",
            TokenType.BOOL: "bool",
        }.get(node.op.type, None)
        if spec_name is None:
            raise ValueError(
                f"Invalid token type {node.op.type.name} for unary operator"
            )

        with ErrorManager(token=node.op):
            return self.ctx(node.op).invoke_spec(right, spec_name)

    def visit_call(self, node: ASTCall) -> Value:
        func = node.callee.visit(self)

        if node.paren.type is TokenType.LSQB:
            func = func.specs["altcall"]

        return self.ctx(node.paren).invoke(
            func,
            *[arg.visit(self) for arg in node.args],
            **{name: value.visit(self) for name, value in node.kwargs.items()},
        )

    def visit_atom(self, node: ASTAtom) -> Value:
        match node.token.type:
            case TokenType.NUM:
                return NumValue(float(node.token.lexeme))
            case TokenType.STR:
                return StrValue(node.token.lexeme)
            case TokenType.ID:
                return self.env[node.token]
            case TokenType.PRIV_ID:
                return self.env.get_priv(node.token)
            case _:
                raise ValueError(f"Invalid atom type {node.token.type.name}")

    def visit_attr(self, node: ASTAttr) -> Value:
        obj = node.expr.visit(self)

        with ErrorManager(token=node.attr):
            if node.attr.type is not TokenType.ID:
                raise ValueError(
                    f"Invalid token type {node.attr.type.name} for attribute access"
                )

            if node.is_spec:
                try:
                    return obj.specs[node.attr.lexeme]
                except KeyError:
                    raise SafulateAttributeError(
                        f"No spec named {node.attr.lexeme!r}", node.attr
                    )

            return self.ctx(node.attr).invoke_spec(
                obj, "get_attr", StrValue(node.attr.lexeme)
            )

    def visit_version(self, node: ASTVersion) -> Value:
        raise RuntimeError("version not allowed")

    def visit_version_req(self, node: ASTVersionReq) -> Value:
        raise RuntimeError("version not allowed")

    # def visit_version(self, node: ASTVersion) -> VersionValue:
    #     major = NumValue(node.major)
    #     minor = null if node.minor is None else NumValue(node.minor)
    #     micro = null if node.micro is None else NumValue(node.micro)

    #     return VersionValue(major=major, minor=minor, micro=micro)

    # def visit_version_req(self, node: ASTVersionReq) -> Value:
    #     with ErrorManager(token=node.token):
    #         match node.version.visit(self):
    #             case VersionValue() as ver_value:
    #                 ver = Version(str(ver_value))
    #                 if ver != self.version:
    #                     raise SafulateVersionConflict(
    #                         f"Current version (v{self.version}) is not equal to the required version (v{ver})"
    #                     )
    #             case VersionConstraintValue(constraint="-", left=null) as const:
    #                 ver = Version(str(const.right))

    #                 if self.version > ver:
    #                     raise SafulateVersionConflict(
    #                         f"Current version (v{self.version}) is above the maximum set version allowed (v{ver})"
    #                     )
    #             case VersionConstraintValue(constraint="+", left=null) as const:
    #                 ver = Version(str(const.right))

    #                 if self.version < ver:
    #                     raise SafulateVersionConflict(
    #                         f"Current version (v{self.version}) is below the minimum set version allowed (v{ver})"
    #                     )
    #             case VersionConstraintValue(constraint="-") as const:
    #                 left_ver = Version(str(const.left))
    #                 right_ver = Version(str(const.right))

    #                 if not (left_ver < self.version < right_ver):
    #                     raise SafulateVersionConflict(
    #                         f"Current version (v{self.version}) outside of the allowed range ({const})"
    #                     )
    #             case _ as x:
    #                 raise RuntimeError(f"Unknown version req combination: {x!r}")
    #         return null  # pyright: ignore[reportPossiblyUnboundVariable] # pyright is high

    def visit_import_req(self, node: ASTImportReq) -> Value:
        with ErrorManager(token=node.source):
            value = self.import_cache.get(node.source.lexeme)

            if value is None:
                match node.source.type:
                    case TokenType.ID:
                        value = self.libs.get_or_load(
                            node.source.lexeme, ctx=self.ctx(node.source)
                        )
                    case TokenType.STR:
                        raise SafulateImportError("Url imports are not allowed yet")
                    case other:
                        raise RuntimeError(f"Unknown import source: {other.name!r}")
            if value is None:
                raise SafulateImportError(
                    f"{node.source.lexeme!r} could not be located"
                )

            self.env.declare(node.name)
            self.env[node.name] = value
            self.import_cache[node.source.lexeme] = value
            return value

    def visit_raise(self, node: ASTRaise) -> Value:
        val = node.expr.visit(self)
        raise SafulateError(val.repr_spec(self.ctx(node.kw)), token=node.kw, obj=val)

    def visit_del(self, node: ASTDel) -> Value:
        del self.env.values[node.var.lexeme]
        return null

    def visit_try_catch(self, node: ASTTryCatch) -> Value:
        try:
            node.body.visit(self)
        except SafulateError as e:
            if not node.catch_branches:
                return null

            for branch in node.catch_branches:
                if branch.target is not None:
                    target_token = branch.target[0]
                    target = branch.target[1].visit(self)

                    if not isinstance(target, TypeValue):
                        raise SafulateTypeError(
                            f"Expected Type object, got {target.repr_spec(self.ctx(target_token))} instead"
                        )
                    if not target.check(self.ctx(target_token), e.saf_value).bool_spec(
                        self.ctx(target_token)
                    ):
                        continue

                with self.scope() as env:
                    if branch.var:
                        env.declare(branch.var)
                        env[branch.var] = e.saf_value

                    return self.visit_unscoped_block(branch.body)
            raise e

        if node.else_branch is None:
            return null

        return node.else_branch.visit(self)

    def _visit_switch_case_entry(
        self, body: ASTBlock, loops: list[tuple[ASTNode, ASTBlock]]
    ) -> Value:
        try:
            return body.visit(self)
        except SafulateInvalidContinue as e:
            next_loop = e.handle_skips(loops)

            if next_loop is None:
                return null
            return self._visit_switch_case_entry(next_loop[-1], loops)

    def visit_switch_case(self, node: ASTSwitchCase) -> Value:
        key = node.expr.visit(self)
        cases = node.cases.copy()

        while cases:
            expr, body = cases.pop(0)
            ctx = self.ctx(node.kw)

            res = ctx.invoke_spec(key, "eq", expr.visit(self))
            if not res.bool_spec(ctx):
                continue

            self._visit_switch_case_entry(body, cases)
            return null

        if node.else_branch:
            node.else_branch.visit(self)
        return null

    def visit_list(self, node: ASTList) -> ListValue:
        return ListValue([child.visit(self) for child in node.children])

    def visit_format(self, node: ASTFormat) -> Value:
        spec = {"r": "repr", "s": "str"}.get(node.spec.lexeme)
        args: tuple[Value, ...] = ()

        if spec is None:
            args = (StrValue(node.spec.lexeme),)
            spec = "format"

        return self.ctx(node.spec).invoke_spec(node.obj.visit(self), spec, *args)

    def visit_property(self, node: ASTProperty) -> Value:
        val = PropertyValue(FuncValue(name=node.name, params=[], body=node.body))
        self.env.declare(node.name)
        self.env[node.name] = val
        return val

    def visit_regex(self, node: ASTRegex) -> Value:
        return PatternValue(re.compile(node.value.lexeme[2:-1]))
