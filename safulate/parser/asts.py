from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..lexer import Token, TokenType
from .enums import ParamType

if TYPE_CHECKING:
    from packaging.version import Version as _PackagingVersion

    from ..interpreter import SafBaseObject

__all__ = (
    "ASTAssign",
    "ASTAtom",
    "ASTBinary",
    "ASTBlock",
    "ASTBreak",
    "ASTCall",
    "ASTContinue",
    "ASTDel",
    "ASTDynamicID",
    "ASTEditObject",
    "ASTExprStmt",
    "ASTForLoop",
    "ASTFormat",
    "ASTFuncDecl",
    "ASTFuncDecl_Param",
    "ASTGetPriv",
    "ASTIf",
    "ASTImportReq",
    "ASTList",
    "ASTNode",
    "ASTPar",
    "ASTProgram",
    "ASTProperty",
    "ASTRaise",
    "ASTRegex",
    "ASTReturn",
    "ASTSwitchCase",
    "ASTTryCatch",
    "ASTTryCatch_CatchBranch",
    "ASTTypeDecl",
    "ASTUnary",
    "ASTVarDecl",
    "ASTVersionReq",
    "ASTVisitor",
    "ASTWhile",
    "ParamType",
)


class ASTNode(ABC):
    @abstractmethod
    def visit(self, visitor: ASTVisitor) -> SafBaseObject: ...


@dataclass
class ASTProgram(ASTNode):
    stmts: list[ASTNode]

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_program(self)


@dataclass
class ASTDynamicID(ASTNode):
    token: Token
    expr: ASTNode | None

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_dynamic_id(self)

    def resolve(self, visitor: ASTVisitor) -> str:
        return visitor.resolve_dynamic_id(self)


@dataclass
class ASTVarDecl(ASTNode):
    name: ASTDynamicID | Token
    value: ASTNode | None
    keyword: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_var_decl(self)


@dataclass
class ASTFuncDecl_Param:
    name: Token
    default: ASTNode | None | SafBaseObject
    type: ParamType

    @property
    def is_arg(self) -> bool:
        return self.type is ParamType.arg or self.type is ParamType.arg_or_kwarg

    @property
    def is_kwarg(self) -> bool:
        return self.type is ParamType.kwarg or self.type is ParamType.arg_or_kwarg


@dataclass
class ASTFuncDecl(ASTNode):
    name: Token | ASTDynamicID | None
    params: list[ASTFuncDecl_Param]
    body: ASTBlock

    kw_token: Token
    paren_token: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_func_decl(self)


@dataclass
class ASTBlock(ASTNode):
    stmts: list[ASTNode]

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_block(self)


@dataclass
class ASTEditObject(ASTNode):
    obj: ASTNode
    block: ASTBlock

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_edit_object(self)


@dataclass
class ASTIf(ASTNode):
    condition: ASTNode
    body: ASTNode
    else_branch: ASTNode | None
    kw_token: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_if(self)


@dataclass
class ASTWhile(ASTNode):
    condition: ASTNode
    body: ASTNode
    kw_token: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_while(self)


@dataclass
class ASTReturn(ASTNode):
    keyword: Token
    expr: ASTNode | None

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_return(self)


@dataclass
class ASTBreak(ASTNode):
    keyword: Token
    amount: ASTNode | None

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_break(self)


@dataclass
class ASTContinue(ASTNode):
    keyword: Token
    amount: ASTNode | None

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_continue(self)


@dataclass
class ASTExprStmt(ASTNode):
    expr: ASTNode

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_expr_stmt(self)


@dataclass
class ASTAssign(ASTNode):
    name: Token
    value: ASTNode

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_assign(self)


@dataclass
class ASTBinary(ASTNode):
    left: ASTNode
    op: Token
    right: ASTNode

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_binary(self)


@dataclass
class ASTUnary(ASTNode):
    op: Token
    right: ASTNode

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_unary(self)


@dataclass
class ASTCall(ASTNode):
    callee: ASTNode
    paren: Token
    params: list[tuple[ParamType, str | None, ASTNode]]

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_call(self)

    @classmethod
    def get_attr(cls, *, expr: ASTNode, dot: Token, attr: Token) -> ASTCall:
        return cls(
            callee=expr,
            paren=dot,
            params=[
                (
                    ParamType.arg,
                    None,
                    ASTAtom(attr.with_type(TokenType.STR, lexme=attr.lexme)),
                )
            ],
        )


@dataclass
class ASTAtom(ASTNode):
    token: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_atom(self)


@dataclass
class ASTVersionReq(ASTNode):
    keyword: Token

    left: _PackagingVersion
    op: Token | None
    right: _PackagingVersion | None

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_version_req(self)


@dataclass
class ASTImportReq(ASTNode):
    source: Token
    name: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_import_req(self)


@dataclass
class ASTRaise(ASTNode):
    expr: ASTNode
    kw: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_raise(self)


@dataclass
class ASTForLoop(ASTNode):
    var_name: Token
    source: ASTNode
    body: ASTNode

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_for_loop(self)


@dataclass
class ASTDel(ASTNode):
    var: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_del(self)


@dataclass
class ASTTryCatch_CatchBranch:
    body: ASTBlock
    target: tuple[Token, ASTNode] | None
    var: Token | None


@dataclass
class ASTTryCatch(ASTNode):
    body: ASTBlock
    catch_branches: list[ASTTryCatch_CatchBranch]
    else_branch: ASTBlock | None

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_try_catch(self)


@dataclass
class ASTSwitchCase(ASTNode):
    cases: list[tuple[ASTNode, ASTBlock]]
    else_branch: ASTBlock | None
    expr: ASTNode
    kw: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_switch_case(self)


@dataclass
class ASTList(ASTNode):
    children: list[ASTBlock]

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_list(self)


@dataclass
class ASTFormat(ASTNode):
    obj: ASTNode
    spec: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_format(self)


@dataclass
class ASTProperty(ASTNode):
    body: ASTBlock
    name: Token
    kw_token: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_property(self)


@dataclass
class ASTRegex(ASTNode):
    value: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_regex(self)


@dataclass
class ASTTypeDecl(ASTNode):
    name: Token | ASTDynamicID
    body: ASTBlock | None
    init: ASTFuncDecl | None
    compare_func: ASTNode | None
    arity: int
    kw_token: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_type_decl(self)


@dataclass
class ASTPar(ASTNode):
    levels: list[Token]

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_get_par(self)


@dataclass
class ASTGetPriv(ASTNode):
    levels: list[Token]
    name: Token

    def visit(self, visitor: ASTVisitor) -> SafBaseObject:
        return visitor.visit_get_priv(self)


class ASTVisitor(ABC):
    @abstractmethod
    def visit_program(self, node: ASTProgram) -> SafBaseObject: ...
    @abstractmethod
    def visit_block(self, node: ASTBlock) -> SafBaseObject: ...
    @abstractmethod
    def visit_if(self, node: ASTIf) -> SafBaseObject: ...
    @abstractmethod
    def visit_while(self, node: ASTWhile) -> SafBaseObject: ...
    @abstractmethod
    def visit_return(self, node: ASTReturn) -> SafBaseObject: ...
    @abstractmethod
    def visit_break(self, node: ASTBreak) -> SafBaseObject: ...
    @abstractmethod
    def visit_expr_stmt(self, node: ASTExprStmt) -> SafBaseObject: ...
    @abstractmethod
    def visit_var_decl(self, node: ASTVarDecl) -> SafBaseObject: ...
    @abstractmethod
    def visit_func_decl(self, node: ASTFuncDecl) -> SafBaseObject: ...
    @abstractmethod
    def visit_assign(self, node: ASTAssign) -> SafBaseObject: ...
    @abstractmethod
    def visit_binary(self, node: ASTBinary) -> SafBaseObject: ...
    @abstractmethod
    def visit_unary(self, node: ASTUnary) -> SafBaseObject: ...
    @abstractmethod
    def visit_call(self, node: ASTCall) -> SafBaseObject: ...
    @abstractmethod
    def visit_atom(self, node: ASTAtom) -> SafBaseObject: ...
    @abstractmethod
    def visit_edit_object(self, node: ASTEditObject) -> SafBaseObject: ...
    @abstractmethod
    def visit_import_req(self, node: ASTImportReq) -> SafBaseObject: ...
    @abstractmethod
    def visit_version_req(self, node: ASTVersionReq) -> SafBaseObject: ...
    @abstractmethod
    def visit_raise(self, node: ASTRaise) -> SafBaseObject: ...
    @abstractmethod
    def visit_for_loop(self, node: ASTForLoop) -> SafBaseObject: ...
    @abstractmethod
    def visit_del(self, node: ASTDel) -> SafBaseObject: ...
    @abstractmethod
    def visit_try_catch(self, node: ASTTryCatch) -> SafBaseObject: ...
    @abstractmethod
    def visit_switch_case(self, node: ASTSwitchCase) -> SafBaseObject: ...
    @abstractmethod
    def visit_continue(self, node: ASTContinue) -> SafBaseObject: ...
    @abstractmethod
    def visit_list(self, node: ASTList) -> SafBaseObject: ...
    @abstractmethod
    def visit_format(self, node: ASTFormat) -> SafBaseObject: ...
    @abstractmethod
    def visit_property(self, node: ASTProperty) -> SafBaseObject: ...
    @abstractmethod
    def visit_regex(self, node: ASTRegex) -> SafBaseObject: ...
    @abstractmethod
    def visit_type_decl(self, node: ASTTypeDecl) -> SafBaseObject: ...
    @abstractmethod
    def visit_get_par(self, node: ASTPar) -> SafBaseObject: ...
    @abstractmethod
    def visit_get_priv(self, node: ASTGetPriv) -> SafBaseObject: ...
    @abstractmethod
    def visit_dynamic_id(self, node: ASTDynamicID) -> SafBaseObject: ...
    @abstractmethod
    def resolve_dynamic_id(self, node: ASTDynamicID) -> str: ...
