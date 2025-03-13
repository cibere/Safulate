from .tokens import (
    Token,
    StringToken,
    AdditionToken,
    GroupToken,
    VariableToken,
    EqualsToken,
    ListToken,
    FunctionToken,
    ArgToken,
    SetVariableToken,
    BaseToken,
    SubtractToken,
    UndefinedToken,
    NotToken,
    IntToken,
    ContainerToken,
)
from .libs.builtins import exporter as builtins
from typing import Any
from .tokens.function import Function
from typing import Sequence


class Executer:
    def __init__(
        self,
        variables: dict[str, Token] | None = None,
        *,
        additional_imports: list[ContainerToken] | None = None,
    ) -> None:
        self.additional_imports = {tkn.value: tkn for tkn in (additional_imports or [])}

        self.variables: dict[str, Token] = {} | builtins.exports
        if variables:
            self.variables.update(variables)

    @classmethod
    def split_var_name(cls, before: str) -> list[str]:
        parts = []
        temp = ""
        for char in before:
            if char == ".":
                parts.append(temp)
                temp = ""
            elif char == "$":
                if temp:
                    parts.append(temp)
                temp = "$"
            else:
                temp += char
        parts.append(temp)
        return parts

    def __getitem__(self, key: str) -> Token:
        parts = self.split_var_name(key)

        token = self.variables[(parts.pop(0))]
        while parts:
            token = token[parts.pop(0)]
        return token

    def __setitem__(self, key: str, value: Token) -> None:
        parts = self.split_var_name(key)

        name = parts.pop(-1)

        token = self
        while parts:
            token = token[parts.pop(0)]

        if token is self:
            self.variables[name] = value
        else:
            token[name] = value

    def resolve_token(self, original: Token) -> Token:
        if not isinstance(original, VariableToken):
            return original

        token = self[original.value]
        if token is None:
            raise RuntimeError(f"Variable {original.value} not found")
        if isinstance(token, VariableToken):
            return self.resolve_token(token)
        return token

    def _build_variables(
        self, args: list[ArgToken], values: ListToken
    ) -> dict[str, Token]:
        vars: dict[str, Token] = {}

        for idx, arg in enumerate(args):
            try:
                value = values.value[idx]
            except IndexError:
                if arg.required:
                    raise RuntimeError(
                        f"{len(values.value)} args were provided to a function that takes {len(args)} arguments"
                    )
                break
            if isinstance(value, UndefinedToken):
                continue

            vars[arg.value] = self.resolve_token(value)
        return vars

    def execute_function(self, func: Any, args: ListToken) -> Token:
        if isinstance(func, Function):
            return func(
                self,
                **{
                    key: value
                    for key, value in self._build_variables(func.args, args).items()
                },
            )
        elif isinstance(func, FunctionToken):
            executer = Executer(
                variables=self.variables | self._build_variables(func.args, args)
            )
            return executer.evaluate_expression(func.value)
        else:
            raise RuntimeError("not a function")

    def get_attr[T](
        self, token: Token, attr: str, check, rt: type[T] = BaseToken
    ) -> T | None:
        try:
            val = token[attr]
            if check(val):
                return val  # pyright: ignore[reportReturnType]
        except KeyError:
            return

    def evaluate_expression(self, tokens: Sequence[Token]) -> Token:
        # print("evaluating expression", tokens)
        match tokens:
            case (
                BaseToken() as a,
                AdditionToken() | SubtractToken() as op,
                BaseToken() as b,
            ):
                try:
                    func = a[f"${op.tag}"]
                except KeyError:
                    raise RuntimeError(f"{a!r} does not support the {op!r} operation")

                return self.execute_function(func, ListToken(value=[b]))
            case (
                BaseToken() as a,
                EqualsToken() | NotToken() as op,
                EqualsToken(),
                BaseToken() as b,
            ):
                try:
                    func = a["$eq"]
                except KeyError:
                    raise RuntimeError(f"{a!r} does not support equality checks")
                res = self.execute_function(func, ListToken(value=[b]))
                if not isinstance(res, IntToken) or res.value not in (0, 1):
                    raise RuntimeError("equality checks must return 0 or 1")
                if isinstance(op, NotToken):
                    res.value = 0 if res.value == 1 else 1
                return res
            case (VariableToken() as var, ListToken() | GroupToken() as args):
                func = self[var.value]
                if func is None:
                    raise RuntimeError(f"Variable not defined: {var.value!r}")
                if isinstance(args, GroupToken):
                    args = ListToken(tokens=args.value)
                return self.execute_function(
                    func, ListToken(value=[]) if not args.value else args.resolve(self)
                )
            case (VariableToken() as token,):
                return self.resolve_token(token)
            case (
                SetVariableToken(),
                GroupToken() | VariableToken() as name,
                EqualsToken(),
                GroupToken() as value,
            ):
                if isinstance(name, GroupToken):
                    name = name.resolve(self)
                    if not isinstance(name, StringToken):
                        raise RuntimeError(
                            "The name of a dynmaic variable setting did not eval to a string"
                        )
                    name = VariableToken(name.value)

                self[name.value] = value = self.evaluate_expression(value.value)
                return value
            case (token,):
                return token
            case _:
                raise RuntimeError(f"Unable to evaluate expression: {tokens}")

    def execute(self, *statements: list[Token]) -> None:
        for idx, statement in enumerate(statements):
            try:
                self.evaluate_expression(statement)
            except Exception as e:
                raise RuntimeError(
                    f"Error occured while evaluating expression #{idx}"
                ) from e
