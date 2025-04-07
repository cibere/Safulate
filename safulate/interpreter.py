from __future__ import annotations

import runpy
from contextlib import contextmanager
from pathlib import Path
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
    ASTDel,
    ASTExprStmt,
    ASTForLoop,
    ASTFuncDecl,
    ASTIf,
    ASTImportReq,
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
    ASTVisitor,
    ASTWhile,
)
from .environment import Environment
from .errors import (
    ErrorManager,
    SafulateBreakoutError,
    SafulateError,
    SafulateImportError,
    SafulateInvalidReturn,
    SafulateTypeError,
    SafulateValueError,
    SafulateVersionConflict,
)
from .exporter import Exporter
from .native_context import NativeContext
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

__all__ = ("TreeWalker",)

libs_path = Path(__file__).parent / "libs"


class TreeWalker(ASTVisitor):
    __slots__ = ("env", "import_cache")

    def __init__(self, *, env: Environment | None = None) -> None:
        self.version = Version("v0.0.1")
        self.import_cache: dict[str, ObjectValue] = {}

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

    def visit_scoped_block(self, node: ASTScopedBlock) -> Value:
        src = node.source.accept(self)
        with self.scope(source=src):
            return self._visit_block_unscoped(node.block)

    def visit_if(self, node: ASTIf) -> Value:
        if node.condition.accept(self).truthy():
            node.body.accept(self)
        elif node.else_branch:
            node.else_branch.accept(self)

        return NullValue()

    def visit_while(self, node: ASTWhile) -> Value:
        while node.condition.accept(self).truthy():
            try:
                node.body.accept(self)
            except SafulateBreakoutError as e:
                e.amount -= 1
                if e.amount != 0:
                    raise e
                break

        return NullValue()

    def visit_for_loop(self, node: ASTForLoop) -> Value:
        src = node.source.accept(self)
        if not isinstance(src, ListValue):
            func = src.specs["iter"]

            with ErrorManager(token=node.var_name):
                src = func.call(NativeContext(self, node.var_name))
                if not isinstance(src, ListValue):
                    raise SafulateValueError(f"{src!r} is not iterable")

        for item in src.value:
            with self.scope() as env:
                env.declare(node.var_name)
                env[node.var_name] = item
                node.body.accept(self)

        return NullValue()

    def visit_return(self, node: ASTReturn) -> Value:
        if node.expr:
            value = node.expr.accept(self)
            raise SafulateInvalidReturn(value, node.keyword)

        raise SafulateInvalidReturn(NullValue(), node.keyword)

    def visit_break(self, node: ASTBreak) -> Value:
        with ErrorManager(token=node.keyword):
            if node.amount is None:
                amount = 1
            else:
                amount_node = node.amount.accept(self)
                if not isinstance(amount_node, NumValue):
                    raise SafulateTypeError(
                        f"Expected a number for break amount, got {amount_node!r} instead.",
                    )
                amount = int(amount_node.value)

            if amount == 0:
                return NullValue()
            elif amount < 0:
                raise SafulateValueError(
                    "You can't breakout of a negative number of loops"
                )

            raise SafulateBreakoutError(amount)

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
            TokenType.CONTAINS: "contains",
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
        return callee.call(
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
            case TokenType.NULL:
                return NullValue()
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
                    path = libs_path / f"{node.source.lexeme}.py"
                    if path.exists():
                        globals = runpy.run_path(str(path.absolute()))
                        exporter = globals.get("exporter")
                        if exporter is None:
                            raise SafulateImportError(
                                "Module does not have an exporter"
                            )
                        if not isinstance(exporter, Exporter):
                            raise RuntimeError("Module does not have a valid exporter")
                        value = exporter.to_container()
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
