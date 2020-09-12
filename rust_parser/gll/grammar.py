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
import enum
from typing import sealed, Dict, Iterable, List, Optional

from . import tokens


class GllParseError(Exception):
    pass


@sealed
class RuleNode:
    pass


@dataclass
class LabeledNode(RuleNode):
    name: str
    item: RuleNode


@dataclass
class StringLiteral(RuleNode):
    string: str


@dataclass
class CharacterRange(RuleNode):
    from_char: str
    to_char: str


@dataclass
class SymbolName(RuleNode):
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

    positive: bool
    items: List[RuleNode]
    separator: Optional[str]
    allow_trailing: bool
    """Whether an extra separator is allowed at the end."""


@dataclass
class Grammar:
    rules: Dict[str, Dict[str, RuleNode]]


_ALTERNATION_TOKEN = object()
_LABEL_TOKEN = object()


def apply_labels_in_group(raw_group):
    group = []
    i = 0
    while i < len(raw_group):
        item = raw_group[i]
        if item is _LABEL_TOKEN:
            label = group.pop()
            assert isinstance(label, SymbolName)
            i += 1
            next_item = raw_group[i]
            group.append(LabeledNode(label.name, next_item))
        else:
            group.append(item)

        i += 1

    return group


def apply_alternation_in_group(raw_group):
    if len(raw_group) == 0:
        raise GllParseError(f"Empty group in rule {current_rule_name}")
    elif len(raw_group) == 1:
        return raw_group[0]
    else:
        clauses = [[]]
        for node in raw_group:
            if node is _ALTERNATION_TOKEN:
                clauses.append([])
            else:
                clauses[-1].append(node)
        assert clauses
        if len(clauses) == 1:
            return Concatenation(items=raw_group)
        else:
            return Alternation(
                [
                    clause[0] if len(clause) == 1 else Concatenation(clause)
                    for clause in clauses
                ]
            )


def postprocess_group(group):
    """Handles infix notations after parsing the whole group.
    This is not the cleanest way to do it, but it's simpler."""
    return apply_alternation_in_group(apply_labels_in_group(group))


class _State(enum.Enum):
    """Parser state"""
    START = 0
    GOT_SYMBOL_NAME = 1
    GOT_EQUAL = 2
    GOT_PIPE = 3
    GOT_RULE_NAME = 4
    IN_NAMED_RULE = 5
    IN_ANONYMOUS_RULE = 6

    # Transition diagram:
    #
    # START -> GOT_SYMBOL_NAME -> GOT_EQUAL -> GOT_PIPE -> GOT_RULE_NAME -> IN_NAMED_RULE
    #  ^ ^                           |                                            |
    #  | |                           v                                            |
    #  | |                   IN_ANONYMOUS_RULE                                    |
    #  | |                           |                                            |
    #  | +---------------------------+                                            |
    #  |                                                                          |
    #  +--------------------------------------------------------------------------+


def parse_gll(toks: Iterable[tokens.Token]) -> Grammar:
    rules = {}

    state = _State.START
    stack = None
    current_symbol_name = None
    current_rule_name = None

    def assert_state_in_rule(error_message):
        nonlocal state
        if state == _State.GOT_EQUAL:
            state = _State.IN_ANONYMOUS_RULE
        elif state not in (_State.IN_NAMED_RULE, _State.IN_ANONYMOUS_RULE):
            raise GllParseError(error_message)

    toks_it = iter(toks)

    for tok in toks_it:
        match tok:

            #####################
            # Symbol "management"

            case tokens.Name(name) if state == _State.START:
                # symbol name
                assert current_symbol_name is None
                assert current_rule_name is None
                assert stack is None
                if name in rules:
                    raise GllParseError(f"Duplicate symbol: {name}")
                state = _State.GOT_SYMBOL_NAME
                current_symbol_name = name
                rules[name] = {}

            case tokens.SimpleToken.EQUAL:
                # = char after a symbol name
                if state != _State.GOT_SYMBOL_NAME:
                    raise GllParseError("Unexpected =.")
                assert stack is None
                state = _State.GOT_EQUAL

                stack = [[]]  # must initialize it now, in case it's an anonymous rule

            case tokens.SimpleToken.SEMICOLON:
                # end of symbol
                if state not in (_State.IN_NAMED_RULE, _State.IN_ANONYMOUS_RULE):
                    raise GllParseError("Unexpected ;")
                assert stack is not None
                assert len(stack) >= 1
                if len(stack) > 1:
                    raise GllParseError(
                        f"unexpected semicolon in rule {current_rule_name} (unclosed group?)"
                    )

                if len(stack[0]) == 0:
                    raise GllParseError(
                        f"unexpected semicolon in rule {current_rule_name} (empty rule?)"
                    )

                rule = postprocess_group(stack[0])

                rules[current_symbol_name][current_rule_name] = rule

                state = _State.START
                current_symbol_name = None
                current_rule_name = None
                stack = None

            #####################
            # Rule "management"

            case tokens.Name(name) if state == _State.GOT_PIPE:
                # rule name
                assert current_symbol_name is not None
                assert current_rule_name is None
                if name in rules[current_symbol_name]:
                    raise GllParseError(
                        f"Duplicate rule for symbol {current_symbol_name}: {name}"
                    )
                current_rule_name = name
                state = _State.GOT_RULE_NAME

            case tokens.SimpleToken.COLON if state == _State.GOT_RULE_NAME:
                assert stack == [[]]
                state = _State.IN_NAMED_RULE

            case tokens.SimpleToken.PIPE if state == _State.GOT_EQUAL:
                # start of the first rule
                assert current_symbol_name is not None
                assert current_rule_name is None
                assert stack == [[]]

                state = _State.GOT_PIPE

            case tokens.SimpleToken.PIPE if len(stack) == 1:
                # end a rule, start a new one

                if state != _State.IN_NAMED_RULE:
                    raise GllParseError("unexpected |")

                rules[current_symbol_name][current_rule_name] = postprocess_group(stack[0])

                state = _State.GOT_PIPE
                current_rule_name = None
                stack = [[]]

            #####################
            # Groups

            case tokens.SimpleToken.GROUP_START:
                assert_state_in_rule("unexpected { (outside a rule?)")
                stack.append([])

            case tokens.SimpleToken.GROUP_END:
                assert_state_in_rule("unexpected } (outside a rule?)")

                group = postprocess_group(stack.pop())
                stack[-1].append(group)

            #####################
            # Combination operators

            case tokens.SimpleToken.PIPE:
                # inside a group
                stack[-1].append(_ALTERNATION_TOKEN)

            case tokens.SimpleToken.COLON:
                assert_state_in_rule("unexpected ':'")
                if not stack[-1]:
                    raise GllParseError("missing lael before ':'")
                else:
                    label = stack[-1][-1]
                    if not isinstance(label, SymbolName):
                        raise GllParseError("{label} is not a valid label")
                stack[-1].append(_LABEL_TOKEN)

            #####################
            # Quantifiers

            case tokens.SimpleToken.QUESTION_MARK:
                assert_state_in_rule("unexpected '?'")
                stack[-1].append(Option(stack[-1].pop()))

            case tokens.SimpleToken.STAR:
                assert_state_in_rule("unexpected '*'")
                stack[-1].append(Repeated(False, stack[-1].pop(), None, False))

            case tokens.SimpleToken.PLUS:
                assert_state_in_rule("unexpected '+'")
                stack[-1].append(Repeated(True, stack[-1].pop(), None, False))

            case tokens.SimpleToken.PERCENT | tokens.SimpleToken.DOUBLE_PERCENT:
                assert_state_in_rule(f"unexpected '{tok.value}'")
                next_token = next(toks_it)  # preempt the next token

                match (stack[-1][-1], next_token):
                    case (Repeated(positive, items, None, _), tokens.String(s)):
                        stack[-1][-1].separator = s
                        stack[-1][-1].allow_trailing = (
                            tok == tokens.SimpleToken.DOUBLE_PERCENT
                        )
                    case (_, tokens.String(s)):

                        raise GllParseError(f"{tok.value} does not follow + or *")
                    case (_, _):
                        raise GllParseError(f"{tok.value} is not followed by a string")

            #####################
            # Others

            case tokens.Name(name):
                # reference to another rule
                assert_state_in_rule(f"unexpected name {name}")
                assert current_symbol_name is not None, name
                assert stack
                stack[-1].append(SymbolName(name))

            case tokens.String(s):
                assert_state_in_rule(f'unexpected string literal "{s}"')
                stack[-1].append(StringLiteral(s))

            case _:
                assert False, tok

    assert state == _State.START, ("unexpected EOF, missing ;", state)

    return Grammar(rules)
