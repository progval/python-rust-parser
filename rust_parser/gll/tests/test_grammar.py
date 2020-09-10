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
from ..grammar import (
    parse_gll,
    Alternation,
    Concatenation,
    Grammar,
    GllParseError,
    LabeledNode,
    Option,
    Repeated,
    StringLiteral,
)


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


def test_concatenation_and_alternation():
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
            String("baz"),
            SimpleToken.GROUP_END,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                "Foobar": Alternation(
                    items=[
                        StringLiteral(string="foo"),
                        Concatenation(
                            [StringLiteral(string="bar"), StringLiteral(string="baz")]
                        ),
                    ]
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


def test_alternation_groups():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foobar"),
            SimpleToken.COLON,
            SimpleToken.GROUP_START,
            SimpleToken.GROUP_START,
            String("foo"),
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.PIPE,
            SimpleToken.GROUP_START,
            String("baz"),
            String("qux"),
            SimpleToken.GROUP_END,
            SimpleToken.GROUP_END,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                "Foobar": Alternation(
                    items=[
                        Concatenation(
                            [StringLiteral(string="foo"), StringLiteral(string="bar")]
                        ),
                        Concatenation(
                            [StringLiteral(string="baz"), StringLiteral(string="qux")]
                        ),
                    ]
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


def test_duplicates():
    with pytest.raises(GllParseError, match="Duplicate symbol: Value"):
        parse_gll(
            [
                Name("Value"),
                SimpleToken.EQUAL,
                SimpleToken.PIPE,
                Name("Foo"),
                SimpleToken.COLON,
                String("foo"),
                SimpleToken.SEMICOLON,
                Name("Value"),
                SimpleToken.EQUAL,
                SimpleToken.PIPE,
                Name("Bar"),
                SimpleToken.COLON,
                String("bar"),
                SimpleToken.SEMICOLON,
            ]
        )

    with pytest.raises(GllParseError, match="Duplicate rule for symbol Value: Foo"):
        parse_gll(
            [
                Name("Value"),
                SimpleToken.EQUAL,
                SimpleToken.PIPE,
                Name("Foo"),
                SimpleToken.COLON,
                String("foo"),
                SimpleToken.PIPE,
                Name("Foo"),
                SimpleToken.COLON,
                String("bar"),
                SimpleToken.SEMICOLON,
            ]
        )


def test_anonymous_rule():
    assert parse_gll(
        [Name("Value"), SimpleToken.EQUAL, String("foo"), SimpleToken.SEMICOLON]
    ) == Grammar(rules={"Value": {None: StringLiteral(string="foo")}})

    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.GROUP_START,
            String("foo"),
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                None: Concatenation(
                    [StringLiteral(string="foo"), StringLiteral(string="bar")]
                )
            }
        }
    )


def test_option():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            String("foo"),
            SimpleToken.QUESTION_MARK,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(rules={"Value": {None: Option(StringLiteral(string="foo"))}})


def test_option_group():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.GROUP_START,
            String("foo"),
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.QUESTION_MARK,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                None: Option(
                    Concatenation(
                        [StringLiteral(string="foo"), StringLiteral(string="bar")]
                    )
                )
            }
        }
    )


def test_repeat():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            String("foo"),
            SimpleToken.STAR,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={"Value": {None: Repeated(0, StringLiteral(string="foo"), None, False)}}
    )

    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            String("foo"),
            SimpleToken.PLUS,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={"Value": {None: Repeated(1, StringLiteral(string="foo"), None, False)}}
    )


def test_repeated_group():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.GROUP_START,
            String("foo"),
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.STAR,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                None: Repeated(
                    0,
                    Concatenation(
                        [StringLiteral(string="foo"), StringLiteral(string="bar")]
                    ),
                    None,
                    False,
                )
            }
        }
    )

    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.GROUP_START,
            String("foo"),
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.PLUS,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                None: Repeated(
                    1,
                    Concatenation(
                        [StringLiteral(string="foo"), StringLiteral(string="bar")]
                    ),
                    None,
                    False,
                )
            }
        }
    )


def test_repeat_separator():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            String("foo"),
            SimpleToken.STAR,
            SimpleToken.PERCENT,
            String("bar"),
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={"Value": {None: Repeated(0, StringLiteral(string="foo"), "bar", False)}}
    )

    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            String("foo"),
            SimpleToken.PLUS,
            SimpleToken.PERCENT,
            String("bar"),
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={"Value": {None: Repeated(1, StringLiteral(string="foo"), "bar", False)}}
    )


def test_repeated_group_separator():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.GROUP_START,
            String("foo"),
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.STAR,
            SimpleToken.PERCENT,
            String("baz"),
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                None: Repeated(
                    0,
                    Concatenation(
                        [StringLiteral(string="foo"), StringLiteral(string="bar")]
                    ),
                    "baz",
                    False,
                )
            }
        }
    )

    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.GROUP_START,
            String("foo"),
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.PLUS,
            SimpleToken.PERCENT,
            String("baz"),
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                None: Repeated(
                    1,
                    Concatenation(
                        [StringLiteral(string="foo"), StringLiteral(string="bar")]
                    ),
                    "baz",
                    False,
                )
            }
        }
    )


def test_repeat_separator_trailing():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            String("foo"),
            SimpleToken.STAR,
            SimpleToken.DOUBLE_PERCENT,
            String("bar"),
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={"Value": {None: Repeated(0, StringLiteral(string="foo"), "bar", True)}}
    )


def test_label():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foobar"),
            SimpleToken.COLON,
            SimpleToken.GROUP_START,
            Name("field1"),
            SimpleToken.COLON,
            String("foo"),
            Name("field2"),
            SimpleToken.COLON,
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                "Foobar": Concatenation(
                    items=[
                        LabeledNode("field1", StringLiteral(string="foo")),
                        LabeledNode("field2", StringLiteral(string="bar")),
                    ]
                )
            }
        }
    )

    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foobar"),
            SimpleToken.COLON,
            Name("field0"),
            SimpleToken.COLON,
            SimpleToken.GROUP_START,
            String("foo"),
            Name("field2"),
            SimpleToken.COLON,
            String("bar"),
            SimpleToken.GROUP_END,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                "Foobar": LabeledNode(
                    "field0",
                    Concatenation(
                        items=[
                            StringLiteral(string="foo"),
                            LabeledNode("field2", StringLiteral(string="bar")),
                        ]
                    ),
                )
            }
        }
    )


def test_label_repeated():
    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foobar"),
            SimpleToken.COLON,
            Name("field1"),
            SimpleToken.COLON,
            String("foo"),
            SimpleToken.STAR,
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                "Foobar": LabeledNode(
                    "field1", Repeated(0, StringLiteral(string="foo"), None, False)
                )
            }
        }
    )

    assert parse_gll(
        [
            Name("Value"),
            SimpleToken.EQUAL,
            SimpleToken.PIPE,
            Name("Foobar"),
            SimpleToken.COLON,
            Name("field1"),
            SimpleToken.COLON,
            String("foo"),
            SimpleToken.STAR,
            SimpleToken.PERCENT,
            String("bar"),
            SimpleToken.SEMICOLON,
        ]
    ) == Grammar(
        rules={
            "Value": {
                "Foobar": LabeledNode(
                    "field1", Repeated(0, StringLiteral(string="foo"), "bar", False)
                )
            }
        }
    )
