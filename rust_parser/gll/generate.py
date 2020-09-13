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

"""Generates a parser using Tatsu."""

from dataclasses import dataclass

from tatsu import grammars as tatsu_grammars
from tatsu.ast import AST

from . import grammar as gll_grammar


def node_to_tatsu(node: gll_grammar.RuleNode):
    match node:
        case gll_grammar.Empty():
            return tatsu_grammars.EmptyClosure()

        case gll_grammar.LabeledNode(name, item):
            return tatsu_grammars.Named(AST(name=name, exp=node_to_tatsu(item)))

        case gll_grammar.StringLiteral(s):
            return tatsu_grammars.Token(ast=s)

        case gll_grammar.CharacterRange(_, _):
            raise NotImplementedError("character ranges")

        case gll_grammar.SymbolName(name):
            return tatsu_grammars.RuleRef(ast=name)

        case gll_grammar.Concatenation(items):
            return tatsu_grammars.Sequence(
                ast=AST(sequence=list(map(node_to_tatsu, items)))
            )

        case gll_grammar.Alternation(items):
            return tatsu_grammars.Choice(ast=list(map(node_to_tatsu, items)))

        case gll_grammar.Option(item):
            return tatsu_grammars.Optional(exp=node_to_tatsu(item))

        case gll_grammar.Repeated(False, item, separator=None, allow_trailing=False):
            return tatsu_grammars.Closure(exp=node_to_tatsu(item))

        case gll_grammar.Repeated(True, item, separator=None, allow_trailing=False):
            return tatsu_grammars.PositiveClosure(exp=node_to_tatsu(item))

        case gll_grammar.Repeated(False, item, separator, allow_trailing=False):
            return tatsu_grammars.Join(
                ast=AST(exp=node_to_tatsu(item), sep=tatsu_grammars.Token(ast=separator))
            )

        case gll_grammar.Repeated(True, item, separator, allow_trailing=False):
            return tatsu_grammars.PositiveJoin(
                ast=AST(exp=node_to_tatsu(item), sep=tatsu_grammars.Token(ast=separator))
            )

        case gll_grammar.Repeated(False, item, separator, allow_trailing=True):
            item = node_to_tatsu(item)
            separator = tatsu_grammars.Token(ast=separator)
            return tatsu_grammars.Sequence(
                ast=AST(
                    sequence=[
                        tatsu_grammars.Closure(
                            exp=tatsu_grammars.Sequence(
                                ast=AST(
                                    sequence=[
                                        item,
                                        separator,
                                    ]
                                )
                            ),
                        ),
                        tatsu_grammars.Optional(exp=item),
                    ]
                )
            )

        case gll_grammar.Repeated(True, item, separator, allow_trailing=True):
            item = node_to_tatsu(item)
            separator = tatsu_grammars.Token(ast=separator)
            return tatsu_grammars.Sequence(
                ast=AST(
                    sequence=[
                        item,
                        tatsu_grammars.Closure(
                            exp=tatsu_grammars.Sequence(
                                ast=AST(
                                    sequence=[
                                        separator,
                                        item,
                                    ]
                                )
                            ),
                        ),
                        tatsu_grammars.Optional(exp=separator),
                    ]
                )
            )

        case _:
            # should be unreachable
            assert False, repr(node)



def generate_tatsu_grammar(grammar: gll_grammar.Grammar) -> tatsu_grammars.Grammar:
    tatsu_rules = []
    for (symbol, rule) in grammar.rules.items():
        tatsu_rule = tatsu_grammars.Rule(
            ast=None,
            name=symbol,
            exp=node_to_tatsu(rule),
            params=None,
            kwparams=None,
        )
        tatsu_rules.append(tatsu_rule)

    return tatsu_grammars.Grammar(name=grammar.name, rules=tatsu_rules)
