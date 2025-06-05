from __future__ import annotations

import re
from contextlib import contextmanager
from typing import TYPE_CHECKING

from packaging.version import Version as _PackagingVersion

from .._version import __version__
from ..errors import (
    SafulateAttributeError,
    SafulateBreakoutError,
    SafulateError,
    SafulateImportError,
    SafulateInvalidContinue,
    SafulateInvalidReturn,
    SafulateNameError,
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
    ASTDynamicID,
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
    SafObject,
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
    __slots__ = (
        "__cs_builtins__",
        "__cs_regex_pattern_cls__",
        "env_stack",
        "libs",
        "module_obj",
        "version",
    )

    def __init__(self, name: str, *, lib_manager: LibManager | None = None) -> None:
        self.version = _PackagingVersion(__version__)
        self.libs = lib_manager or LibManager()
        self.module_obj = SafModule(name)
        self.env_stack: list[SafBaseObject] = [self.module_obj]

    @property
    def env(self) -> SafBaseObject:
        return self.env_stack[0]

    @property
    def name(self) -> str:
        return self.module_obj.name

    @cached_property("regex_pattern_cls")
    def regex_pattern_cls(self) -> type[_SafPattern]:
        from .libs.regex import SafPattern

        return SafPattern

    @cached_property("__cs_builtins__")
    def _builtins(self) -> dict[str, SafBaseObject]:
        from .libs.builtins import Builtins

        return Builtins().public_attrs

    def ctx(self, token: Token) -> NativeContext:
        return NativeContext(self, token)

    @contextmanager
    def scope(self, new: SafBaseObject | None = None) -> Iterator[SafBaseObject]:
        if new is None:
            new = SafObject("temp scope")
            new.set_parent(self.env)

        self.env_stack.insert(0, new)
        yield new
        assert self.env_stack.pop(0) == new

    def visit_program(self, node: ASTProgram | ASTBlock) -> SafBaseObject:
        if len(node.stmts) <= 0:
            return null
        for stmt in node.stmts[:-1]:
            stmt.visit(self)

        return node.stmts[-1].visit(self)

    def visit_block(self, node: ASTBlock) -> SafBaseObject:
        with self.scope():
            return self.visit_program(node)

    def visit_edit_object(self, node: ASTEditObject) -> SafBaseObject:
        src = node.obj.visit(self)
        with self.scope(src):
            self.visit_program(node.block)
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
                self._var_decl(node.var_name.lexme, item, scope=None, declare=True)
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

        if node.amount is None:
            amount = 1
        else:
            amount_node = node.amount.visit(self)
            if not isinstance(amount_node, SafNum):
                raise SafulateTypeError(
                    f"Expected a number for {'break' if is_break else 'continue'} amount, got {amount_node.repr_spec(self.ctx(node.keyword))} instead.",
                    node.keyword,
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
            raise SafulateValueError(msg, node.keyword)

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
        return self._var_decl(
            node.name.lexme
            if isinstance(node.name, Token)
            else node.name.resolve(self),
            null if node.value is None else node.value.visit(self),
            scope=node.keyword,
            declare=True,
        )

    def _var_decl(
        self,
        name: str,
        value: SafBaseObject,
        *,
        scope: Token | None,
        declare: bool = False,
    ) -> SafBaseObject:
        match scope:
            case Token(type=TokenType.PUB) | None:
                for env in self.env_stack:
                    if declare or name in env.public_attrs:
                        env.public_attrs[name] = value
                        break
                else:
                    if name in self._builtins:
                        self._builtins[name] = value
                    else:
                        raise SafulateNameError(f"Name {name!r} is not defined", scope)

            case Token(type=TokenType.PRIV):
                self.env.private_attrs[name] = value
            case Token(lexme=SoftKeyword.SPEC.value):
                try:
                    spec = spec_name_from_str(name)
                except ValueError:
                    raise SafulateValueError(
                        f"there is no spec named {name!r}", scope
                    ) from None

                self.env.specs[spec] = value
            case _:
                raise RuntimeError(f"Unknown var decl keyword: {scope!r}")
        return value

    def visit_func_decl(self, node: ASTFuncDecl) -> SafBaseObject:
        return SafFunc(
            name=None
            if node.name is None
            else (
                node.name.lexme
                if isinstance(node.name, Token)
                else node.name.resolve(self)
            ),
            params=node.params,
            body=node.body,
            parent=self.env,
        )

    def visit_assign(self, node: ASTAssign) -> SafBaseObject:
        value = node.value.visit(self)
        self._var_decl(node.name.lexme, value, scope=None)
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

        return ctx.invoke_spec(left, spec, right)

    def visit_unary(self, node: ASTUnary) -> SafBaseObject:
        right = node.right.visit(self)
        ctx = self.ctx(node.op)

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

    def _get_var(self, name: str, token: Token) -> SafBaseObject:
        for env in self.env_stack:
            if name in env.public_attrs:
                return env.public_attrs[name]

        if name in self._builtins:
            return self._builtins[name]
        else:
            raise SafulateNameError(f"Name {name!r} is not defined", token)

    def visit_atom(self, node: ASTAtom) -> SafBaseObject:
        match node.token.type:
            case TokenType.NUM:
                return SafNum(float(node.token.lexme))
            case TokenType.STR:
                return SafStr(node.token.lexme)
            case TokenType.ID:
                return self._get_var(node.token.lexme, node.token)
            case TokenType.TYPE:
                return SafType.base_type()
            case TokenType.ELLIPSIS:
                return SafEllipsis()
            case _:
                raise ValueError(f"Invalid atom type {node.token.type.name}")

    def visit_version_req(self, node: ASTVersionReq) -> SafBaseObject:
        match (node.left, node.op, node.right):
            case (_PackagingVersion() as ver, None, None):
                left = str(ver)
                right = str(self.version)
                if len(left) < len(right):
                    left, right = right, left
                if not left.startswith(right):
                    raise SafulateVersionConflict(
                        f"Current version (v{self.version}) is not equal to the required version (v{ver})",
                        node.keyword,
                    )
            case (_PackagingVersion() as left, Token(type=TokenType.MINUS), None):
                if self.version > left:
                    raise SafulateVersionConflict(
                        f"Current version (v{self.version}) is above the maximum set version allowed (v{left})",
                        node.keyword,
                    )
            case (_PackagingVersion() as left, Token(type=TokenType.PLUS), None):
                if self.version < left:
                    raise SafulateVersionConflict(
                        f"Current version (v{self.version}) is below the minimum set version allowed (v{left})",
                        node.keyword,
                    )
            case (
                _PackagingVersion() as left,
                Token(TokenType.MINUS),
                _PackagingVersion() as right,
            ):
                if not (left < self.version < right):
                    raise SafulateVersionConflict(
                        f"Current version (v{self.version}) outside of the allowed range (v{left}-v{right})",
                        node.keyword,
                    )
            case _ as x:
                raise RuntimeError(f"Unknown version req combination: {x!r}")

        return null

    def visit_import_req(self, node: ASTImportReq) -> SafBaseObject:
        value = self.libs[node.source.lexme]

        if value is None:
            match node.source.type:
                case TokenType.ID:
                    value = self.libs.load_builtin_lib(
                        node.source.lexme, ctx=self.ctx(node.source)
                    )
                case TokenType.STR:
                    raise SafulateImportError(
                        "Url imports are not allowed yet", node.source
                    )
                case other:
                    raise RuntimeError(f"Unknown import source: {other.name!r}")

        self._var_decl(node.name.lexme, value, scope=None, declare=True)
        return value

    def visit_raise(self, node: ASTRaise) -> SafBaseObject:
        val = node.expr.visit(self)
        raise SafulateError(val.repr_spec(self.ctx(node.kw)), token=node.kw, obj=val)

    def visit_del(self, node: ASTDel) -> SafBaseObject:
        for parent in self.env.walk_parents(include_self=True):
            if node.var.lexme in parent.public_attrs:
                return parent.public_attrs.pop(node.var.lexme)
        if node.var.lexme in self._builtins:
            return self._builtins.pop(node.var.lexme)

        raise SafulateNameError(f"Name {node.var.lexme!r} is not defined")

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

                with self.scope():
                    if branch.var:
                        self._var_decl(
                            branch.var.lexme, e.saf_value, scope=None, declare=True
                        )

                    return self.visit_program(branch.body)
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
            next_loop = None

            while e.amount != 0:
                try:
                    next_loop = loops.pop(0)
                except IndexError:
                    return null
                e.amount -= 1

            if next_loop is None:
                return null

            loops.insert(0, next_loop)
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

    def visit_regex(self, node: ASTRegex) -> SafBaseObject:
        return self.regex_pattern_cls(re.compile(node.value.lexme[2:-1]))

    def visit_type_decl(self, node: ASTTypeDecl) -> SafBaseObject:
        obj = SafType(
            node.name.lexme
            if isinstance(node.name, Token)
            else node.name.resolve(self),
            init=node.init.visit(self) if node.init else None,
            arity=node.arity,
        )
        obj.set_parent(self.env)

        with self.scope(obj):
            if node.body:
                self.visit_program(node.body)
            if node.compare_func:
                self.env["check"] = node.compare_func.visit(self)

        return obj

    def _get_scope_parent(self, levels: list[Token]) -> SafBaseObject:
        _levels = levels.copy()
        assert self.env

        for scope in self.env.walk_parents(include_self=True):
            if _levels:
                _levels.pop(0)

            if not _levels:
                return scope

        raise SafulateScopeError("Can't go any futher", levels[-1])

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

    def visit_dynamic_id(self, node: ASTDynamicID) -> SafBaseObject:
        return self._get_var(node.resolve(self), node.token)

    def resolve_dynamic_id(self, node: ASTDynamicID) -> str:
        return (
            node.token.lexme
            if node.expr is None
            else node.expr.visit(self).str_spec(self.ctx(node.token))
        )
