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

import textwrap

import pytest
import tatsu
from tatsu import exceptions

from .. import grammar as gll_grammar
from ..semantics import generate_semantics_code
from ..generate import generate_tatsu_grammar


def test_simple_grammar():
    grammar = gll_grammar.Grammar(rules={"Foo": gll_grammar.StringLiteral("foo")})
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import typing


        class Foo(str):
            @classmethod
            def from_ast(cls, ast):
                return cls(ast)


        class Semantics:
            def Foo(self, ast) -> Foo:
                return Foo.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()

    assert g.parse("foo", semantics=semantics) == "foo"
    with pytest.raises(exceptions.FailedToken):
        g.parse("bar", semantics=semantics)


def test_labeled_concatenation():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "foo_field", gll_grammar.StringLiteral("foo")
                    ),
                    gll_grammar.LabeledNode(
                        "bar_field",
                        gll_grammar.Option(gll_grammar.StringLiteral("bar")),
                    ),
                    gll_grammar.LabeledNode(
                        "baz_field", gll_grammar.StringLiteral("baz")
                    ),
                ]
            )
        }
    )
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import typing


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast):
                return cls(**ast)

            foo_field: str
            bar_field: typing.Optional[str]
            baz_field: str


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]

    assert g.parse("foo bar baz", semantics=semantics) == Main("foo", "bar", "baz")
    assert g.parse("foo baz", semantics=semantics) == Main("foo", None, "baz")
    with pytest.raises(exceptions.FailedToken):
        g.parse("foo", semantics=semantics)
    with pytest.raises(exceptions.FailedToken):
        g.parse("bar", semantics=semantics)


def test_labeled_alternation():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Alternation(
                [
                    gll_grammar.LabeledNode("Foo", gll_grammar.StringLiteral("foo")),
                    gll_grammar.LabeledNode("Bar", gll_grammar.StringLiteral("bar")),
                    gll_grammar.LabeledNode("Baz", gll_grammar.StringLiteral("baz")),
                ]
            )
        }
    )
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import typing


        @typing.sealed
        class Main:
            @staticmethod
            def from_ast(ast):
                ((variant_name, subtree),) = ast.items()
                cls = globals()[variant_name]
                assert issubclass(cls, Main)  # sealed
                return cls.from_ast(subtree)


        class Foo(str, Main):
            @classmethod
            def from_ast(cls, ast):
                return cls(ast)


        class Bar(str, Main):
            @classmethod
            def from_ast(cls, ast):
                return cls(ast)


        class Baz(str, Main):
            @classmethod
            def from_ast(cls, ast):
                return cls(ast)


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]
    Foo = namespace["Foo"]
    Bar = namespace["Bar"]
    Baz = namespace["Baz"]

    assert g.parse("foo", semantics=semantics) == Foo("foo")
    assert g.parse("bar", semantics=semantics) == Bar("bar")
    assert g.parse("baz", semantics=semantics) == Bar("baz")
    with pytest.raises(exceptions.FailedParse):
        g.parse("qux", semantics=semantics)
