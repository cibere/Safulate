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
    ParamType,
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
    SafDict,
    SafFunc,
    SafList,
    SafNum,
    SafObject,
    SafPattern,
    SafProperty,
    SafStr,
    SafType,
    SafBaseObject,
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
        self.import_cache: dict[str, SafObject] = {}

        self.libs = lib_manager or LibManager()

        if env:
            self.env = env
        else:
            self.env = Environment().add_builtins()

    def ctx(self, token: Token) -> NativeContext:
        return NativeContext(self, token)

    @contextmanager
    def scope(self, source: SafBaseObject | None = None) -> Iterator[Environment]:
        old_env = self.env
        self.env = Environment(self.env, scope=source)
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
        src = node.source.visit(self)
        if not isinstance(src, SafList):
            with ErrorManager(token=node.var_name):
                src = self.ctx(node.var_name).invoke_spec(src, "iter")
                if not isinstance(src, SafList):
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
                raise SafulateBreakoutError(amount)
            raise SafulateInvalidContinue(amount)

    def visit_break(self, node: ASTBreak) -> SafBaseObject:
        return self._visit_continue_and_break(node)

    def visit_continue(self, node: ASTContinue) -> SafBaseObject:
        return self._visit_continue_and_break(node)

    def visit_expr_stmt(self, node: ASTExprStmt) -> SafBaseObject:
        value = node.expr.visit(self)
        return value

    def visit_var_decl(self, node: ASTVarDecl) -> SafBaseObject:
        value = null if node.value is None else node.value.visit(self)
        match node.keyword.type:
            case TokenType.PUB:
                self.env.declare(node.name)
                self.env[node.name] = value
            case TokenType.PRIV:
                self.env.set_priv(node.name, value)
            case _:
                raise RuntimeError(f"Unknown var decl keyword: {node.keyword.type!r}")
        return value

    def visit_func_decl(self, node: ASTFuncDecl) -> SafBaseObject:
        value = SafFunc(
            name=node.name,
            params=node.params,  # pyright: ignore[reportArgumentType]
            body=node.body,
            extra_vars=self.env.values.copy(),
        )
        self.env._set_parent(value)

        if node.name is None:
            return value
        elif node.scope_token is None:
            node.scope_token = Token(TokenType.PUB, "pub", node.kw_token.start)

        match node.scope_token:
            case Token(type=TokenType.PUB):
                self.env.declare(node.name)
                self.env[node.name] = value
            case Token(type=TokenType.PRIV):
                self.env.set_priv(node.name, value)
            case Token(lexme=SoftKeyword.SPEC.value):
                if self.env.scope is None:
                    raise SafulateScopeError(
                        "specs can only be set in an edit object statement",
                        node.kw_token,
                    )

                try:
                    current_spec = self.env.scope.specs[node.name.lexeme]
                    assert isinstance(current_spec, SafFunc)
                except KeyError:
                    raise SafulateValueError(
                        f"there is no spec named {node.name.lexeme!r}", node.name
                    ) from None

                # if node.name.lexeme != "call" and value.arity != current_spec.arity:
                #     raise SafulateValueError(
                #         f"number of params for {node.name.lexeme!r} spec do not compare",
                #         node.paren_token,
                #     )

                self.env.scope.specs[node.name.lexeme] = value
                return value
            case _:
                raise RuntimeError(
                    f"Unknown func decl scope keyword: {node.scope_token!r}"
                )
        return value

    def visit_assign(self, node: ASTAssign) -> SafBaseObject:
        value = node.value.visit(self)
        self.env[node.name] = value
        return value

    def visit_binary(self, node: ASTBinary) -> SafBaseObject:
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
                    return SafNum(
                        1 if left.bool_spec(ctx) and right.bool_spec(ctx) else 0
                    )
                case _:
                    raise ValueError(
                        f"Invalid token type {node.op.type.name} for binary operator"
                    )

        with ErrorManager(token=node.op):
            return ctx.invoke_spec(left, spec_name, right)

    def visit_unary(self, node: ASTUnary) -> SafBaseObject:
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

    def visit_call(self, node: ASTCall) -> SafBaseObject:
        func = node.callee.visit(self)
        ctx = self.ctx(node.paren)

        if node.paren.type is TokenType.LSQB:
            func = func.specs["altcall"]

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
                    val = ctx.invoke_spec(value.visit(self), "iter")
                    if not isinstance(val, SafList):
                        raise SafulateValueError(
                            f"Can not unpack, {val.repr_spec(ctx)} is not iterable"
                        )
                    args.extend(val.value)
                case ParamType.varkwarg:
                    val = value.visit(self)
                    if not isinstance(val, SafDict):
                        raise SafulateValueError(
                            f"Can not unpack, {val.repr_spec(ctx)} is not a dictionary"
                        )
                    kwargs.update(val.data)
                case _:
                    raise RuntimeError(
                        f"Unhandled param: {param_type}, {name}, {value}"
                    )

        return self.ctx(node.paren).invoke(
            func,
            *args,
            **kwargs,
        )

    def visit_atom(self, node: ASTAtom) -> SafBaseObject:
        match node.token.type:
            case TokenType.NUM:
                return SafNum(float(node.token.lexeme))
            case TokenType.STR:
                return SafStr(node.token.lexeme)
            case TokenType.ID:
                return self.env[node.token]
            case TokenType.PRIV_ID:
                return self.env.get_priv(node.token)
            case _:
                raise ValueError(f"Invalid atom type {node.token.type.name}")

    def visit_attr(self, node: ASTAttr) -> SafBaseObject:
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
                obj, "get_attr", SafStr(node.attr.lexeme)
            )

    def visit_version(self, node: ASTVersion) -> SafBaseObject:
        raise RuntimeError("version not allowed")

    def visit_version_req(self, node: ASTVersionReq) -> SafBaseObject:
        raise RuntimeError("version not allowed")

    # def visit_version(self, node: ASTVersion) -> VersionValue:
    #     major = SafNum(node.major)
    #     minor = null if node.minor is None else SafNum(node.minor)
    #     micro = null if node.micro is None else SafNum(node.micro)

    #     return VersionValue(major=major, minor=minor, micro=micro)

    # def visit_version_req(self, node: ASTVersionReq) -> SafBaseObject:
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

    def visit_import_req(self, node: ASTImportReq) -> SafBaseObject:
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

    def visit_raise(self, node: ASTRaise) -> SafBaseObject:
        val = node.expr.visit(self)
        raise SafulateError(val.repr_spec(self.ctx(node.kw)), token=node.kw, obj=val)

    def visit_del(self, node: ASTDel) -> SafBaseObject:
        del self.env.values[node.var.lexeme]
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

            res = ctx.invoke_spec(key, "eq", expr.visit(self))
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
        spec = {"r": "repr", "s": "str"}.get(node.spec.lexeme)
        args: tuple[SafBaseObject, ...] = ()

        if spec is None:
            args = (SafStr(node.spec.lexeme),)
            spec = "format"

        return self.ctx(node.spec).invoke_spec(node.obj.visit(self), spec, *args)

    def visit_property(self, node: ASTProperty) -> SafBaseObject:
        val = SafProperty(SafFunc(name=node.name, params=[], body=node.body))
        self.env.declare(node.name)
        self.env[node.name] = val
        return val

    def visit_regex(self, node: ASTRegex) -> SafBaseObject:
        return SafPattern(re.compile(node.value.lexeme[2:-1]))
