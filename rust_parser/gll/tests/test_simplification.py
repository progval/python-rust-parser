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

from .. import grammar
from ..simplification import simplify_tree


def test_leaves():
    assert simplify_tree(grammar.Empty()) == grammar.Empty()

    assert simplify_tree(grammar.StringLiteral("foo")) == grammar.Empty()

    assert simplify_tree(grammar.SymbolName("Foo")) == grammar.SymbolName("Foo")


def test_labelednode():
    assert simplify_tree(
        grammar.LabeledNode("foo", grammar.Empty())
    ) == grammar.LabeledNode("foo", grammar.Empty())

    assert simplify_tree(
        grammar.LabeledNode("foo", grammar.StringLiteral("foo"))
    ) == grammar.LabeledNode("foo", grammar.Empty())

    assert simplify_tree(
        grammar.LabeledNode("foo", grammar.SymbolName("Foo"))
    ) == grammar.LabeledNode("foo", grammar.SymbolName("Foo"))


def test_concatenation():
    assert simplify_tree(grammar.Concatenation([])) == grammar.Empty()

    assert simplify_tree(grammar.Concatenation([grammar.Empty()])) == grammar.Empty()

    assert simplify_tree(
        grammar.Concatenation([grammar.SymbolName("Foo")])
    ) == grammar.SymbolName("Foo")

    assert simplify_tree(
        grammar.Concatenation([grammar.Empty(), grammar.SymbolName("Foo")])
    ) == grammar.SymbolName("Foo")

    assert simplify_tree(
        grammar.Concatenation([grammar.SymbolName("Foo"), grammar.SymbolName("Bar")])
    ) == grammar.Concatenation([grammar.SymbolName("Foo"), grammar.SymbolName("Bar")])


def test_alternation():
    assert simplify_tree(grammar.Alternation([grammar.Empty()])) == grammar.Empty()

    assert simplify_tree(
        grammar.Alternation([grammar.SymbolName("Foo")])
    ) == grammar.SymbolName("Foo")

    assert simplify_tree(
        grammar.Alternation([grammar.Empty(), grammar.SymbolName("Foo")])
    ) == grammar.Alternation([grammar.Empty(), grammar.SymbolName("Foo")])

    assert simplify_tree(
        grammar.Alternation([grammar.SymbolName("Foo"), grammar.SymbolName("Bar")])
    ) == grammar.Alternation([grammar.SymbolName("Foo"), grammar.SymbolName("Bar")])


def test_option():
    assert simplify_tree(grammar.Option(grammar.Empty())) == grammar.Option(
        grammar.Empty()
    )

    assert simplify_tree(
        grammar.Option(grammar.StringLiteral("foo"))
    ) == grammar.Option(grammar.Empty())

    assert simplify_tree(grammar.Option(grammar.SymbolName("Foo"))) == grammar.Option(
        grammar.SymbolName("Foo")
    )

    assert simplify_tree(
        grammar.Option(grammar.LabeledNode("foo", grammar.SymbolName("Foo")))
    ) == grammar.LabeledNode("foo", grammar.Option(grammar.SymbolName("Foo")))
