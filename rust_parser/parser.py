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

import os.path
import importlib.util
import pkg_resources
import secrets
import sys
import tempfile
import types
import typing

import tatsu
import tatsu.ast
import tatsu.grammars

from .gll.tokens import tokenize_gll
from .gll.grammar import parse_gll
from .gll.generate import generate_tatsu_grammar
from .gll.semantics import generate_semantics_code
from .gll.simplification import simplify_grammar
from .gll.builtin_rules import BUILTIN_RULES


GRAMMAR_PATH = "wg-grammar/grammar/"


# TODO: that's ugly, we shouldn't need a tempfile for that, and especially not let it
# live for as long as the process, but it's the only way I could find to make pytest
# find the code
ast_dir = tempfile.TemporaryDirectory("rust_parser_asts")
# class ast_dir:
#    name = "asts/"


class Parser:
    def __init__(self, start_rules: typing.Dict[str, str]):

        code = "\n\n".join(
            pkg_resources.resource_string(
                __name__, os.path.join(GRAMMAR_PATH, filename)
            ).decode()
            for filename in pkg_resources.resource_listdir(__name__, GRAMMAR_PATH)
        )
        assert code

        start_rules = [
            tatsu.grammars.Rule(
                ast=None,
                params=None,
                kwparams=None,
                name=start_rule_name,
                exp=tatsu.grammars.Sequence(
                    ast=tatsu.ast.AST(
                        sequence=[
                            tatsu.grammars.RuleRef(start_rule_target),
                            tatsu.grammars.EOF(),
                        ]
                    )
                ),
            )
            for (start_rule_name, start_rule_target) in start_rules.items()
        ]

        tokens = tokenize_gll(code)
        gll_grammar = parse_gll(tokens)
        self.tatsu_grammar = generate_tatsu_grammar(
            gll_grammar, extra_rules=BUILTIN_RULES + start_rules
        )

        # TODO: that's ugly, we shouldn't need a tempfile for that, but it's
        # the only way I could find to make pytest find the code
        semantics_code = generate_semantics_code(
            simplify_grammar(gll_grammar), use_builtin_rules=True
        )
        module_name = "ast_" + secrets.token_hex(10)
        module_fullname = "rust_parser.asts." + module_name
        filename = os.path.join(ast_dir.name, module_name + ".py")
        with open(filename, "wt") as fd:
            fd.write(semantics_code)
        spec = importlib.util.spec_from_file_location(module_fullname, filename)
        self.ast = importlib.util.module_from_spec(spec)
        sys.modules[module_fullname] = self.ast  # needed by dataclasses when executing
        spec.loader.exec_module(self.ast)

    def parse(self, s, start_rule_name):
        return self.tatsu_grammar.parse(
            s, semantics=self.ast.Semantics(), rule_name=start_rule_name
        )
