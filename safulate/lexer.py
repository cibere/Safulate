from .tokens import (
    StringToken,
    VariableToken,
    GroupToken,
    EndOfStatementToken,
    AdditionToken,
    EqualsToken,
    SubtractToken,
    Token,
    CommaToken,
    ListToken,
    DictToken,
    DictEntrySeperatorToken,
    SetVariableToken,
    IntToken,
    FloatToken,
    CreateFuncToken,
    NotToken,
)
from typing import Any, overload

# import math
from enum import Enum, auto as auto_enum

STRING_END_CHARS = ('"', "'")


class Status(Enum):
    in_string = auto_enum()
    none = auto_enum()
    exit_step_1 = auto_enum()
    exit_step_2 = auto_enum()
    in_group = auto_enum()


class GroupType(Enum):
    start_paren = "("
    end_paren = ")"
    start_list = "["
    end_list = "]"
    start_dict = "{"
    end_dict = "}"


group_type_to_cls: dict[GroupType, Any] = {
    GroupType.start_paren: GroupToken,
    GroupType.end_paren: GroupToken,
    GroupType.start_list: ListToken,
    GroupType.end_list: ListToken,
    GroupType.start_dict: DictToken,
    GroupType.end_dict: DictToken,
}
group_type_start_to_end = {
    GroupType.start_dict: GroupType.end_dict,
    GroupType.start_list: GroupType.end_list,
    GroupType.start_paren: GroupType.end_paren,
}
group_type_end_to_start = {end: start for start, end in group_type_start_to_end.items()}

special_char_tokens = {
    ";": EndOfStatementToken,
    "+": AdditionToken,
    "=": EqualsToken,
    "-": SubtractToken,
    ",": CommaToken,
    ":": DictEntrySeperatorToken,
    "~": CreateFuncToken,
    "!": NotToken,
}
keywords = {
    "set": SetVariableToken,
}

_chars = "qwertyuiopasdfghjklzxcvbnm"
variable_name_chars = _chars + _chars.upper() + "_.$"


class Lexer:
    def __init__(self, code: str) -> None:
        self.code = code
        self.tokens: list[Token] = []
        self.temp = ""
        self.status = Status.none
        self.statements: list[list[Token]] = []
        self.groups: list[tuple[str, GroupType]] = []
        self.num_groups = 0
        self.last_group_type = None

    def run_isolated(self, code: str) -> list[Token]:
        new_self = self.__class__(code)
        new_self.start()
        return new_self.tokens

    def clear_temp(self) -> None:
        txt = self.temp.strip()
        if txt:
            cls = keywords.get(txt, VariableToken)
            if txt[0].isnumeric() and cls is VariableToken:
                if "." in txt:
                    try:
                        txt = float(txt)
                    except ValueError:
                        raise RuntimeError(f"Invalid float: {txt!r}")
                    cls = FloatToken
                else:
                    try:
                        txt = int(txt)
                    except ValueError:
                        raise RuntimeError(f"Invalid int: {txt!r}")
                    cls = IntToken
            self.add(cls(txt))  # pyright: ignore[reportArgumentType]
        self.temp = ""

    def add(self, token: Token) -> None:
        post_init = getattr(token, "__post_init__", lambda: None)
        post_init()

        if isinstance(token, EndOfStatementToken):
            self.statements.append(self.tokens)
            self.tokens = []
        else:
            self.tokens.append(token)

    # def lex_group(
    #     self, group_entries: list[tuple[str, GroupType] | None | GroupToken]
    # ) -> list[Token]:
    #     i = 1
    #     middle = []
    #     while any([isinstance(x, tuple) for x in group_entries]):
    #         for idx, entry in enumerate(group_entries):
    #             if entry is None or isinstance(entry, GroupToken):
    #                 continue
    #             text, group_type = entry
    #             print(f"Handling entry {entry=}")

    #             try:
    #                 middle =group_entries[idx:idx + i]
    #                 end = middle.pop(-1)
    #                 if isinstance(end, tuple) and group_type == end[1]:
    #                     group_entries[idx + i] = None
    #                     start = self.run_isolated(text)
    #                     end = self.run_isolated(end[0])
    #                     resolved_middle = [token for token in middle if isinstance(token, GroupToken)]
    #                     group_entries[idx] = GroupToken(tokens=[*start, *resolved_middle, *end])
    #             except IndexError as e:
    #                 print(f"{e=}")
    #         i += 1

    #     return group_entries

    @overload
    def lex_group(
        self, group_tokens: list[tuple[str, GroupType]], *, end: GroupType
    ) -> tuple[str, GroupType] | list[Token]: ...
    @overload
    def lex_group(self, group_tokens: list[tuple[str, GroupType]]) -> list[Token]: ...
    def lex_group(
        self, group_tokens: list[tuple[str, GroupType]], *, end: GroupType | None = None
    ) -> list[Token] | tuple[str, GroupType]:
        while group_tokens:
            text, group_type = group_tokens.pop(0)
            print(f"Lexing group: {group_type=} {text=}")
            match group_type:
                case (
                    GroupType.start_dict
                    | GroupType.start_list
                    | GroupType.start_paren as start_type
                ):
                    end_type = group_type_start_to_end[start_type]
                    print(f"is start. {end_type=}")
                    ret = self.lex_group(group_tokens, end=end_type)
                    print(f"{ret=}")
                    if isinstance(ret, tuple):
                        return self.run_isolated(text + ret[0])
                    ret2 = self.lex_group(group_tokens, end=end_type)
                    print(f"{ret2=}")
                    # if
                    return [*self.run_isolated(text), GroupToken(tokens=ret)]
                case (
                    GroupType.end_dict
                    | GroupType.end_list
                    | GroupType.end_paren as end_type
                ) if end is not None and end_type is end:
                    print("is end")
                    return (
                        text,
                        group_type,
                    )
                case (
                    GroupType.end_dict
                    | GroupType.end_list
                    | GroupType.end_paren as end_type
                ):
                    raise RuntimeError(
                        f"{end_type!r} detected without starting version"
                    )
                case other:
                    raise RuntimeError(f"How did we get here? {other=}")

        return []

    def start(self) -> None:
        for line in self.code.splitlines():
            for idx, char in enumerate(line):
                print(f"{char=}")

                match (self.status, char):
                    # Strings
                    case (Status.none, '"'):
                        self.status = Status.in_string
                        self.clear_temp()
                    case (Status.in_string, '"'):
                        self.add(StringToken(self.temp))
                        self.temp = ""
                        self.status = Status.none
                    case (Status.in_string, char):
                        self.temp += char

                    # comments
                    case (Status.none, "#"):
                        break

                    # groups
                    case (Status.none, "(" | "[" | "{" as char):
                        self.clear_temp()
                        self.status = Status.in_group
                        self.groups = []
                        self.num_groups = 1
                        self.last_group_type = GroupType(char)
                        print(
                            f"Setting last group to {self.last_group_type=} for char {char}"
                        )
                    case (Status.in_group, "(" | "[" | "{" as char):
                        assert self.last_group_type
                        print(f"{self.last_group_type=}")
                        self.groups.append((self.temp, self.last_group_type))
                        self.temp = ""
                        self.num_groups += 1
                        self.last_group_type = GroupType(char)
                    case (Status.in_group, ")" | "]" | "}" as char):
                        group_type = GroupType(char)

                        if (
                            self.last_group_type
                            and group_type
                            == group_type_start_to_end[self.last_group_type]
                        ):
                            self.groups.append(("", self.last_group_type))
                            # self.num_groups -= 1
                            self.last_group_type = None

                        self.groups.append((self.temp, group_type))
                        self.temp = ""
                        self.num_groups -= 1

                        if self.num_groups == 0:
                            print(f"{self.groups=}")
                            # if len(self.groups) % 2 != 0:
                            #     code, paren_type = self.groups.pop(
                            #         int(len(self.groups) / 2)
                            #     )
                            #     token = [
                            #         group_type_to_cls[paren_type](
                            #             tokens=self.run_isolated(code)
                            #         )
                            #     ]
                            # else:
                            #     token = []

                            # while self.groups:
                            #     print(f"{self.groups=}")
                            #     print(f"{token=}")
                            #     num_groups = len(self.groups)

                            #     idx = math.ceil(num_groups / 2) - 1
                            #     first, first_type = self.groups.pop(idx)
                            #     second, second_type = self.groups.pop(idx)
                            #     assert first_type is second_type, (
                            #         f"{first_type} != {second_type} for {idx} idx"
                            #     )

                            #     token = [
                            #         group_type_to_cls[first_type](
                            #             self.run_isolated(first)
                            #             + token
                            #             + self.run_isolated(second)
                            #         )
                            #     ]

                            # self.add(token[0])
                            self.add(GroupToken(tokens=self.lex_group(self.groups)))
                            self.groups = []
                            self.status = Status.none
                    case (Status.in_group, char):
                        self.temp += char

                    # special chars like operators
                    case (
                        Status.none,
                        "-" | "+" | "=" | ";" | "," | ":" | "~" | "!" as special_char,
                    ):
                        self.clear_temp()
                        self.add(special_char_tokens[special_char](special_char))

                    # no match
                    case (_, char) if (
                        char in variable_name_chars
                        and not self.temp.startswith(
                            ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")
                        )
                    ):
                        self.temp += char
                    case (_, char) if char in "1234567890":
                        self.temp += char
                    case (_, ".") if self.temp.isnumeric():
                        self.temp += "."
                    case (_, char) if char.strip():
                        raise RuntimeError(f"Invalid Character: {char!r} as pos {idx}")
                    case (_, char):
                        if self.temp.strip():
                            self.clear_temp()

        self.clear_temp()

        match self.status:
            case Status.in_string:
                raise RuntimeError("String was not closed")
            case Status.in_group:
                raise RuntimeError("Parens were not exited")
            case Status.none:
                pass
            case other:
                raise RuntimeError(f"Status is not none: {other!r}")
