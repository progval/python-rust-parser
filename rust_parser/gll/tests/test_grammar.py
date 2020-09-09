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

import pytest

from ..tokens import SimpleToken, Name, String
from ..grammar import parse_gll, Alternation, Concatenation, Grammar, StringLiteral


def test_trivial_rule():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foo"),
            SimpleToken.COLON,
            String("foo"),
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(rules={"Value": {"Foo": StringLiteral(string="foo")}})


def test_two_rules():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foo"),
            SimpleToken.COLON,
            String("foo"),
            SimpleToken.PIPE,
            Name("Bar"),
            SimpleToken.COLON,
            String("bar"),
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                "Foo": StringLiteral(string="foo"),
                "Bar": StringLiteral(string="bar"),
            }
        }
    )


def test_concatenation():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foobar"),
            SimpleToken.COLON,
            SimpleToken.GROUP_START,
            String("foo"),
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                "Foobar": Concatenation(
                    items=[StringLiteral(string="foo"), StringLiteral(string="bar")]
                )
            }
        }
    )


def test_alternation():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foobar"),
            SimpleToken.COLON,
            SimpleToken.GROUP_START,
            String("foo"),
            SimpleToken.PIPE,
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                "Foobar": Alternation(
                    items=[StringLiteral(string="foo"), StringLiteral(string="bar")]
                )
            }
        }
    )


def test_two_symbols():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foo"),
            SimpleToken.COLON,
            String("foo"),
            SimpleToken.SEMICOLON,
            Name("Value2"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Bar"),
            SimpleToken.COLON,
            String("bar"),
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {"Foo": StringLiteral(string="foo")},
            "Value2": {"Bar": StringLiteral(string="bar")},
        }
    )
