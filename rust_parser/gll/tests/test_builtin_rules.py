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

import re

from tatsu.grammars import Grammar

from ..builtin_rules import IDENT, PUNCT, LITERAL, TOKEN_TREE, BuiltinSemantics

grammar = Grammar("gram", [TOKEN_TREE.RULE, IDENT.RULE, PUNCT.RULE, LITERAL.RULE])


def parse(s):
    return grammar.parse(s, semantics=BuiltinSemantics)


def test_ident():
    assert parse("foo") == TOKEN_TREE(IDENT("foo"))
    assert parse("foo ") == TOKEN_TREE(IDENT("foo"))
    assert parse(" foo") == TOKEN_TREE(IDENT("foo"))
    assert parse("foo42") == TOKEN_TREE(IDENT("foo42"))
    assert parse("foo_bar") == TOKEN_TREE(IDENT("foo_bar"))
    assert parse("_42") == TOKEN_TREE(IDENT("_42"))


def test_punct():
    assert parse(">") == TOKEN_TREE(PUNCT(">"))
    assert parse("+") == TOKEN_TREE(PUNCT("+"))


def test_literal():
    assert parse("42") == TOKEN_TREE(LITERAL("42"))
    assert parse(" 42") == TOKEN_TREE(LITERAL("42"))
    assert parse("42 ") == TOKEN_TREE(LITERAL("42"))
    assert parse(".42") == TOKEN_TREE(LITERAL(".42"))
    assert parse("42.") == TOKEN_TREE(LITERAL("42."))
    assert parse("42.42") == TOKEN_TREE(LITERAL("42.42"))
    assert parse("0x4_2.4_2u8") == TOKEN_TREE(LITERAL("0x4_2.4_2u8"))
    assert parse("0x42") == TOKEN_TREE(LITERAL("0x42"))
    assert parse("0x_42") == TOKEN_TREE(LITERAL("0x_42"))
    assert parse("0b_10101010") == TOKEN_TREE(LITERAL("0b_10101010"))
    assert parse("0b_1_0_1_0_1_0_1_0") == TOKEN_TREE(LITERAL("0b_1_0_1_0_1_0_1_0"))


def test_token_tree():
    assert parse(" (42)") == TOKEN_TREE(("(", [TOKEN_TREE(LITERAL("42"))], ")"))
    assert parse("(42)") == TOKEN_TREE(("(", [TOKEN_TREE(LITERAL("42"))], ")"))
    assert parse("( 42 )") == TOKEN_TREE(("(", [TOKEN_TREE(LITERAL("42"))], ")"))
    assert parse("(42 foo)") == TOKEN_TREE(
        ("(", [TOKEN_TREE(LITERAL("42")), TOKEN_TREE(IDENT("foo"))], ")")
    )
    assert parse("(42 { foo bar } )") == TOKEN_TREE(
        (
            "(",
            [
                TOKEN_TREE(LITERAL("42")),
                TOKEN_TREE(
                    tokens=(
                        "{",
                        [
                            TOKEN_TREE(tokens=IDENT(ident="foo")),
                            TOKEN_TREE(tokens=IDENT(ident="bar")),
                        ],
                        "}",
                    )
                ),
            ],
            ")",
        )
    )
