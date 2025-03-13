from __future__ import annotations
from typing import Any, TYPE_CHECKING, Literal
from ..utils import split_list

if TYPE_CHECKING:
    from . import Token
    from ..executer import Executer

from .base import BaseToken, method


class StringToken(BaseToken[str], tag="string"):
    @method("replace")
    def method_replace(
        self, exe: Executer, before: StringToken, after: StringToken
    ) -> StringToken:
        return StringToken(self.value.replace(before.value, after.value, count=1))

    @method("replace_all")
    def method_replace_all(
        self, exe: Executer, before: StringToken, after: StringToken
    ) -> StringToken:
        return StringToken(self.value.replace(before.value, after.value))

    @method("$str")
    def to_str(self, exe: Executer) -> StringToken:
        return self

    @method("$add")
    def add(self, exe: Executer, other: StringToken) -> StringToken:
        # print("str adding")
        return StringToken(other.value + self.value)


class IntToken(BaseToken[int], tag="int"):
    @method("$str")
    def to_str(self, exe: Executer) -> StringToken:
        return StringToken(str(self.value))

    @method("$add")
    def add(self, exe: Executer, other: IntToken) -> IntToken:
        return IntToken(other.value + self.value)

    @method("$sub")
    def sub(self, exe: Executer, other: IntToken) -> IntToken:
        return IntToken(self.value - other.value)

    @method("$div")
    def divide(self, exe: Executer, other: IntToken) -> FloatToken:
        return FloatToken(self.value / other.value)

    @method("to_float")
    def to_float(self, exe: Executer) -> FloatToken:
        return FloatToken(float(self.value))


class FloatToken(BaseToken[float], tag="float"):
    @method("$str")
    def to_str(self, exe: Executer) -> StringToken:
        return StringToken(str(self.value))

    @method("$add")
    def add(self, exe: Executer, other: FloatToken) -> FloatToken:
        return FloatToken(self.value + other.value)

    @method("$sub")
    def sub(self, exe: Executer, other: FloatToken) -> FloatToken:
        return FloatToken(self.value - other.value)

    @method("$div")
    def divide(self, exe: Executer, other: FloatToken) -> FloatToken:
        return FloatToken(self.value / other.value)

    @method("to_int")
    def to_int(self, exe: Executer) -> IntToken:
        return IntToken(int(self.value))


class VariableToken(BaseToken[str], tag="variable"):
    def validate(self) -> None:
        if self.value.startswith((".", "$")) or self.value.endswith((".", "$")):
            raise ValueError(
                f"Variable starts or ends with invalid characters: {self.value!r}"
            )

    @method("$str")
    def to_str(self, exe: Executer) -> StringToken:
        tk = exe.resolve_token(self)
        # print(f"Variable token got token: {id(tk)} {tk!r}")
        return tk.to_str(exe)

    def __hash__(self):
        return hash(self.value)


class BaseGroup[VT](BaseToken[VT]):
    def __init__(
        self, *, tokens: list[Token] | None = None, value: VT | None = None
    ) -> None:
        if tokens is not None and value is None:
            value = self.convert_to_value(tokens)
        elif tokens is None and value is not None:
            pass
        else:
            raise ValueError(f"Mismatch of args. {value=} {tokens=}")
        super().__init__(value)

    def convert_to_value(self, tokens: list[Token]) -> VT:
        raise NotImplementedError


class GroupToken(BaseGroup[list["Token"]], tag="group"):
    def convert_to_value(self, tokens: list[Token]) -> list[Token]:
        return tokens

    @method("$str")
    def to_str(self, exe: Executer) -> StringToken:
        if len(self.value) == 1:
            return self.value[0].to_str(exe)
        return StringToken(
            f"({', '.join(val.to_str(exe).value for val in self.value)})"
        )

    def resolve(self, exe: Executer) -> Token:
        if self.value:
            return exe.evaluate_expression(self.value)
        return UndefinedToken(None)


class ListToken(BaseGroup[list["Token"]], tag="list"):
    def convert_to_value(self, tokens: list[Token]) -> list[Token]:
        entries = split_list(tokens, lambda d: isinstance(d, CommaToken))
        return [
            children[0] if len(children) == 1 else GroupToken(tokens=children)
            for children in entries
        ]

    @method("for_each")
    def for_each(self, exe: Executer, func: FunctionToken) -> NullToken:
        for child in self.value:
            exe.execute_function(func, ListToken(value=[child]))
        return NullToken()

    @method("$str")
    def to_str(self, exe: Executer) -> StringToken:
        # print(f"{id(self)}: {self.value=}")
        return StringToken(
            str(
                [
                    getattr(child, "to_str")(exe).value
                    for child in self.value
                    # if (print(f"{child=}")) is None
                ]
            )
        )

    def to_python(self, exe: Executer) -> list[Any]:
        return [item.to_python(exe) for item in self.value]

    def resolve(self, exe: Executer) -> ListToken:
        return ListToken(value=[token.resolve(exe) for token in self.value])


class ArgToken(BaseToken[str], tag="arg"):
    def __init__(self, value: str, required: bool) -> None:
        super().__init__(value)

        self.required = required


class FunctionToken(BaseGroup[list["Token"]], tag="func"):
    def __init__(self, *, tokens: list[Token], args: list[ArgToken]) -> None:
        super().__init__(tokens=tokens)

        self.args = args


class NullToken(
    BaseToken[None],
    tag="null",
):
    def __init__(self, value: None = None) -> None:
        super().__init__(value)


class DictToken(BaseToken[dict[str, "Token"]], tag="dict"):
    def __init__(
        self,
        *,
        tokens: list[Token] | None = None,
        value: dict[str, Token] | None = None,
    ) -> None:
        if tokens is not None and value is None:
            entries = split_list(tokens, lambda d: isinstance(d, CommaToken))
            data: dict[str, Token] = {}
            for entry in entries:
                if not entry:
                    continue

                parts = split_list(
                    entry,
                    lambda d: isinstance(d, (EqualsToken, DictEntrySeperatorToken)),
                )
                if len(parts) != 2:
                    raise RuntimeError("invalid dict entry")
                if len(parts[0]) != 1 or not isinstance(parts[0][0], StringToken):
                    raise RuntimeError("invalid dict key")
                # print(parts)
                data[parts[0][0].value] = GroupToken(tokens=parts[1])
        elif value is not None and tokens is None:
            data = value
        else:
            raise ValueError("Mismatch of args")

        super().__init__(data)

    @method("$str")
    def to_str(self, exe: Executer) -> StringToken:
        return StringToken(
            str({key: value.to_str(exe).value for key, value in self.value.items()})
        )

    def to_python(self, exe: Executer) -> dict[str, Any]:
        return {key: item.to_python(exe) for key, item in self.value.items()}


class ContainerToken(BaseToken[str], tag="container"):
    ...

    @method("$repr")
    def method_repr(self, exe: Executer) -> StringToken:
        return StringToken(f"<Containter {self.value!r}>")


class SetVariableToken(BaseToken[Literal["set"]], tag="set-var"): ...


class UndefinedToken(BaseToken):
    def __init__(self, *args: Any): ...
    @property
    def value(self) -> Any:
        raise RuntimeError("Undefined has no value")


class EndOfStatementToken(BaseToken[Literal[";"]], tag="end-of-statement"): ...


class DictEntrySeperatorToken(BaseToken[Literal[":"]], tag="dict-entry-seperator"): ...


class AdditionToken(BaseToken[Literal["+"]], tag="add"): ...


class EqualsToken(BaseToken[Literal["="]], tag="equals"): ...


class SubtractToken(BaseToken[Literal["-"]], tag="sub"): ...


class CommaToken(BaseToken[Literal[","]], tag="comma"): ...


class NotToken(BaseToken[Literal["!"]], tag="not"): ...


class CreateFuncToken(BaseToken[Literal["~"]], tag="create-func"): ...
