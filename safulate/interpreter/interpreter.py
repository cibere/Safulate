from __future__ import annotations

import re
from contextlib import contextmanager
from typing import TYPE_CHECKING

from packaging.version import Version as _PackagingVersion

from .._version import __version__
from ..errors import (
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
    SafulateVersionConflict,
)
from ..lexer import SoftKeyword, Token, TokenType
from ..parser import (
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
    ASTTypeDecl,
    ASTUnary,
    ASTVarDecl,
    ASTVersionReq,
    ASTVisitor,
    ASTWhile,
    BinarySpec,
    CallSpec,
    FormatSpec,
    ParamType,
    UnarySpec,
    spec_name_from_str,
)
from ..properties import cached_property
from .environment import Environment
from .lib_manager import LibManager
from .native_context import NativeContext
from .objects import (
    SafBaseObject,
    SafDict,
    SafEllipsis,
    SafFunc,
    SafList,
    SafModule,
    SafNum,
    SafProperty,
    SafStr,
    SafType,
    false,
    null,
    true,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .libs.regex import SafPattern as _SafPattern

__all__ = ("Interpreter",)


class Interpreter(ASTVisitor):
    __slots__ = ("__cs_regex_pattern_cls__", "env", "libs", "module_obj", "version")

    def __init__(self, name: str, *, lib_manager: LibManager | None = None) -> None:
        self.version = _PackagingVersion(__version__)
        self.libs = lib_manager or LibManager()
        self.module_obj = SafModule(name)
        self.env = Environment(scope=self.module_obj)

    @property
    def name(self) -> str:
        return self.module_obj.name

    @cached_property("regex_pattern_cls")
    def regex_pattern_cls(self) -> type[_SafPattern]:
        from .libs.regex import SafPattern

        return SafPattern

    def ctx(self, token: Token) -> NativeContext:
        return NativeContext(self, token)

    @contextmanager
    def scope(
        self, source: SafBaseObject | None = None, isolated_public_vars: bool = False
    ) -> Iterator[Environment]:
        old_env = self.env
        self.env = Environment(
            self.env, scope=source, isolated_public_vars=isolated_public_vars
        )
        yield self.env
        self.env = old_env

    def visit_program(self, node: ASTProgram) -> SafBaseObject:
        if len(node.stmts) <= 0:
            return null
        for stmt in node.stmts[:-1]:
            stmt.visit(self)

        return node.stmts[-1].visit(self)

    def visit_unscoped_block(self, node: ASTBlock) -> SafBaseObject:
        if len(node.stmts) <= 0:
            return null

        for stmt in node.stmts[:-1]:
            stmt.visit(self)
        res = node.stmts[-1].visit(self)

        return res

    def visit_block(self, node: ASTBlock) -> SafBaseObject:
        with self.scope():
            return self.visit_unscoped_block(node)

    def visit_edit_object(self, node: ASTEditObject) -> SafBaseObject:
        src = node.obj.visit(self)
        with self.scope(source=src):
            self.visit_unscoped_block(node.block)
        return src

    def visit_if(self, node: ASTIf) -> SafBaseObject:
        if node.condition.visit(self).bool_spec(self.ctx(node.kw_token)):
            return node.body.visit(self)
        elif node.else_branch:
            return node.else_branch.visit(self)
        return null

    def visit_while(self, node: ASTWhile) -> SafBaseObject:
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

    def visit_for_loop(self, node: ASTForLoop) -> SafBaseObject:
        ctx = self.ctx(node.var_name)
        src = ctx.invoke_spec(node.source.visit(self), CallSpec.iter)

        val = null
        while 1:
            try:
                item = ctx.invoke_spec(src, CallSpec.next)
            except SafulateBreakoutError as e:
                e.check()
                break

            try:
                with self.scope() as env:
                    env.declare(node.var_name)
                    env[node.var_name] = item
                    val = node.body.visit(self)
            except SafulateInvalidContinue as e:
                for _ in range(e.amount):
                    try:
                        item = ctx.invoke_spec(src, CallSpec.next)
                    except SafulateBreakoutError as e:
                        e.check()
                        break
            except SafulateBreakoutError as e:
                e.check()
                break

        return val

    def visit_return(self, node: ASTReturn) -> SafBaseObject:
        if node.expr:
            value = node.expr.visit(self)
            raise SafulateInvalidReturn(value, node.keyword)

        raise SafulateInvalidReturn(null, node.keyword)

    def _visit_continue_and_break(self, node: ASTBreak | ASTContinue) -> SafBaseObject:
        is_break = isinstance(node, ASTBreak)

        with ErrorManager(token=node.keyword):
            if node.amount is None:
                amount = 1
            else:
                amount_node = node.amount.visit(self)
                if not isinstance(amount_node, SafNum):
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
                raise SafulateBreakoutError(amount, node.keyword)
            raise SafulateInvalidContinue(amount, node.keyword)

    def visit_break(self, node: ASTBreak) -> SafBaseObject:
        return self._visit_continue_and_break(node)

    def visit_continue(self, node: ASTContinue) -> SafBaseObject:
        return self._visit_continue_and_break(node)

    def visit_expr_stmt(self, node: ASTExprStmt) -> SafBaseObject:
        value = node.expr.visit(self)
        return value

    def visit_var_decl(
        self,
        node: ASTVarDecl,
    ) -> SafBaseObject:
        value = null if node.value is None else node.value.visit(self)
        return self._var_decl(node.name, value, scope=node.keyword)

    def _var_decl(
        self, name: Token, value: SafBaseObject, *, scope: Token
    ) -> SafBaseObject:
        match scope:
            case Token(type=TokenType.PUB):
                self.env.declare(name)
                self.env[name] = value
            case Token(type=TokenType.PRIV):
                if self.env.scope is None:
                    raise SafulateScopeError(
                        "Private vars can only be set while scoped", scope
                    )
                self.env.scope.private_attrs[name.lexme] = value
            case Token(lexme=SoftKeyword.SPEC.value):
                if self.env.scope is None:
                    raise SafulateScopeError(
                        "specs can only be set while scoped", scope
                    )

                try:
                    spec = spec_name_from_str(name.lexme)
                except ValueError:
                    raise SafulateValueError(
                        f"there is no spec named {name.lexme!r}", name
                    ) from None

                self.env.scope.specs[spec] = value
            case _:
                raise RuntimeError(f"Unknown var decl keyword: {scope!r}")
        return value

    def visit_func_decl(self, node: ASTFuncDecl) -> SafBaseObject:
        return SafFunc(
            name=node.name,
            params=node.params,  # pyright: ignore[reportArgumentType]
            body=node.body,
            parent=self.env.scope,
        )

    def visit_assign(self, node: ASTAssign) -> SafBaseObject:
        value = node.value.visit(self)
        self.env[node.name] = value
        return value

    def visit_binary(self, node: ASTBinary) -> SafBaseObject:
        left = node.left.visit(self)
        right = node.right.visit(self)
        ctx = self.ctx(node.op)

        try:
            spec = BinarySpec(node.op.type)
        except ValueError as e:
            match node.op.type:
                case TokenType.OR:
                    if left.bool_spec(ctx):
                        return left
                    if right.bool_spec(ctx):
                        return right
                    return null
                case TokenType.AND:
                    return (
                        true if left.bool_spec(ctx) and right.bool_spec(ctx) else false
                    )
                case TokenType.EQEQEQ:
                    return true if id(left) == id(right) else false
                case _:
                    raise ValueError(
                        f"Invalid token type {node.op.type.name} for binary operator"
                    ) from e

        with ErrorManager(token=node.op):
            return ctx.invoke_spec(left, spec, right)

    def visit_unary(self, node: ASTUnary) -> SafBaseObject:
        right = node.right.visit(self)
        ctx = self.ctx(node.op)

        with ErrorManager(token=node.op):
            try:
                spec = UnarySpec(node.op.type)
            except ValueError as e:
                if node.op.type is TokenType.NOT:
                    return false if right.bool_spec(ctx) else true
                else:
                    raise ValueError(
                        f"Invalid token type {node.op.type.name} for unary operator"
                    ) from e

            return self.ctx(node.op).invoke_spec(right, spec)

    def visit_call(self, node: ASTCall) -> SafBaseObject:
        ctx = self.ctx(node.paren)
        args: list[SafBaseObject] = []
        kwargs: dict[str, SafBaseObject] = {}

        for param_type, name, value in node.params:
            match param_type:
                case ParamType.arg:
                    args.append(value.visit(self))
                case ParamType.kwarg if name:
                    kwargs[name] = value.visit(self)
                case ParamType.kwarg:
                    raise RuntimeError(
                        f"Kwarg without name: {param_type}, {name}, {value}"
                    )
                case ParamType.vararg:
                    args.extend(value.visit(self).iter_spec(ctx))
                case ParamType.varkwarg:
                    val = value.visit(self)
                    if not isinstance(val, SafDict):
                        raise SafulateValueError(
                            f"Can not unpack, {val.repr_spec(ctx)} is not a dictionary"
                        )
                    kwargs.update(
                        {key.str_spec(ctx): value for key, value in val.data.values()}
                    )
                case _:
                    raise RuntimeError(
                        f"Unhandled param: {param_type}, {name}, {value}"
                    )

        return self.ctx(node.paren).invoke_spec(
            node.callee.visit(self),
            CallSpec(node.paren.type),
            *args,
            **kwargs,
        )

    def visit_atom(self, node: ASTAtom) -> SafBaseObject:
        match node.token.type:
            case TokenType.NUM:
                return SafNum(float(node.token.lexme))
            case TokenType.STR:
                return SafStr(node.token.lexme)
            case TokenType.ID:
                return self.env[node.token]
            case TokenType.TYPE:
                return SafType.base_type()
            case TokenType.ELLIPSIS:
                return SafEllipsis()
            case _:
                raise ValueError(f"Invalid atom type {node.token.type.name}")

    def visit_version_req(self, node: ASTVersionReq) -> SafBaseObject:
        with ErrorManager(token=node.keyword):
            match (node.left, node.op, node.right):
                case (_PackagingVersion() as ver, None, None):
                    left = str(ver)
                    right = str(self.version)
                    if len(left) < len(right):
                        left, right = right, left
                    if not left.startswith(right):
                        raise SafulateVersionConflict(
                            f"Current version (v{self.version}) is not equal to the required version (v{ver})"
                        )
                case (_PackagingVersion() as left, Token(type=TokenType.MINUS), None):
                    if self.version > left:
                        raise SafulateVersionConflict(
                            f"Current version (v{self.version}) is above the maximum set version allowed (v{left})"
                        )
                case (_PackagingVersion() as left, Token(type=TokenType.PLUS), None):
                    if self.version < left:
                        raise SafulateVersionConflict(
                            f"Current version (v{self.version}) is below the minimum set version allowed (v{left})"
                        )
                case (
                    _PackagingVersion() as left,
                    Token(TokenType.MINUS),
                    _PackagingVersion() as right,
                ):
                    if not (left < self.version < right):
                        raise SafulateVersionConflict(
                            f"Current version (v{self.version}) outside of the allowed range (v{left}-v{right})"
                        )
                case _ as x:
                    raise RuntimeError(f"Unknown version req combination: {x!r}")
            return null  # pyright: ignore[reportPossiblyUnboundVariable] # pyright is high

    def visit_import_req(self, node: ASTImportReq) -> SafBaseObject:
        with ErrorManager(token=node.source):
            value = self.libs[node.source.lexme]

            if value is None:
                match node.source.type:
                    case TokenType.ID:
                        value = self.libs.load_builtin_lib(
                            node.source.lexme, ctx=self.ctx(node.source)
                        )
                    case TokenType.STR:
                        raise SafulateImportError("Url imports are not allowed yet")
                    case other:
                        raise RuntimeError(f"Unknown import source: {other.name!r}")

            self.env.declare(node.name)
            self.env[node.name] = value
            return value

    def visit_raise(self, node: ASTRaise) -> SafBaseObject:
        val = node.expr.visit(self)
        raise SafulateError(val.repr_spec(self.ctx(node.kw)), token=node.kw, obj=val)

    def visit_del(self, node: ASTDel) -> SafBaseObject:
        del self.env.values[node.var.lexme]
        return null

    def visit_try_catch(self, node: ASTTryCatch) -> SafBaseObject:
        try:
            node.body.visit(self)
        except SafulateError as e:
            if not node.catch_branches:
                return null

            for branch in node.catch_branches:
                if branch.target is not None:
                    target_token = branch.target[0]
                    target = branch.target[1].visit(self)

                    if not isinstance(target, SafType):
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
    ) -> SafBaseObject:
        try:
            return body.visit(self)
        except SafulateInvalidContinue as e:
            next_loop = e.handle_skips(loops)

            if next_loop is None:
                return null
            return self._visit_switch_case_entry(next_loop[-1], loops)

    def visit_switch_case(self, node: ASTSwitchCase) -> SafBaseObject:
        key = node.expr.visit(self)
        cases = node.cases.copy()

        while cases:
            expr, body = cases.pop(0)
            ctx = self.ctx(node.kw)

            res = ctx.invoke_spec(key, BinarySpec.eq, expr.visit(self))
            if not res.bool_spec(ctx):
                continue

            self._visit_switch_case_entry(body, cases)
            return null

        if node.else_branch:
            node.else_branch.visit(self)
        return null

    def visit_list(self, node: ASTList) -> SafList:
        return SafList([child.visit(self) for child in node.children])

    def visit_format(self, node: ASTFormat) -> SafBaseObject:
        args: tuple[SafBaseObject, ...] = ()

        try:
            spec = FormatSpec(node.spec.lexme)
        except ValueError:
            args = (SafStr(node.spec.lexme),)
            spec = CallSpec.format

        return self.ctx(node.spec).invoke_spec(node.obj.visit(self), spec, *args)

    def visit_property(self, node: ASTProperty) -> SafBaseObject:
        return self._var_decl(
            name=node.name,
            value=SafProperty(
                SafFunc(
                    name=node.name, params=[], body=node.body, parent=self.env.scope
                )
            ),
            scope=node.kw_token.with_type(TokenType.PUB),
        )

    def visit_regex(self, node: ASTRegex) -> SafBaseObject:
        return self.regex_pattern_cls(re.compile(node.value.lexme[2:-1]))

    def visit_type_decl(self, node: ASTTypeDecl) -> SafBaseObject:
        obj = SafType(
            node.name.lexme,
            init=node.init.visit(self) if node.init else None,
            arity=node.arity,
        )
        obj.set_parent(self.env.scope)

        with self.scope(obj):
            if node.body:
                self.visit_unscoped_block(node.body)
            if node.compare_func:
                self.env["check"] = node.compare_func.visit(self)

        return obj

    def _get_scope_parent(self, levels: list[Token]) -> SafBaseObject:
        scope: SafBaseObject | None = self.env.scope

        for level in levels[1:]:
            if not scope:
                raise SafulateScopeError("Can't go any futher", level)

            scope = scope.parent

        if not scope:
            raise SafulateScopeError("Can't go any futher", levels[-1])

        return scope

    def visit_get_par(self, node: ASTPar) -> SafBaseObject:
        return self._get_scope_parent(node.levels)

    def visit_get_priv(self, node: ASTGetPriv) -> SafBaseObject:
        scope = self._get_scope_parent(node.levels)
        val = scope.private_attrs.get(node.name.lexme)

        if val is None:
            raise SafulateAttributeError(
                f"Private Var Not Found: {node.name.lexme!r}",
                node.name,
            )
        return val
