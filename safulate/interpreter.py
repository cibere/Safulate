from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from packaging.version import Version

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
    SafulateBreakoutError,
    SafulateError,
    SafulateImportError,
    SafulateInvalidContinue,
    SafulateInvalidReturn,
    SafulateTypeError,
    SafulateValueError,
    SafulateVersionConflict,
)
from .native_context import NativeContext
from .py_libs import LibManager
from .tokens import TokenType
from .values import (
    FuncValue,
    ListValue,
    NativeFunc,
    NullValue,
    NumValue,
    ObjectValue,
    StrValue,
    Value,
    VersionConstraintValue,
    VersionValue,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

__version__ = "v0.1.0"

__all__ = ("TreeWalker", "__version__")


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

    @contextmanager
    def scope(self, source: Value | None = None) -> Iterator[Environment]:
        old_env = self.env
        self.env = Environment(self.env, scope=source)
        yield self.env
        self.env = old_env

    def visit_program(self, node: ASTProgram) -> Value:
        if len(node.stmts) <= 0:
            return NullValue()
        for stmt in node.stmts[:-1]:
            stmt.accept(self)

        return node.stmts[-1].accept(self)

    def _visit_block_unscoped(self, node: ASTBlock) -> Value:
        if len(node.stmts) <= 0:
            return NullValue()

        for stmt in node.stmts[:-1]:
            stmt.accept(self)
        res = node.stmts[-1].accept(self)

        return res

    def visit_block(self, node: ASTBlock) -> Value:
        with self.scope():
            return self._visit_block_unscoped(node)

    def visit_edit_object(self, node: ASTEditObject) -> Value:
        src = node.obj.accept(self)
        with self.scope(source=src):
            self._visit_block_unscoped(node.block)
        return src

    def visit_if(self, node: ASTIf) -> Value:
        if node.condition.accept(self).truthy():
            return node.body.accept(self)
        elif node.else_branch:
            return node.else_branch.accept(self)
        return NullValue()

    def visit_while(self, node: ASTWhile) -> Value:
        val = NullValue()

        while node.condition.accept(self).truthy():
            try:
                val = node.body.accept(self)
            except SafulateBreakoutError as e:
                e.check()
                break
            except SafulateInvalidContinue:
                pass

        return val

    def visit_for_loop(self, node: ASTForLoop) -> Value:
        src = node.source.accept(self)
        if not isinstance(src, ListValue):
            func = src.specs["iter"]

            with ErrorManager(token=node.var_name):
                src = func.call(NativeContext(self, node.var_name))
                if not isinstance(src, ListValue):
                    raise SafulateValueError(f"{src!r} is not iterable")

        loops = src.value.copy()
        val = NullValue()
        while loops:
            item = loops.pop(0)

            try:
                with self.scope() as env:
                    env.declare(node.var_name)
                    env[node.var_name] = item
                    val = node.body.accept(self)
            except SafulateInvalidContinue as e:
                e.handle_skips(loops)
            except SafulateBreakoutError as e:
                e.check()
                break

        return val

    def visit_return(self, node: ASTReturn) -> Value:
        if node.expr:
            value = node.expr.accept(self)
            raise SafulateInvalidReturn(value, node.keyword)

        raise SafulateInvalidReturn(NullValue(), node.keyword)

    def _visit_continue_and_break(self, node: ASTBreak | ASTContinue) -> Value:
        is_break = isinstance(node, ASTBreak)

        with ErrorManager(token=node.keyword):
            if node.amount is None:
                amount = 1
            else:
                amount_node = node.amount.accept(self)
                if not isinstance(amount_node, NumValue):
                    raise SafulateTypeError(
                        f"Expected a number for {'break' if is_break else 'continue'} amount, got {amount_node!r} instead.",
                    )
                amount = int(amount_node.value)

            if amount == 0:
                return NullValue()
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
        value = node.expr.accept(self)
        return value

    def _declare_var(self, node: ASTVarDecl | ASTPrivDecl) -> Value:
        self.env.declare(node.name)
        value = NullValue() if node.value is None else node.value.accept(self)
        self.env[node.name] = value
        return value

    def visit_var_decl(self, node: ASTVarDecl) -> Value:
        return self._declare_var(node)

    def visit_priv_decl(self, node: ASTPrivDecl) -> Value:
        node.name.lexeme = f"${node.name.lexeme}"
        return self._declare_var(node)

    def _declare_func(self, node: ASTFuncDecl | ASTSpecDecl) -> Value:
        self.env.declare(node.name)
        self.env[node.name] = value = FuncValue(node.name, node.params, node.body)
        return value

    def visit_func_decl(self, node: ASTFuncDecl) -> Value:
        return self._declare_func(node)

    def visit_spec_decl(self, node: ASTSpecDecl) -> Value:
        node.name.lexeme = f"%{node.name.lexeme}"
        return self._declare_func(node)

    def visit_assign(self, node: ASTAssign) -> Value:
        value = node.value.accept(self)
        self.env[node.name] = value
        return value

    def visit_binary(self, node: ASTBinary) -> Value:
        left = node.left.accept(self)
        right = node.right.accept(self)

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
            TokenType.AND: "and",
            TokenType.OR: "or",
            TokenType.HAS: "has_item",
        }.get(node.op.type)

        if spec_name is None:
            raise ValueError(
                f"Invalid token type {node.op.type.name} for binary operator"
            )

        with ErrorManager(token=node.op):
            func = left.specs[spec_name]
            return func.call(NativeContext(self, node.op), right)

    def visit_unary(self, node: ASTUnary) -> Value:
        right = node.right.accept(self)

        spec_name = {
            TokenType.PLUS: "uadd",
            TokenType.MINUS: "neg",
            TokenType.NOT: "not",
        }.get(node.op.type, None)
        if spec_name is None:
            raise ValueError(
                f"Invalid token type {node.op.type.name} for unary operator"
            )

        with ErrorManager(token=node.op):
            func = right.specs[spec_name]
            assert isinstance(func, NativeFunc)
            return func.call(NativeContext(self, node.op))

    def visit_call(self, node: ASTCall) -> Value:
        callee = node.callee.accept(self)
        func_name = {TokenType.LPAR: "call", TokenType.LSQB: "subscript"}[
            node.paren.type
        ]

        func = callee.specs[func_name]
        return func.call(
            NativeContext(self, node.paren), *[arg.accept(self) for arg in node.args]
        )

    def visit_atom(self, node: ASTAtom) -> Value:
        match node.token.type:
            case TokenType.NUM:
                return NumValue(node.token.value)
            case TokenType.STR:
                return StrValue(node.token.value)
            case TokenType.ID:
                return self.env[node.token]
            case _:
                raise ValueError(f"Invalid atom type {node.token.type.name}")

    def visit_attr(self, node: ASTAttr) -> Value:
        obj = node.expr.accept(self)

        with ErrorManager(token=node.attr):
            if node.attr.type is not TokenType.ID:
                raise ValueError(
                    f"Invalid token type {node.attr.type.name} for attribute access"
                )

            return obj[node.attr.lexeme]

    def visit_version(self, node: ASTVersion) -> VersionValue:
        major = NumValue(node.major)
        minor = NullValue() if node.minor is None else NumValue(node.minor)
        micro = NullValue() if node.micro is None else NumValue(node.micro)

        return VersionValue(major=major, minor=minor, micro=micro)

    def visit_version_req(self, node: ASTVersionReq) -> Value:
        with ErrorManager(token=node.token):
            match node.version.accept(self):
                case VersionValue() as ver_value:
                    ver = Version(str(ver_value))
                    if ver != self.version:
                        raise SafulateVersionConflict(
                            f"Current version (v{self.version}) is not equal to the required version (v{ver})"
                        )
                case VersionConstraintValue(constraint="-", left=NullValue()) as const:
                    ver = Version(str(const.right))

                    if self.version > ver:
                        raise SafulateVersionConflict(
                            f"Current version (v{self.version}) is above the maximum set version allowed (v{ver})"
                        )
                case VersionConstraintValue(constraint="+", left=NullValue()) as const:
                    ver = Version(str(const.right))

                    if self.version < ver:
                        raise SafulateVersionConflict(
                            f"Current version (v{self.version}) is below the minimum set version allowed (v{ver})"
                        )
                case VersionConstraintValue(constraint="-") as const:
                    left_ver = Version(str(const.left))
                    right_ver = Version(str(const.right))

                    if not (left_ver < self.version < right_ver):
                        raise SafulateVersionConflict(
                            f"Current version (v{self.version}) outside of the allowed range ({const})"
                        )
                case _ as x:
                    raise RuntimeError(f"Unknown version req combination: {x!r}")
            return NullValue()

    def visit_import_req(self, node: ASTImportReq) -> Value:
        cached_value = self.import_cache.get(node.source.lexeme)
        if cached_value:
            return cached_value

        with ErrorManager(token=node.source):
            value = None

            match node.source.type:
                case TokenType.ID:
                    value = self.libs[node.source.lexeme]
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
            self.import_cache[node.name.lexeme] = value
            return value

    def visit_raise(self, node: ASTRaise) -> Value:
        raise SafulateError(node.expr.accept(self), node.kw)

    def visit_del(self, node: ASTDel) -> Value:
        del self.env.values[node.var.lexeme]
        return NullValue()

    def visit_try_catch(self, node: ASTTryCatch) -> Value:
        try:
            node.body.accept(self)
        except SafulateError as e:
            if node.catch_branch is None:
                return NullValue()

            with self.scope() as env:
                if node.error_var:
                    env.declare(node.error_var)
                    env[node.error_var] = e.obj

                return self._visit_block_unscoped(node.catch_branch)

        if node.else_branch is None:
            return NullValue()

        return node.else_branch.accept(self)

    def _visit_switch_case_entry(
        self, body: ASTBlock, loops: list[tuple[ASTNode, ASTBlock]]
    ) -> Value:
        try:
            return body.accept(self)
        except SafulateInvalidContinue as e:
            next_loop = e.handle_skips(loops)

            if next_loop is None:
                return NullValue()
            return self._visit_switch_case_entry(next_loop[-1], loops)

    def visit_switch_case(self, node: ASTSwitchCase) -> Value:
        key = node.expr.accept(self)
        cases = node.cases.copy()

        while cases:
            expr, body = cases.pop(0)

            res = key.specs["eq"].call(NativeContext(self, node.kw), expr.accept(self))
            if not res.bool_spec():
                continue

            self._visit_switch_case_entry(body, cases)
            return NullValue()

        if node.else_branch:
            node.else_branch.accept(self)
        return NullValue()

    def visit_list(self, node: ASTList) -> ListValue:
        return ListValue([child.accept(self) for child in node.children])
