# Copyright (C) 2020 Valentin Lorentz
#
# This file is part of python-rust-parser.
#
# python-rust-parser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-rust-parser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with python-rust-parser.  If not, see <https://www.gnu.org/licenses/>.

"""Represents a grammar defined in GLL's language, and parses such grammar.
But does not generate a parser from this grammar."""


from dataclasses import dataclass
from typing import sealed, Dict, Iterable, List, Optional

from . import tokens


@sealed
class RuleNode:
    pass


@dataclass
class StringLiteral(RuleNode):
    string: str


@dataclass
class CharacterRange(RuleNode):
    from_char: str
    to_char: str


@dataclass
class RuleName(RuleNode):
    name: str


@dataclass
class Concatenation(RuleNode):
    items: List[RuleNode]


@dataclass
class Alternation(RuleNode):
    items: List[RuleNode]


@dataclass
class Option(RuleNode):
    """aka. 'optional' in GLL"""

    item: RuleNode


@dataclass
class Repeated(RuleNode):
    """aka. 'list' in GLL"""

    min_nb: int
    items: List[RuleNode]
    separator: Optional[str]


@dataclass
class Grammar:
    rules: Dict[str, Dict[str, RuleNode]]


_ALTERNATION_TOKEN = object()


def parse_gll(toks: Iterable[tokens.Token]) -> Grammar:
    rules = {}

    stack = None
    current_symbol_name = None
    current_rule_name = None

    for tok in toks:
        match tok:

            #####################
            # Symbol "management"

            case tokens.Name(name) if current_symbol_name is None:
                # symbol name
                assert current_rule_name is None
                assert stack is None
                current_symbol_name = name
                assert name not in rules, name
                rules[name] = {}

            case tokens.SimpleToken.EQUAL:
                # = char after a symbol name
                assert current_symbol_name is not None, "= without a symbol name"
                assert current_rule_name is None
                assert stack is None, "= inside a rule"

            case tokens.SimpleToken.SEMICOLON:
                # end of symbol
                assert stack is not None
                assert len(stack) == 1
                assert len(stack[0]) == 1, "rule has more than one direct child (missing group?)"
                rules[current_symbol_name][current_rule_name] = stack[0][0]
                current_symbol_name = None
                current_rule_name = None
                stack = None

            #####################
            # Rule "management"

            case tokens.Name(name) if current_rule_name is None:
                # rule name
                assert stack == [[]]
                assert current_symbol_name is not None
                assert current_rule_name is None
                current_rule_name = name
                assert name not in rules, name

            case tokens.SimpleToken.COLON:
                # : char after a rule name
                assert current_symbol_name is not None
                assert current_rule_name is not None, ": without a rule name"
                assert stack == [[]], ": inside a rule"

            case tokens.SimpleToken.PIPE if current_rule_name is None:
                # start of the first rule
                assert current_symbol_name is not None
                assert stack is None
                stack = [[]]

            case tokens.SimpleToken.PIPE if len(stack) == 1:
                # end a rule, start a new one
                assert len(stack[0]) == 1, "rule has more than one direct child (missing group?)"
                rules[current_symbol_name][current_rule_name] = stack[0][0]
                current_rule_name = None
                stack = [[]]

            #####################
            # Groups

            case tokens.SimpleToken.GROUP_START:
                stack.append([])

            case tokens.SimpleToken.GROUP_END:
                group = stack.pop()
                if len(group) == 0:
                    assert False, "empty group"
                elif len(group) == 1:
                    stack[-1].append(group[0])
                else:
                    if _ALTERNATION_TOKEN in group:
                        assert all(item is _ALTERNATION_TOKEN for item in group[1::2])
                        assert _ALTERNATION_TOKEN not in group[::2]
                        stack[-1].append(Alternation(items=group[::2]))
                    else:
                        stack[-1].append(Concatenation(items=group))

            #####################
            # Combination operators

            case tokens.SimpleToken.PIPE:
                # inside a group
                stack[-1].append(_ALTERNATION_TOKEN)

            #####################
            # Others

            case tokens.Name(name):
                # reference to another rule
                assert stack
                stack[-1].append(RuleName(name))

            case tokens.String(name):
                stack[-1].append(StringLiteral(name))

            case _:
                assert False, token

    assert stack is None, "unexpected EOF, missing ;"

    return Grammar(rules)
