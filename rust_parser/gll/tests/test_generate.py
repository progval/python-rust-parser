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
from tatsu import compile
from tatsu import grammars as tatsu_grammars
from tatsu import exceptions

from .. import grammar as gll_grammar
from ..generate import generate_tatsu_grammar


def test_simple_grammar():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(rules={"Foo": {None: gll_grammar.StringLiteral("foo")}})
    )
    assert str(g) == str(compile("Foo = 'foo';"))

    assert g.parse("foo") == "foo"
    with pytest.raises(exceptions.FailedToken):
        g.parse("bar")

    g = generate_tatsu_grammar(
        gll_grammar.Grammar(rules={"Foo": {"Bar": gll_grammar.StringLiteral("foo")}})
    )
    assert str(g) == str(compile("Foo = Bar:'foo';"))

    assert g.parse("foo") == {"Bar": "foo"}
    with pytest.raises(exceptions.FailedParse):
        g.parse("bar")


def test_multiple_rules():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Foo": {
                    "Bar": gll_grammar.StringLiteral("bar"),
                    "Baz": gll_grammar.StringLiteral("baz"),
                }
            }
        )
    )
    assert str(g) == str(compile("Foo = Bar:'bar' | Baz:'baz';"))

    assert g.parse("bar") == {"Bar": "bar"}
    assert g.parse("baz") == {"Baz": "baz"}
    with pytest.raises(exceptions.FailedParse):
        g.parse("foo")


def test_alternation():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Alternation(
                        [
                            gll_grammar.StringLiteral("bar"),
                            gll_grammar.StringLiteral("baz"),
                        ]
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = 'bar' | 'baz';"))

    assert g.parse("bar") == "bar"
    assert g.parse("baz") == "baz"
    with pytest.raises(exceptions.FailedParse):
        g.parse("foo")


def test_multiple_symbols():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    "Bar": gll_grammar.SymbolName("SBar"),
                    "Baz": gll_grammar.SymbolName("SBaz"),
                },
                "SBar": {"Bar": gll_grammar.StringLiteral("bar")},
                "SBaz": {"Baz": gll_grammar.StringLiteral("baz")},
            }
        )
    )
    assert str(g) == str(
        compile("Main = Bar: SBar | Baz: SBaz; SBar = Bar: 'bar'; SBaz = Baz: 'baz';")
    )

    assert g.parse("bar") == {"Bar": {"Bar": "bar"}}
    assert g.parse("baz") == {"Baz": {"Baz": "baz"}}
    with pytest.raises(exceptions.FailedParse):
        g.parse("foo")


def test_concatenation():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Concatenation(
                        [
                            gll_grammar.StringLiteral("bar"),
                            gll_grammar.StringLiteral("baz"),
                        ]
                    )
                }
            }
        )
    )
    print(repr(g.rules[0].exp.__dict__))
    assert str(g) == str(compile("Main = 'bar' 'baz';"))

    assert g.parse("bar baz") == ("bar", "baz")
    with pytest.raises(exceptions.FailedParse):
        g.parse("foo")
    with pytest.raises(exceptions.FailedParse):
        g.parse("bar")
    with pytest.raises(exceptions.FailedParse):
        g.parse("baz")
    with pytest.raises(exceptions.FailedParse):
        g.parse("barbaz")


def test_option():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Concatenation(
                        [
                            gll_grammar.StringLiteral("bar"),
                            gll_grammar.Option(gll_grammar.StringLiteral("baz")),
                        ]
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = 'bar' ['baz'];"))

    assert g.parse("bar") == "bar"
    assert g.parse("bar baz") == ("bar", "baz")
    with pytest.raises(exceptions.FailedParse):
        g.parse("foo")
    with pytest.raises(exceptions.FailedParse):
        g.parse("baz")
    with pytest.raises(exceptions.FailedParse):
        g.parse("barbaz")


def test_labels():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Concatenation(
                        [
                            gll_grammar.LabeledNode(
                                "l1", gll_grammar.StringLiteral("bar")
                            ),
                            gll_grammar.LabeledNode(
                                "l2",
                                gll_grammar.Option(gll_grammar.StringLiteral("baz")),
                            ),
                        ]
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = l1:'bar' l2:['baz'];"))

    assert g.parse("bar") == {"l1": "bar", "l2": None}
    assert g.parse("bar baz") == {"l1": "bar", "l2": "baz"}
    with pytest.raises(exceptions.FailedParse):
        g.parse("foo")
    with pytest.raises(exceptions.FailedParse):
        g.parse("baz")
    with pytest.raises(exceptions.FailedParse):
        g.parse("barbaz")


def test_label_in_option():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Concatenation(
                        [
                            gll_grammar.LabeledNode(
                                "l1", gll_grammar.StringLiteral("bar")
                            ),
                            gll_grammar.Option(
                                gll_grammar.LabeledNode(
                                    "l2", gll_grammar.StringLiteral("baz")
                                )
                            ),
                        ]
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = l1:'bar' [l2:'baz'];"))

    assert g.parse("bar") == {"l1": "bar"}
    assert g.parse("bar baz") == {"l1": "bar", "l2": "baz"}
    with pytest.raises(exceptions.FailedParse):
        g.parse("foo")
    with pytest.raises(exceptions.FailedParse):
        g.parse("baz")
    with pytest.raises(exceptions.FailedParse):
        g.parse("barbaz")


def test_repeat():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Repeated(
                        False, gll_grammar.StringLiteral("foo"), None, False
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = {'foo'}*;"))

    assert g.parse("") == []
    assert g.parse("foo") == ["foo"]
    assert g.parse("foo foo") == ["foo", "foo"]
    assert g.parse("baz") == []


def test_repeat_positive():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Repeated(
                        True, gll_grammar.StringLiteral("foo"), None, False
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = {'foo'}+;"))

    assert g.parse("foo") == ["foo"]
    assert g.parse("foo foo") == ["foo", "foo"]
    with pytest.raises(exceptions.FailedParse):
        assert g.parse("") == []
    with pytest.raises(exceptions.FailedParse):
        assert g.parse("baz") == []


def test_repeat_separator():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Repeated(
                        False, gll_grammar.StringLiteral("foo"), ",", False
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = ','%{'foo'}*;"))

    assert g.parse("") == []
    assert g.parse("foo") == ["foo"]
    assert g.parse("foo foo") == ["foo"]
    assert g.parse("foo, foo") == ["foo", ",", "foo"]
    assert g.parse("foo, foo foo") == ["foo", ",", "foo"]
    assert g.parse("baz") == []
    with pytest.raises(exceptions.FailedCut):
        g.parse("foo, foo,")


def test_repeat_positive_separator():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Repeated(
                        True, gll_grammar.StringLiteral("foo"), ",", False
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = ','%{'foo'}+;"))

    assert g.parse("foo") == ["foo"]
    assert g.parse("foo foo") == ["foo"]
    assert g.parse("foo, foo") == ["foo", ",", "foo"]
    assert g.parse("foo, foo foo") == ["foo", ",", "foo"]
    with pytest.raises(exceptions.FailedParse):
        g.parse("")
    with pytest.raises(exceptions.FailedParse):
        g.parse("baz")
    with pytest.raises(exceptions.FailedCut):
        g.parse("foo, foo,")


def test_repeat_separator_trailing():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Repeated(
                        False, gll_grammar.StringLiteral("foo"), ",", True
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = {'foo' ','}* ['foo'];"))

    assert g.parse("") == []
    assert g.parse("foo") == ([], "foo")
    assert g.parse("foo foo") == ([], "foo")
    assert g.parse("foo, foo") == ([["foo", ","]], "foo")
    assert g.parse("foo, foo,") == [["foo", ","], ["foo", ","]]
    assert g.parse("foo, foo foo") == ([["foo", ","]], "foo")
    assert g.parse("baz") == []


def test_repeat_positive_separator_trailing():
    g = generate_tatsu_grammar(
        gll_grammar.Grammar(
            rules={
                "Main": {
                    None: gll_grammar.Repeated(
                        True, gll_grammar.StringLiteral("foo"), ",", True
                    )
                }
            }
        )
    )
    assert str(g) == str(compile("Main = 'foo' {',' 'foo'}* [','];"))

    assert g.parse("foo") == ("foo", [])
    assert g.parse("foo foo") == ("foo", [])
    assert g.parse("foo, foo") == ("foo", [[",", "foo"]])
    assert g.parse("foo, foo,") == ("foo", [[",", "foo"]], ",")
    assert g.parse("foo, foo foo") == ("foo", [[",", "foo"]])
    with pytest.raises(exceptions.FailedParse):
        assert g.parse("") == []
    with pytest.raises(exceptions.FailedParse):
        assert g.parse("baz") == []
