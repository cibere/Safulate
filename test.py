# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "msgspec",
# ]
# ///
from safulate.lexer import Lexer, GroupType
from safulate.tokens import GroupToken
import json

tks = [
    ("first", GroupType.start_paren),
    ("second", GroupType.start_paren),
    ("third", GroupType.start_list),
    ("", GroupType.end_list),
    ("fourth", GroupType.end_paren),
    ("foo", GroupType.start_paren),
    ("", GroupType.end_paren),
    ("end", GroupType.end_paren),
]
lexer = Lexer("")
tokens = lexer.lex_group(tks)
# print(tokens)

res = GroupToken(tokens=tokens)
print("-" * 10)
print(json.dumps(res.to_dict(), indent=4))

{
    "type": "group",
    "children": [
        "first",
        {"type": "group", "children": ["second"]},
        {"type": "group", "children": ["third"]},
        "fourth",
    ],
}
