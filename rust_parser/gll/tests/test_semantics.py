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
from ..semantics import generate_semantics_code, Maybe
from ..generate import generate_tatsu_grammar
from ..builtin_rules import BUILTIN_RULES, IDENT


def test_qualname_maybe():
    Main = Maybe[str]

    assert Main.__qualname__ == "Maybe[str]"
    assert Main.Just.__qualname__ == "Maybe[str].Just"
    assert Main.Nothing.__qualname__ == "Maybe[str].Nothing"


def test_simple_grammar():
    grammar = gll_grammar.Grammar(rules={"Foo": gll_grammar.StringLiteral("foo")})
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics


        class Foo(str):
            @classmethod
            def from_ast(cls, ast: str) -> Foo:
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
                        "baz_field",
                        gll_grammar.Option(gll_grammar.StringLiteral("baz")),
                    ),
                ]
            )
        }
    )
    g = generate_tatsu_grammar(grammar)

    # we need a different grammar for generate_semantics_code to trigger the
    # boolean case
    grammar.rules["Main"].items[2] = gll_grammar.LabeledNode(
        "baz_field", gll_grammar.Option(gll_grammar.Empty())
    )

    sc = generate_semantics_code(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(
                    foo_field=str(ast["foo_field"]),
                    bar_field=str(ast["bar_field"]) if ast["bar_field"] else None,
                    baz_field=bool(ast["baz_field"]),
                )

            foo_field: str
            bar_field: typing.Optional[str]
            baz_field: bool


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]

    assert g.parse("foo bar baz", semantics=semantics) == Main("foo", "bar", True)
    assert g.parse("foo baz", semantics=semantics) == Main("foo", None, True)
    assert g.parse("foo bar", semantics=semantics) == Main("foo", "bar", False)
    assert g.parse("foo", semantics=semantics) == Main("foo", None, False)
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
        import enum
        import typing

        import rust_parser.gll.semantics


        @typing.sealed
        class Main(metaclass=rust_parser.gll.semantics.ADT):
            _variants = {"Foo": "Foo", "Bar": "Bar", "Baz": "Baz"}

            class Foo(str):
                @classmethod
                def from_ast(cls, ast: str) -> Foo:
                    return cls(ast)

            class Bar(str):
                @classmethod
                def from_ast(cls, ast: str) -> Bar:
                    return cls(ast)

            class Baz(str):
                @classmethod
                def from_ast(cls, ast: str) -> Baz:
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

    assert issubclass(Main.Foo, Main)

    assert g.parse("foo", semantics=semantics) == Main.Foo("foo")
    assert isinstance(g.parse("foo", semantics=semantics), Main.Foo)
    assert g.parse("bar", semantics=semantics) == Main.Bar("bar")
    assert isinstance(g.parse("bar", semantics=semantics), Main.Bar)
    assert g.parse("baz", semantics=semantics) == Main.Baz("baz")
    assert isinstance(g.parse("baz", semantics=semantics), Main.Baz)
    with pytest.raises(exceptions.FailedParse):
        g.parse("qux", semantics=semantics)


def test_labeled_alternation_labeled_alternation():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Alternation(
                [
                    gll_grammar.LabeledNode(
                        "Foo",
                        gll_grammar.Concatenation(
                            [
                                gll_grammar.LabeledNode(
                                    "foo1", gll_grammar.StringLiteral("one")
                                ),
                                gll_grammar.LabeledNode(
                                    "foo2", gll_grammar.StringLiteral("two")
                                ),
                            ]
                        ),
                    ),
                    gll_grammar.LabeledNode(
                        "Bar",
                        gll_grammar.Concatenation(
                            [
                                gll_grammar.LabeledNode(
                                    "bar1", gll_grammar.StringLiteral("two")
                                ),
                                gll_grammar.LabeledNode(
                                    "bar2", gll_grammar.StringLiteral("three")
                                ),
                            ]
                        ),
                    ),
                    gll_grammar.LabeledNode(
                        "Baz",
                        gll_grammar.Concatenation(
                            [
                                gll_grammar.LabeledNode(
                                    "baz1", gll_grammar.StringLiteral("three")
                                ),
                                gll_grammar.LabeledNode(
                                    "baz2", gll_grammar.StringLiteral("four")
                                ),
                            ]
                        ),
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
        import enum
        import typing

        import rust_parser.gll.semantics


        @typing.sealed
        class Main(metaclass=rust_parser.gll.semantics.ADT):
            _variants = {"Foo": "Foo", "Bar": "Bar", "Baz": "Baz"}

            @dataclasses.dataclass
            class Foo:
                @classmethod
                def from_ast(cls, ast) -> Foo:
                    return cls(
                        foo1=str(ast["foo1"]),
                        foo2=str(ast["foo2"]),
                    )

                foo1: str
                foo2: str

            @dataclasses.dataclass
            class Bar:
                @classmethod
                def from_ast(cls, ast) -> Bar:
                    return cls(
                        bar1=str(ast["bar1"]),
                        bar2=str(ast["bar2"]),
                    )

                bar1: str
                bar2: str

            @dataclasses.dataclass
            class Baz:
                @classmethod
                def from_ast(cls, ast) -> Baz:
                    return cls(
                        baz1=str(ast["baz1"]),
                        baz2=str(ast["baz2"]),
                    )

                baz1: str
                baz2: str


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]

    assert issubclass(Main.Foo, Main)

    assert g.parse("one two", semantics=semantics) == Main.Foo("one", "two")
    assert isinstance(g.parse("one two", semantics=semantics), Main.Foo)
    assert g.parse("two three", semantics=semantics) == Main.Bar("two", "three")
    assert isinstance(g.parse("two three", semantics=semantics), Main.Bar)
    assert g.parse("three four", semantics=semantics) == Main.Baz("three", "four")
    assert isinstance(g.parse("three four", semantics=semantics), Main.Baz)
    with pytest.raises(exceptions.FailedParse):
        g.parse("qux", semantics=semantics)


def test_option():
    grammar = gll_grammar.Grammar(
        rules={"Main": gll_grammar.Option(gll_grammar.StringLiteral("foo"))}
    )
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics


        class MainInner(str):
            @classmethod
            def from_ast(cls, ast: str) -> MainInner:
                return cls(ast)


        Main = rust_parser.gll.semantics.Maybe[MainInner]


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]

    assert issubclass(Main.Nothing, Main)
    assert issubclass(Main.Just, Main)

    assert g.parse("", semantics=semantics) == Main.Nothing()
    assert isinstance(g.parse("", semantics=semantics), Main.Nothing)
    assert g.parse("foo", semantics=semantics) == Main.Just("foo")
    assert isinstance(g.parse("foo", semantics=semantics), Main.Just)


def test_empty_in_concatenation():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "foo_field", gll_grammar.StringLiteral("foo")
                    ),
                    gll_grammar.LabeledNode("bar_field", gll_grammar.Empty()),
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
        import enum
        import typing

        import rust_parser.gll.semantics


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(
                    foo_field=str(ast["foo_field"]),
                    bar_field=None,
                    baz_field=str(ast["baz_field"]),
                )

            foo_field: str
            bar_field: None
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

    assert g.parse("foo baz", semantics=semantics) == Main("foo", None, "baz")
    with pytest.raises(exceptions.FailedToken):
        g.parse("foo", semantics=semantics)
    with pytest.raises(exceptions.FailedToken):
        g.parse("baz", semantics=semantics)


def test_sequence_in_concatenation():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "foo_field", gll_grammar.StringLiteral("foo")
                    ),
                    gll_grammar.LabeledNode(
                        "bar_field",
                        gll_grammar.Repeated(
                            0, gll_grammar.StringLiteral("bar"), None, False
                        ),
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
        import enum
        import typing

        import rust_parser.gll.semantics


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(
                    foo_field=str(ast["foo_field"]),
                    bar_field=[str(ast_bar_field_item) for ast_bar_field_item in ast["bar_field"]],
                    baz_field=str(ast["baz_field"]),
                )

            foo_field: str
            bar_field: typing.List[str]
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

    assert g.parse("foo baz", semantics=semantics) == Main("foo", [], "baz")
    assert g.parse("foo bar baz", semantics=semantics) == Main("foo", ["bar"], "baz")
    assert g.parse("foo bar bar baz", semantics=semantics) == Main(
        "foo", ["bar", "bar"], "baz"
    )
    with pytest.raises(exceptions.FailedToken):
        g.parse("foo", semantics=semantics)
    with pytest.raises(exceptions.FailedToken):
        g.parse("baz", semantics=semantics)


def test_simple_alternation():
    """An alternation of only empty subtrees, meaning it can be serialialized as
    an Enum rather than an ADT."""
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Alternation(
                [
                    gll_grammar.LabeledNode("Foo", gll_grammar.Empty()),
                    gll_grammar.LabeledNode("Bar", gll_grammar.Empty()),
                ]
            )
        }
    )
    sc = generate_semantics_code(grammar)
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Alternation(
                [
                    gll_grammar.LabeledNode("Foo", gll_grammar.StringLiteral("foo")),
                    gll_grammar.LabeledNode("Bar", gll_grammar.StringLiteral("bar")),
                ]
            )
        }
    )
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics


        @enum.unique
        class Main(enum.Enum):
            @staticmethod
            def _variants():
                return frozenset(["Foo", "Bar"])

            @classmethod
            def from_ast(cls, ast) -> Main:
                (variant,) = set(ast) & cls._variants()
                return cls(variant)

            FOO = "Foo"
            BAR = "Bar"


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]

    assert g.parse("foo", semantics=semantics) == Main.FOO
    assert g.parse("bar", semantics=semantics) == Main.BAR
    with pytest.raises(exceptions.FailedParse):
        g.parse("baz", semantics=semantics)


def test_alternation_with_anonymous_variant_in_concatenation():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "foo_field", gll_grammar.StringLiteral("foo")
                    ),
                    gll_grammar.LabeledNode(
                        "bar_field",
                        gll_grammar.Alternation(
                            [
                                gll_grammar.LabeledNode(
                                    "Bar1", gll_grammar.StringLiteral("bar1")
                                ),
                                gll_grammar.StringLiteral("bar2"),
                            ]
                        ),
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
        import enum
        import typing

        import rust_parser.gll.semantics


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(
                    foo_field=str(ast["foo_field"]),
                    bar_field=(lambda constructors: constructors.get((list(set(constructors) & set(ast)) or [None])[0], lambda: None))(dict(Bar1=(lambda: str(ast["Bar1"])), Variant1=(lambda: str(ast["Variant1"]))))(),
                )

            foo_field: str
            bar_field: typing.Union[str, None]


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]

    assert g.parse("foo bar1 baz", semantics=semantics) == Main("foo", "bar1")
    assert g.parse("foo bar2 baz", semantics=semantics) == Main("foo", None)
    with pytest.raises(exceptions.FailedParse):
        g.parse("foo baz", semantics=semantics)


def test_alternation_in_concatenation():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "foo_field", gll_grammar.StringLiteral("foo")
                    ),
                    gll_grammar.LabeledNode(
                        "bar_field",
                        gll_grammar.Alternation(
                            [
                                gll_grammar.LabeledNode(
                                    "Bar1", gll_grammar.StringLiteral("bar1")
                                ),
                                gll_grammar.LabeledNode(
                                    "Bar2", gll_grammar.StringLiteral("bar2")
                                ),
                            ]
                        ),
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
        import enum
        import typing

        import rust_parser.gll.semantics


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(
                    foo_field=str(ast["foo_field"]),
                    bar_field=(lambda constructors: constructors.get((list(set(constructors) & set(ast)) or [None])[0], lambda: None))(dict(Bar1=(lambda: str(ast["Bar1"])), Bar2=(lambda: str(ast["Bar2"]))))(),
                    baz_field=str(ast["baz_field"]),
                )

            foo_field: str
            bar_field: typing.Union[str, str]
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

    assert g.parse("foo bar1 baz", semantics=semantics) == Main("foo", "bar1", "baz")
    assert g.parse("foo bar2 baz", semantics=semantics) == Main("foo", "bar2", "baz")
    with pytest.raises(exceptions.FailedParse):
        g.parse("foo baz", semantics=semantics)


def test_rule_reference():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "foo_field", gll_grammar.StringLiteral("foo")
                    ),
                    gll_grammar.LabeledNode("bar_field", gll_grammar.SymbolName("Bar")),
                    gll_grammar.LabeledNode(
                        "baz_field", gll_grammar.StringLiteral("baz")
                    ),
                ]
            ),
            "Bar": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "bar1_field", gll_grammar.StringLiteral("bar1")
                    ),
                    gll_grammar.LabeledNode(
                        "bar2_field", gll_grammar.StringLiteral("bar2")
                    ),
                ]
            ),
        }
    )
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(
                    foo_field=str(ast["foo_field"]),
                    bar_field=ast["bar_field"],
                    baz_field=str(ast["baz_field"]),
                )

            foo_field: str
            bar_field: Bar
            baz_field: str


        @dataclasses.dataclass
        class Bar:
            @classmethod
            def from_ast(cls, ast) -> Bar:
                return cls(
                    bar1_field=str(ast["bar1_field"]),
                    bar2_field=str(ast["bar2_field"]),
                )

            bar1_field: str
            bar2_field: str


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)

            def Bar(self, ast) -> Bar:
                return Bar.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]
    Bar = namespace["Bar"]

    assert g.parse("foo bar1 bar2 baz", semantics=semantics) == Main(
        "foo", Bar("bar1", "bar2"), "baz"
    )


def test_root_repeated_rule_reference():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Alternation(
                [
                    gll_grammar.LabeledNode("Foo", gll_grammar.StringLiteral("foo")),
                    gll_grammar.LabeledNode(
                        "Bar",
                        gll_grammar.Repeated(
                            0, gll_grammar.SymbolName("Bar"), None, False
                        ),
                    ),
                ]
            ),
            "Bar": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "bar1_field", gll_grammar.StringLiteral("bar1")
                    ),
                    gll_grammar.LabeledNode(
                        "bar2_field", gll_grammar.StringLiteral("bar2")
                    ),
                ]
            ),
        }
    )
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics


        @typing.sealed
        class Main(metaclass=rust_parser.gll.semantics.ADT):
            _variants = {"Foo": "Foo", "Bar": "Bar_"}

            class Foo(str):
                @classmethod
                def from_ast(cls, ast: str) -> Foo:
                    return cls(ast)

            @dataclasses.dataclass
            class Bar_Inner:
                inner: Bar

                @classmethod
                def from_ast(cls, ast) -> Bar_Inner:
                    return cls(inner=ast)

            class Bar_(typing.List[Bar_Inner]):
                @classmethod
                def from_ast(cls, ast) -> Bar_:
                    return cls(list(map(cls.Bar_Inner.from_ast, ast)))


        @dataclasses.dataclass
        class Bar:
            @classmethod
            def from_ast(cls, ast) -> Bar:
                return cls(
                    bar1_field=str(ast["bar1_field"]),
                    bar2_field=str(ast["bar2_field"]),
                )

            bar1_field: str
            bar2_field: str


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)

            def Bar(self, ast) -> Bar:
                return Bar.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]
    Bar = namespace["Bar"]

    assert g.parse("foo", semantics=semantics) == Main.Foo("foo")
    assert g.parse("bar1 bar2", semantics=semantics) == Main.Bar_(
        [Main.Bar_Inner(Bar("bar1", "bar2"))]
    )
    assert g.parse("bar1 bar2 bar1 bar2", semantics=semantics) == Main.Bar_(
        [Main.Bar_Inner(Bar("bar1", "bar2")), Main.Bar_Inner(Bar("bar1", "bar2"))]
    )


def test_root_repeated_rule_reference_with_separator():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Alternation(
                [
                    gll_grammar.LabeledNode("Foo", gll_grammar.StringLiteral("foo")),
                    gll_grammar.LabeledNode(
                        "Bar",
                        gll_grammar.Repeated(
                            0, gll_grammar.SymbolName("Bar"), "::", False
                        ),
                    ),
                ]
            ),
            "Bar": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "bar1_field", gll_grammar.StringLiteral("bar1")
                    ),
                    gll_grammar.LabeledNode(
                        "bar2_field", gll_grammar.StringLiteral("bar2")
                    ),
                ]
            ),
        }
    )
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics


        @typing.sealed
        class Main(metaclass=rust_parser.gll.semantics.ADT):
            _variants = {"Foo": "Foo", "Bar": "Bar_"}

            class Foo(str):
                @classmethod
                def from_ast(cls, ast: str) -> Foo:
                    return cls(ast)

            @dataclasses.dataclass
            class Bar_Inner:
                inner: Bar

                @classmethod
                def from_ast(cls, ast) -> Bar_Inner:
                    return cls(inner=ast)

            class Bar_(typing.List[Bar_Inner]):
                @classmethod
                def from_ast(cls, ast) -> Bar_:
                    return cls(list(map(cls.Bar_Inner.from_ast, ast))[0::2])


        @dataclasses.dataclass
        class Bar:
            @classmethod
            def from_ast(cls, ast) -> Bar:
                return cls(
                    bar1_field=str(ast["bar1_field"]),
                    bar2_field=str(ast["bar2_field"]),
                )

            bar1_field: str
            bar2_field: str


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)

            def Bar(self, ast) -> Bar:
                return Bar.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]
    Bar = namespace["Bar"]

    assert g.parse("foo", semantics=semantics) == Main.Foo("foo")
    assert g.parse("bar1 bar2", semantics=semantics) == Main.Bar_(
        [Main.Bar_Inner(Bar("bar1", "bar2"))]
    )
    assert g.parse("bar1 bar2 :: bar1 bar2", semantics=semantics) == Main.Bar_(
        [Main.Bar_Inner(Bar("bar1", "bar2")), Main.Bar_Inner(Bar("bar1", "bar2"))]
    )


def test_nested_repeated_rule_reference():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "foo_field", gll_grammar.StringLiteral("foo")
                    ),
                    gll_grammar.LabeledNode(
                        "bar_field",
                        gll_grammar.Repeated(
                            0, gll_grammar.SymbolName("Bar"), None, False
                        ),
                    ),
                ]
            ),
            "Bar": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "bar1_field", gll_grammar.StringLiteral("bar1")
                    ),
                    gll_grammar.LabeledNode(
                        "bar2_field", gll_grammar.StringLiteral("bar2")
                    ),
                ]
            ),
        }
    )
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(
                    foo_field=str(ast["foo_field"]),
                    bar_field=[ast_bar_field_item for ast_bar_field_item in ast["bar_field"]],
                )

            foo_field: str
            bar_field: typing.List[Bar]


        @dataclasses.dataclass
        class Bar:
            @classmethod
            def from_ast(cls, ast) -> Bar:
                return cls(
                    bar1_field=str(ast["bar1_field"]),
                    bar2_field=str(ast["bar2_field"]),
                )

            bar1_field: str
            bar2_field: str


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)

            def Bar(self, ast) -> Bar:
                return Bar.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]
    Bar = namespace["Bar"]

    assert g.parse("foo", semantics=semantics) == Main("foo", [])
    assert g.parse("foo bar1 bar2", semantics=semantics) == Main(
        "foo", [Bar("bar1", "bar2")]
    )
    assert g.parse("foo bar1 bar2 bar1 bar2", semantics=semantics) == Main(
        "foo", [Bar("bar1", "bar2"), Bar("bar1", "bar2")]
    )


def test_nested_repeated_rule_reference_with_separator():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "foo_field", gll_grammar.StringLiteral("foo")
                    ),
                    gll_grammar.LabeledNode(
                        "bar_field",
                        gll_grammar.Repeated(
                            0, gll_grammar.SymbolName("Bar"), "::", False
                        ),
                    ),
                ]
            ),
            "Bar": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode(
                        "bar1_field", gll_grammar.StringLiteral("bar1")
                    ),
                    gll_grammar.LabeledNode(
                        "bar2_field", gll_grammar.StringLiteral("bar2")
                    ),
                ]
            ),
        }
    )
    sc = generate_semantics_code(grammar)
    g = generate_tatsu_grammar(grammar)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(
                    foo_field=str(ast["foo_field"]),
                    bar_field=[ast_bar_field_item for ast_bar_field_item in ast["bar_field"]][0::2],
                )

            foo_field: str
            bar_field: typing.List[Bar]


        @dataclasses.dataclass
        class Bar:
            @classmethod
            def from_ast(cls, ast) -> Bar:
                return cls(
                    bar1_field=str(ast["bar1_field"]),
                    bar2_field=str(ast["bar2_field"]),
                )

            bar1_field: str
            bar2_field: str


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)

            def Bar(self, ast) -> Bar:
                return Bar.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]
    Bar = namespace["Bar"]

    assert g.parse("foo", semantics=semantics) == Main("foo", [])
    assert g.parse("foo bar1 bar2", semantics=semantics) == Main(
        "foo", [Bar("bar1", "bar2")]
    )
    assert g.parse("foo bar1 bar2 :: bar1 bar2", semantics=semantics) == Main(
        "foo", [Bar("bar1", "bar2"), Bar("bar1", "bar2")]
    )


def test_option_in_root_alternation():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Alternation(
                items=[
                    gll_grammar.LabeledNode(
                        name="Foo", item=gll_grammar.StringLiteral("foo")
                    ),
                    gll_grammar.LabeledNode(
                        name="Bar",
                        item=gll_grammar.Option(item=gll_grammar.StringLiteral("bar")),
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
        import enum
        import typing

        import rust_parser.gll.semantics


        @typing.sealed
        class Main(metaclass=rust_parser.gll.semantics.ADT):
            _variants = {"Foo": "Foo", "Bar": "Bar"}

            class Foo(str):
                @classmethod
                def from_ast(cls, ast: str) -> Foo:
                    return cls(ast)

            class BarInner(str):
                @classmethod
                def from_ast(cls, ast: str) -> BarInner:
                    return cls(ast)

            Bar = rust_parser.gll.semantics.Maybe[BarInner]


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)
        """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]

    assert g.parse("foo", semantics=semantics) == Main.Foo("foo")
    assert g.parse("bar", semantics=semantics) == Main.Bar.Just("bar")
    assert g.parse("", semantics=semantics) == Main.Bar.Nothing()
    assert g.parse("qux", semantics=semantics) == Main.Bar.Nothing()


def test_empty_in_root_alternation():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Alternation(
                items=[
                    gll_grammar.LabeledNode("Foo", gll_grammar.StringLiteral("foo")),
                    gll_grammar.LabeledNode("Bar", gll_grammar.Empty()),
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
        import enum
        import typing

        import rust_parser.gll.semantics


        @typing.sealed
        class Main(metaclass=rust_parser.gll.semantics.ADT):
            _variants = {"Foo": "Foo", "Bar": "Bar"}

            class Foo(str):
                @classmethod
                def from_ast(cls, ast: str) -> Foo:
                    return cls(ast)

            class Bar:
                pass


        class Semantics:
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)
        """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]

    assert g.parse("foo", semantics=semantics) == Main.Foo("foo")
    return  # TODO: the following will fail
    assert g.parse("", semantics=semantics) == Main.Bar()


def test_reference_ident():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode("foo", gll_grammar.SymbolName("IDENT")),
                    gll_grammar.LabeledNode("bar", gll_grammar.SymbolName("SBar")),
                ]
            ),
            "SBar": gll_grammar.Concatenation(
                [
                    gll_grammar.LabeledNode("bar1", gll_grammar.StringLiteral("bar1")),
                    gll_grammar.LabeledNode("bar2", gll_grammar.StringLiteral("bar2")),
                ]
            ),
        }
    )

    sc = generate_semantics_code(grammar, use_builtin_rules=True)
    g = generate_tatsu_grammar(grammar, extra_rules=BUILTIN_RULES)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics
        import rust_parser.gll.builtin_rules


        @dataclasses.dataclass
        class Main:
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(
                    foo=ast["foo"],
                    bar=ast["bar"],
                )

            foo: rust_parser.gll.builtin_rules.IDENT
            bar: SBar


        @dataclasses.dataclass
        class SBar:
            @classmethod
            def from_ast(cls, ast) -> SBar:
                return cls(
                    bar1=str(ast["bar1"]),
                    bar2=str(ast["bar2"]),
                )

            bar1: str
            bar2: str


        class Semantics(rust_parser.gll.builtin_rules.BuiltinSemantics):
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)

            def SBar(self, ast) -> SBar:
                return SBar.from_ast(ast)
        """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]
    SBar = namespace["SBar"]

    assert g.parse("foo bar1 bar2", semantics=semantics, rule_name="Main") == Main(
        IDENT("foo"), SBar("bar1", "bar2")
    )


def test_labeled_repeated():
    grammar = gll_grammar.Grammar(
        rules={
            "Main": gll_grammar.LabeledNode(
                name="items",
                item=gll_grammar.Repeated(
                    positive=True,
                    item=gll_grammar.SymbolName(name="Item"),
                    separator="::",
                    allow_trailing=False,
                ),
            ),
            "Item": gll_grammar.Concatenation(
                items=[
                    gll_grammar.LabeledNode("foo", gll_grammar.StringLiteral("FOO")),
                    gll_grammar.LabeledNode("bar", gll_grammar.StringLiteral("BAR")),
                ]
            ),
        }
    )

    sc = generate_semantics_code(grammar, use_builtin_rules=True)
    g = generate_tatsu_grammar(grammar, extra_rules=BUILTIN_RULES)

    assert sc == textwrap.dedent(
        """\
        from __future__ import annotations

        import dataclasses
        import enum
        import typing

        import rust_parser.gll.semantics
        import rust_parser.gll.builtin_rules


        @dataclasses.dataclass
        class MainInner:
            inner: Item

            @classmethod
            def from_ast(cls, ast) -> MainInner:
                return cls(inner=ast)

        class Main(typing.List[MainInner]):
            @classmethod
            def from_ast(cls, ast) -> Main:
                return cls(list(map(MainInner.from_ast, ast["items"]))[0::2])


        @dataclasses.dataclass
        class Item:
            @classmethod
            def from_ast(cls, ast) -> Item:
                return cls(
                    foo=str(ast["foo"]),
                    bar=str(ast["bar"]),
                )

            foo: str
            bar: str


        class Semantics(rust_parser.gll.builtin_rules.BuiltinSemantics):
            def Main(self, ast) -> Main:
                return Main.from_ast(ast)

            def Item(self, ast) -> Item:
                return Item.from_ast(ast)
    """
    )

    namespace = {}
    exec(sc, namespace)
    semantics = namespace["Semantics"]()
    Main = namespace["Main"]
    MainInner = namespace["MainInner"]
    Item = namespace["Item"]

    assert g.parse("FOO BAR", semantics=semantics, rule_name="Main") == Main(
        [MainInner(Item("FOO", "BAR"))]
    )
    assert g.parse("FOO BAR :: FOO BAR", semantics=semantics, rule_name="Main") == Main(
        [MainInner(Item("FOO", "BAR")), MainInner(Item("FOO", "BAR"))]
    )
