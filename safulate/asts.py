from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lexer import Token
    from .values import Value

__all__ = (
    "ASTAssign",
    "ASTAtom",
    "ASTBinary",
    "ASTBlock",
    "ASTBreak",
    "ASTCall",
    "ASTExprStmt",
    "ASTFuncDecl",
    "ASTIf",
    "ASTImportReq",
    "ASTNode",
    "ASTPrivDecl",
    "ASTProgram",
    "ASTReturn",
    "ASTScopedBlock",
    "ASTSpecDecl",
    "ASTUnary",
    "ASTVarDecl",
    "ASTVersion",
    "ASTVersionReq",
    "ASTWhile",
)


class ASTNode(ABC):
    @abstractmethod
    def accept(self, visitor: ASTVisitor) -> Value: ...


@dataclass
class ASTProgram(ASTNode):
    stmts: list[ASTNode]

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_program(self)


@dataclass
class ASTVarDecl(ASTNode):
    name: Token
    value: ASTNode | None

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_var_decl(self)


@dataclass
class ASTPrivDecl(ASTNode):
    name: Token
    value: ASTNode | None

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_priv_decl(self)


@dataclass
class ASTFuncDecl(ASTNode):
    name: Token
    params: list[Token]
    body: ASTNode

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_func_decl(self)


@dataclass
class ASTSpecDecl(ASTNode):
    name: Token
    params: list[Token]
    body: ASTNode

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_spec_decl(self)


@dataclass
class ASTBlock(ASTNode):
    stmts: list[ASTNode]

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_block(self)


@dataclass
class ASTScopedBlock(ASTNode):
    source: ASTNode
    block: ASTBlock

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_scoped_block(self)


@dataclass
class ASTIf(ASTNode):
    condition: ASTNode
    body: ASTNode
    else_branch: ASTNode | None

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_if(self)


@dataclass
class ASTWhile(ASTNode):
    condition: ASTNode
    body: ASTNode

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_while(self)


@dataclass
class ASTReturn(ASTNode):
    keyword: Token
    expr: ASTNode | None

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_return(self)


@dataclass
class ASTBreak(ASTNode):
    keyword: Token
    amount: ASTNode | None

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_break(self)


@dataclass
class ASTExprStmt(ASTNode):
    expr: ASTNode

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_expr_stmt(self)


@dataclass
class ASTAssign(ASTNode):
    name: Token
    value: ASTNode

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_assign(self)


@dataclass
class ASTBinary(ASTNode):
    left: ASTNode
    op: Token
    right: ASTNode

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_binary(self)


@dataclass
class ASTUnary(ASTNode):
    op: Token
    right: ASTNode

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_unary(self)


@dataclass
class ASTCall(ASTNode):
    callee: ASTNode
    paren: Token  # Soley for error handling
    args: list[ASTNode]

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_call(self)


@dataclass
class ASTAtom(ASTNode):
    token: Token

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_atom(self)


@dataclass
class ASTAttr(ASTNode):
    expr: ASTNode
    attr: Token

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_attr(self)


@dataclass
class ASTVersion(ASTNode):
    major: float
    minor: float | None
    micro: float | None

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_version(self)


@dataclass
class ASTImportReq(ASTNode):
    source: Token
    name: Token

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_import_req(self)


@dataclass
class ASTVersionReq(ASTNode):
    version: ASTNode
    token: Token

    def accept(self, visitor: ASTVisitor) -> Value:
        return visitor.visit_version_req(self)


class ASTVisitor(ABC):
    @abstractmethod
    def visit_program(self, node: ASTProgram) -> Value: ...
    @abstractmethod
    def visit_block(self, node: ASTBlock) -> Value: ...
    @abstractmethod
    def visit_if(self, node: ASTIf) -> Value: ...
    @abstractmethod
    def visit_while(self, node: ASTWhile) -> Value: ...
    @abstractmethod
    def visit_return(self, node: ASTReturn) -> Value: ...
    @abstractmethod
    def visit_break(self, node: ASTBreak) -> Value: ...
    @abstractmethod
    def visit_expr_stmt(self, node: ASTExprStmt) -> Value: ...
    @abstractmethod
    def visit_var_decl(self, node: ASTVarDecl) -> Value: ...
    @abstractmethod
    def visit_func_decl(self, node: ASTFuncDecl) -> Value: ...
    @abstractmethod
    def visit_assign(self, node: ASTAssign) -> Value: ...
    @abstractmethod
    def visit_binary(self, node: ASTBinary) -> Value: ...
    @abstractmethod
    def visit_unary(self, node: ASTUnary) -> Value: ...
    @abstractmethod
    def visit_call(self, node: ASTCall) -> Value: ...
    @abstractmethod
    def visit_atom(self, node: ASTAtom) -> Value: ...
    @abstractmethod
    def visit_attr(self, node: ASTAttr) -> Value: ...
    @abstractmethod
    def visit_scoped_block(self, node: ASTScopedBlock) -> Value: ...
    @abstractmethod
    def visit_spec_decl(self, node: ASTSpecDecl) -> Value: ...
    @abstractmethod
    def visit_priv_decl(self, node: ASTPrivDecl) -> Value: ...
    @abstractmethod
    def visit_version(self, node: ASTVersion) -> Value: ...
    @abstractmethod
    def visit_import_req(self, node: ASTImportReq) -> Value: ...
    @abstractmethod
    def visit_version_req(self, node: ASTVersionReq) -> Value: ...
