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
import keyword
import textwrap
import typing
from typing import Dict, Generic, List, Optional, Type, TypeVar

from tatsu.util import safe_name

from . import grammar
from .builtin_rules import BUILTIN_RULES


_IMPORTS = ["dataclasses", "enum", "typing"]
"""Modules imported by the generated source code."""


T = TypeVar("T", bound="ADT")


def _adt_from_ast(cls: Type[T], ast: typing.Dict[str, typing.Any]) -> T:
    (variant_name,) = set(ast) & set(cls._variants)
    value = ast.pop(variant_name)
    variant_class = getattr(cls, cls._variants[variant_name])
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

        for (variant_name, variant_type_name) in variant_names.items():
            # get the class defined inside this one.
            variant_source = attributes[variant_type_name]

            variant_parents = list(variant_source.__bases__)
            if object in variant_parents:
                variant_parents.remove(object)

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
                variant_type_name, (*variant_parents, adt), variant_attributes,
            )

            # Replace the old one with the one we just created
            setattr(adt, variant_type_name, variant)

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
    def from_ast(cls, ast) -> Maybe[T]:
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


class SemanticsGenerator:
    def __init__(self, use_builtin_rules):
        self.use_builtin_rules = use_builtin_rules
        self.rule_name_to_type_name: Dict[str, str] = {}
        if use_builtin_rules:
            for rule in BUILTIN_RULES:
                self.rule_name_to_type_name[rule.name] = (
                    f"rust_parser.gll.builtin_rules.{rule.name}"
                )
        self.used_global_names: Set[str] = set(keyword.kwlist)
        self.generated_global_types: Set[str] = set()

    def gen_global_name(self, name):
        while name in self.used_global_names:
            name += "_"
        self.used_global_names.add(name)
        return name

    def gen_local_name(self, name):
        while name in self.used_global_names:
            name += "_"
        return name

    def node_to_type(self, node: grammar.RuleNode) -> str:
        """From a rule's description, return a type representing its AST."""
        match node:
            case grammar.Empty():
                return "None"

            case grammar.LabeledNode(name, item):
                return self.node_to_type(item)

            case grammar.StringLiteral(string):
                # TODO: NewType?
                return "str"

            case grammar.CharacterRange(from_char, to_char):
                raise NotImplementedError("character ranges")

            case grammar.SymbolName(name):
                # alias of an other rule
                return self.rule_name_to_type_name[name]

            case grammar.Concatenation(items):
                # TODO: use namedtuple if they have names
                members = tuple(
                    self.node_to_type(item) for item in items
                )
                return f"typing.Tuple[{', '.join(members)}]"

            case grammar.Alternation(items):
                # TODO: use an ADT
                members = tuple(
                    (
                        self.node_to_type(item)
                        if self.node_to_name(item, None)
                        else "None"
                    )
                    for item in items
                )
                return f"typing.Union[{', '.join(members)}]"

            case grammar.Option(grammar.Empty()):
                return "bool"

            case grammar.Option(item):
                return f"typing.Optional[{self.node_to_type(item)}]"

            case grammar.Repeated(positive, item, separator, allow_trailing):
                return f"typing.List[{self.node_to_type(item)}]"

            case _:
                # should be unreachable
                assert False, node

    def node_to_name(
        self, node: grammar.RuleNode, default_name: str,
    ) -> (str, (str, str)):
        match node:
            case grammar.LabeledNode(name, item):
                return name

            case _:
                return default_name

    def _alternation_can_be_enum(self, items: List[grammar.RuleNode]) -> bool:
        """Returns whether all the items in an alternation are empty, meaning the
        alternation can be a simply Python Enum rather than an ADT."""
        for item in items:
            match item:
                case grammar.LabeledNode(_, grammar.Empty()):
                    # TODO: also support grammar.Empty() unlabeled
                    pass
                case _:
                    return False

        return True

    def _nodes_to_variant_names(self, items: List[grammar.RuleNode]) -> List[str]:
        variant_names = []
        for (i, item) in enumerate(items):
            variant_names.append(self.node_to_name(item, f"Variant{i}"))
        return variant_names

    def node_to_constructor(self, node: grammar.RuleNode, var_name: str) -> str:
        """From a rule's description, return an expression to build it from a Tatsu AST."""
        match node:
            case grammar.Empty():
                return "None"

            case grammar.LabeledNode(_, item):
                return self.node_to_constructor(item, var_name)

            case grammar.StringLiteral(string):
                # TODO: NewType?
                return f"str({var_name})"  # we could get rid of the str() call * shrug *

            case grammar.CharacterRange(from_char, to_char):
                raise NotImplementedError("character ranges")

            case grammar.SymbolName(rule_name):
                # alias of an other rule
                return f"{var_name}"

            case grammar.Concatenation(items):
                # TODO: use namedtuple if they have names
                members = tuple(
                    self.node_to_type(item) for item in items
                )
                return f"tuple(ast.values())"

            case grammar.Alternation(items):
                variant_names = self._nodes_to_variant_names(items)

                variants = [
                    (
                        f"{name}=(lambda: "
                        + self.node_to_constructor(item, f'ast["{name}"]')
                        + ")"
                    )
                    for (name, item) in zip(variant_names, items)
                ]
                # FIXME: that's unreadable, it needs to be refactored
                return f"(lambda constructors: constructors.get((list(set(constructors) & set(ast)) or [None])[0], lambda: None))(dict({', '.join(variants)}))()"

            case grammar.Option(grammar.Empty()):
                return f"bool({var_name})"

            case grammar.Option(item):
                return f"{self.node_to_constructor(item, var_name)} if {var_name} else None"

            case grammar.Repeated(positive, item, separator, allow_trailing):
                # FIXME: ugly
                iter_var_name = var_name.split(".")[-1].replace('["', "_").replace('"]', '') + "_item"
                return (
                    f"[{self.node_to_constructor(item, f'{iter_var_name}')} "
                    f"for {iter_var_name} in {var_name}]"
                )

            case _:
                # should be unreachable
                assert False, node

    def node_to_type_code(self, type_name: str, node: grammar.RuleNode, local: bool) -> str:
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
                return self.node_to_type_code(type_name, item, local)

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
                target_name = self.rule_name_to_type_name[name]
                # TODO: try to automatically reorder rule definition to
                # minimize the first case

                if target_name in self.generated_global_types:
                    # the target is defined before this, we can inherit it.
                    return textwrap.dedent(
                        f"""\
                        class {type_name}({target_name}):
                            @classmethod
                            def from_ast(cls, ast) -> {type_name}:
                                return cls(ast)
                        """
                    )
                else:
                    # the target will be defined later in the file, we can't
                    # inherit it
                    return textwrap.dedent(
                        f"""\
                        @dataclasses.dataclass
                        class {type_name}:
                            inner: {target_name}

                            @classmethod
                            def from_ast(cls, ast) -> {type_name}:
                                return cls(inner=ast)
                        """
                    )

            case grammar.Concatenation(items):
                field_names = [
                    self.gen_local_name(self.node_to_name(item, f"field_{i}"))
                    for (i, item) in enumerate(items)
                ]
                constructors = [
                    self.node_to_constructor(item, f'ast["{name}"]')
                    for (name, item) in zip(field_names, items)
                ]
                field_types = [
                    self.node_to_type(item)
                    for (name, item) in zip(field_names, items)
                ]

                args = "".join(
                    f'''
                                    {name}={constructor},'''
                    for (name, constructor) in zip(field_names, constructors)
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
                    for (name, type_) in zip(field_names, field_types)
                )
                lines.append("")
                return "\n".join(lines)

            case grammar.Alternation(items) if self._alternation_can_be_enum(items):
                variant_names = self._nodes_to_variant_names(items)
                serialized_variant_names = ", ".join(
                    f'"{name}"' for name in variant_names
                )

                lines = [
                    f"@enum.unique",
                    f"class {type_name}(enum.Enum):",
                    f"    @staticmethod",
                    f"    def _variants():",
                    f"        return frozenset([{serialized_variant_names}])",
                    f"",
                    f"    @classmethod",
                    f"    def from_ast(cls, ast) -> {type_name}:",
                    f"        (variant,) = set(ast) & cls._variants()",
                    f"        return cls(variant)",
                    f""
                ]

                for variant_name in variant_names:
                    upper_variant_name = self.gen_local_name(variant_name.upper())
                    lines.append(f'    {upper_variant_name} = "{variant_name}"')

                lines.append("")

                return "\n".join(lines)

            case grammar.Alternation(items):
                blocks = []
                variant_names = self._nodes_to_variant_names(items)
                for (name, item) in zip(variant_names, items):
                    block = self.node_to_type_code(
                        self.gen_local_name(name), item, local=True
                    )
                    blocks.append(textwrap.indent(block, "    "))

                blocks.insert(
                    0,
                    textwrap.dedent(
                        f"""\
                        @typing.sealed
                        class {type_name}(metaclass=rust_parser.gll.semantics.ADT):
                            _variants = {{{
                                ', '.join(
                                    f'"{variant_name}": "{self.gen_local_name(variant_name)}"'
                                    for variant_name in variant_names
                                )
                            }}}
                        """
                    )
                )

                return "\n".join(blocks).replace("\n\n\n", "\n\n")

            case grammar.Option(item):
                # TODO: better name
                if local:
                    inner_name = self.gen_local_name(f"{type_name}Inner")
                else:
                    inner_name = self.gen_global_name(f"{type_name}Inner")
                blocks = [
                    self.node_to_type_code(inner_name, item, local),
                    f"{type_name} = rust_parser.gll.semantics.Maybe[{inner_name}]\n",
                ]
                return "\n\n".join(blocks)

            case grammar.Repeated(positive, item, separator, allow_trailing):
                # TODO: better name
                if local:
                    inner_name = self.gen_local_name(f"{type_name}Inner")
                    cls = "cls."
                else:
                    inner_name = self.gen_global_name(f"{type_name}Inner")
                    cls = ""
                blocks = [
                    self.node_to_type_code(inner_name, item, local),
                    textwrap.dedent(
                        f"""\
                        class {type_name}(typing.List[{inner_name}]):
                            @classmethod
                            def from_ast(cls, ast) -> {type_name}:
                                return cls(map({cls}{inner_name}.from_ast, ast))
                        """
                    )
                ]
                return "\n".join(blocks)

            case _:
                # should be unreachable
                assert False, node

    def grammar_to_semantics_code(self, grammar: grammar.Grammar) -> str:
        lines = []
        if self.use_builtin_rules:
            lines.append("class Semantics(rust_parser.gll.builtin_rules.BuiltinSemantics):")
        else:
            lines.append("class Semantics:")
        for rule_name in grammar.rules:
            type_name = self.rule_name_to_type_name[rule_name]
            lines.append(
                f"    def {safe_name(rule_name)}(self, ast) -> {type_name}:"
            )

            lines.append(f"        return {type_name}.from_ast(ast)")
            lines.append("")

        return "\n".join(lines)

    def generate(self, grammar: grammar.Grammar) -> str:
        """entry point of this class"""
        for rule_name in grammar.rules:
            # TODO: escape keywords, special chars, etc.
            type_name = safe_name(rule_name)
            assert type_name not in self.used_global_names
            self.rule_name_to_type_name[rule_name] = type_name
            self.used_global_names.add(type_name)

        blocks = []
        for (rule_name, rule) in grammar.rules.items():
            code = self.node_to_type_code(rule_name, rule, local=False)
            self.generated_global_types.add(self.rule_name_to_type_name[rule_name])
            blocks.append(code)

        blocks.append(self.grammar_to_semantics_code(grammar))

        return "\n\n".join(blocks)


def generate_semantics_code(grammar: grammar.Grammar, use_builtin_rules=False) -> str:
    local_imports = ["import rust_parser.gll.semantics\n"]
    if use_builtin_rules:
        local_imports.append("import rust_parser.gll.builtin_rules\n")
    blocks = [
        "from __future__ import annotations",
        "\n".join(f"import {name}" for name in _IMPORTS),
        "".join(local_imports),
        SemanticsGenerator(use_builtin_rules=use_builtin_rules).generate(grammar),
    ]


    return "\n\n".join(blocks)
