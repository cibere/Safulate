from .core import (
    StringToken,
    VariableToken,
    GroupToken,
    ArgToken,
    CommaToken,
    ListToken,
    SubtractToken,
    EqualsToken,
    EndOfStatementToken,
    ContainerToken,
    DictToken,
    NullToken,
    DictEntrySeperatorToken,
    FunctionToken,
    AdditionToken,
    SetVariableToken,
    IntToken,
    FloatToken,
    UndefinedToken as UndefinedToken,
    CreateFuncToken,
    NotToken,
)
from .base import BaseToken
from typing import Any

type Token = (
    BaseToken
    | StringToken
    | VariableToken
    | GroupToken
    | EndOfStatementToken
    | EqualsToken
    | SubtractToken
    | CommaToken
    | ListToken
    | FunctionToken
    | ArgToken
    | AdditionToken
    | NullToken
    | DictToken
    | DictEntrySeperatorToken
    | ContainerToken
    | SetVariableToken
    | IntToken
    | FloatToken
    | CreateFuncToken
    | NotToken
)


def python_to_token(python: Any) -> Token:
    match python:
        case str():
            return StringToken(python)
        case dict():
            data = {str(key): python_to_token(value) for key, value in python.items()}
            return DictToken(value=data)
        case list():
            return ListToken(value=[python_to_token(item) for item in python])
        case None:
            return NullToken()
    raise ValueError(f"Could not convert {python=} into a token")
