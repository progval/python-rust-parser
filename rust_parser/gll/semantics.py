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

"""Generates semantic actions for use by a Tatsu parser."""

from __future__ import annotations

from dataclasses import dataclass
import enum
import textwrap
import typing
from typing import Dict, Generic, List, Optional, Type, TypeVar

from tatsu.util import safe_name

from . import grammar


_IMPORTS = ["dataclasses", "typing"]
"""Modules imported by the generated source code."""


T = TypeVar("T", bound="ADT")


def _adt_from_ast(cls: Type[T], ast: typing.Dict[str, typing.Any]) -> T:
    (variant_name,) = set(ast) & cls._variants
    value = ast.pop(variant_name)
    variant_class = getattr(cls, variant_name)
    assert issubclass(variant_class, cls)  # sealed
    if ast:
        # cls is probably a "complex" type, Tatsu wrote
        # its fields at the same level of the AST
        return variant_class.from_ast(ast)
    else:
        # cls is probably a native type, so not a named
        # subtree, so the value is not at the same level of
        # the AST
        return variant_class.from_ast(value)


class ADT(type):
    """A metaclass that makes the attributes listed in the 'variants' attribute
    a subclass of the class."""
    def __new__(cls, name, parents, attributes):
        variant_names = attributes["_variants"]

        # The class that we are producing
        attributes["from_ast"] = classmethod(_adt_from_ast)
        adt = type(name, parents, attributes)

        for variant_name in variant_names:
            # get the class defined inside this one.
            variant_source = attributes[variant_name]

            # It has only parents that inherit only 'object' directly because
            # we defined it that way. Get these parents.
            # If they didn't inherit directly, then this would add 'duplicate'
            # inheritence, but we don't need to deal with that for now.
            variant_mro = variant_source.mro()
            (_variant, *variant_parents, _object) = variant_mro
            assert _variant is variant_source
            assert _object is object

            variant_attributes = {}
            for (attr_name, attr) in variant_source.__dict__.items():
                if hasattr(attr, "__self__"):
                    # We need to use .__func__ to get the unbound method, or it would be
                    # bound to the old class instead of the new one. (ie. using
                    # 'variant_source.from_ast' directly would return instances of
                    # 'variant_source', instead of instances of 'variant')
                    variant_attributes[attr_name] = attr.__func__
                else:
                    variant_attributes[attr_name] = attr

            # Create a similar class, which inherits the adt in addition to its
            # original parents
            variant = type(
                variant_name, (*variant_parents, adt), variant_attributes,
            )

            # Replace the old one with the one we just created
            setattr(adt, variant_name, variant)

        return adt


@typing.sealed
class Maybe(Generic[T]):
    """An Option like it ought to be: an ADT, not like Python's Optional[T].
    """

    # Ideally this would be named Option/None/Some for consistency with Rust,
    # but it clashes with Python names, so this uses Haskell names instead.

    # FIXME: This leaks memory if the set of types is not bounded. Maybe we can
    # do it with a WeakKeyDictionary?
    __cache = {}
    """We *need* to memoize the generated classes, because otherwise,
    `Maybe[int].Nothing()` would not be equal to `Maybe[int].Nothing()`, as these
    would be two different Nothings.
    """

    @classmethod
    def from_ast(cls, ast):
        if ast:
            return cls.Just.from_ast(ast)
        else:
            return cls.Nothing()

    def __class_getitem__(cls, type_param):
        """Generates Just and Nothing variants for the non-generic class."""
        if type_param in cls.__cache:
            return cls.__cache[type_param]
        new_cls = type(f"Maybe[{type_param}]", (cls,), {})

        @dataclass
        class Just(new_cls):
            item: type_param

            @classmethod
            def from_ast(cls, ast):
                return Just(type_param.from_ast(ast))

        @dataclass
        class Nothing(new_cls):
            pass

        new_cls.Just = Just
        new_cls.Nothing = Nothing

        assert issubclass(Just, new_cls)
        assert issubclass(Nothing, new_cls)

        cls.__cache[type_param] = new_cls

        return new_cls


class ListNode(List[T], Generic[T]):
    __cache = {}
    """See Maybe.__cache"""

    @classmethod
    def from_ast(cls, ast):
        return cls(map(cls.__Item.from_ast, ast))

    def __class_getitem__(cls, type_param):
        return type(f"ListNode[{type_param}]", (cls,), {"_ListNode__Item": type_param})


# TODO: ideally, this should be None to be pythonic, but I can't find how to do it :(
@dataclass
class NoneTree:
    @classmethod
    def from_ast(cls, ast) -> NoneTree:
        return NoneTree()


class StrLeaf(str):
    @classmethod
    def from_ast(cls, ast) -> StrLeaf:
        return cls(ast)


def node_to_type(node: grammar.RuleNode, rule_name_to_type_name: Dict[str, str]):
    """From a rule's description, return a type representing its AST."""
    match node:
        case grammar.Empty():
            return "rust_parser.gll.semantics.NoneTree"

        case grammar.LabeledNode(name, item):
            # TODO: do something with the label?
            return node_to_type(item, rule_name_to_type_name)

        case grammar.StringLiteral(string):
            # TODO: NewType?
            return "rust_parser.gll.semantics.StrLeaf"

        case grammar.CharacterRange(from_char, to_char):
            raise NotImplementedError("character ranges")

        case grammar.SymbolName(name):
            # alias of an other rule
            return rule_name_to_type_name[name]

        case grammar.Concatenation(items):
            # TODO: use namedtuple if they have names
            members = tuple(
                node_to_type(item, rule_name_to_type_name) for item in items
            )
            return str(typing.Tuple[members])

        case grammar.Alternation(items):
            raise NotImplementedError("Alternation nested in rule")  # TODO

        case grammar.Option(item):
            return f"rust_parser.gll.semantics.Maybe[{node_to_type(item, rule_name_to_type_name)}]"

        case grammar.Repeated(positive, item, separator, allow_trailing):
            return f"rust_parser.gll.semantics.ListNode[{node_to_type(item, rule_name_to_type_name)}]"

        case _:
            # should be unreachable
            assert False, node


def _node_to_field_code(
    node: grammar.RuleNode,
    default_name: str,
    rule_name_to_type_name: Dict[str, str],
) -> (str, str):
    """Returns the source code to describe this node as a field in a dataclass."""
    match node:
        case grammar.LabeledNode(name, item):
            return (name, node_to_type(item, rule_name_to_type_name))

        case _:
            return (default_name, node_to_type(node, rule_name_to_type_name))


def node_to_type_code(
    type_name: str,
    node: grammar.RuleNode,
    rule_name_to_type_name: Dict[str, str],
) -> str:
    """From a node description, return the source code of a class
    representing its AST."""

    match node:
        case grammar.Empty():
            return textwrap.dedent(
                f"""
                class {type_name}:
                    pass
                """
            )

        case grammar.LabeledNode(name, item):
            # TODO: if the type_name was auto-generated, use the label instead
            return node_to_type_code(
                type_name, item, rule_name_to_type_name,
            )

        case grammar.StringLiteral(string):
            return textwrap.dedent(
                f"""\
                class {type_name}(str):
                    @classmethod
                    def from_ast(cls, ast: str) -> {type_name}:
                        return cls(ast)
                """
            )

        case grammar.CharacterRange(from_char, to_char):
            raise NotImplementedError("character ranges")

        case grammar.SymbolName(name):
            # alias of an other rule
            target_name = rule_name_to_type_name[name]
            return textwrap.dedent(
                f"""\
                class {type_name}({target_name}):
                    @classmethod
                    def from_ast(cls, ast: str) -> {type_name}:
                        return cls(ast)
                """
            )

        case grammar.Concatenation(items):
            field_names_and_types = [
                _node_to_field_code(item, f"field_{i}", rule_name_to_type_name)
                for (i, item) in enumerate(items)
            ]

            args = "".join(
                f'''
                                {name}={type_}.from_ast(ast.{name}),'''
                for (i, (name, type_)) in enumerate(field_names_and_types)
            )

            lines = [
                textwrap.dedent(
                    f"""\
                    @dataclasses.dataclass
                    class {type_name}:
                        @classmethod
                        def from_ast(cls, ast) -> {type_name}:
                            return cls({args}
                            )
                    """
                )
            ]
            lines.extend(
                f"    {name}: {type_}"
                for (name, type_) in field_names_and_types
            )
            lines.append("")
            return "\n".join(lines)

        case grammar.Alternation(items):
            # Ideally, we would use algebraic data types here.
            # Bad news: Python doesn't have ADTs.
            # Good news: PEP 622 is close enough, so we'll use that.
            blocks = []
            variant_names = []
            for (i, item) in enumerate(items):
                match item:
                    case grammar.LabeledNode(name, item):
                        # We're in luck! We have a human-supplied name for this variant
                        # TODO: make sure it's unique
                        block = node_to_type_code(
                            name, item, rule_name_to_type_name,
                        )

                    case _:
                        # else, generate a name.
                        # TODO: make sure it's unique
                        name = f"{type_name}_{i}"
                        block = node_to_type_code(
                            name, item, rule_name_to_type_name,
                        )

                variant_names.append(name)
                blocks.append(textwrap.indent(block, "    "))

            blocks.insert(
                0,
                textwrap.dedent(
                    f"""\
                    @typing.sealed
                    class {type_name}(metaclass=rust_parser.gll.semantics.ADT):
                        _variants = {{{
                            ', '.join(
                                f'"{variant_name}"' for variant_name in variant_names
                            )
                        }}}
                    """
                )
            )

            return "\n".join(blocks)

        case grammar.Option(item):
            # TODO: better name
            name = f"{type_name}Inner"
            blocks = [
                node_to_type_code(name, item, rule_name_to_type_name),
                f"{type_name} = rust_parser.gll.semantics.Maybe[{name}]\n",
            ]
            return "\n\n".join(blocks)

        case grammar.Repeated(positive, item, separator, allow_trailing):
            # now I can see a use for that, but I'm just lazy, let's do it later
            raise NotImplementedError("Entire rule is repeated.")

        case _:
            # should be unreachable
            assert False, node


def grammar_to_semantics_code(
    grammar: grammar.Grammar,
    rule_name_to_type_name: Dict[str, str],
) -> str:
    lines = ["class Semantics:"]
    for rule_name in grammar.rules:
        type_name = rule_name_to_type_name[rule_name]
        lines.append(
            f"    def {safe_name(rule_name)}(self, ast) -> {type_name}:"
        )

        lines.append(f"        return {type_name}.from_ast(ast)")
        lines.append("")

    return "\n".join(lines)


def generate_semantics_code(grammar: grammar.Grammar) -> str:
    rule_name_to_type_name = {}
    for rule_name in grammar.rules:
        # TODO: escape keywords, special chars, etc.
        rule_name_to_type_name[rule_name] = safe_name(rule_name)

    blocks = [
        "from __future__ import annotations",
        "\n".join(f"import {name}" for name in _IMPORTS),
        "import rust_parser.gll.semantics\n",
    ]

    for (rule_name, rule) in grammar.rules.items():
        code = node_to_type_code(rule_name, rule, rule_name_to_type_name)
        blocks.append(code)

    blocks.append(
        grammar_to_semantics_code(grammar, rule_name_to_type_name)
    )

    return "\n\n".join(blocks)
