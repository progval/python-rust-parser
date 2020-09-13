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

import pickle
import pprint
import sys

import tatsu

from .tokens import tokenize_gll
from .grammar import parse_gll
from .generate import generate_tatsu_grammar
from .semantics import generate_semantics_code


def read_input_file(filename: str) -> str:
    if filename == "-":
        return sys.stdin.read()
    else:
        with open(filename, "rt") as fd:
            return fd.read()


def write_output_file(filename: str, s: str) -> None:
    if filename == "-":
        sys.stdout.write(s)
    else:
        with open(filename, "wt") as fd:
            fd.write(s)


def main():
    try:
        if "-h" in sys.argv or "--help" in sys.argv:
            raise ValueError()
        (
            _,
            input_grammar_filename,
            output_parser_filename,
            output_ast_filename,
        ) = sys.argv
    except ValueError:
        print(
            f"Syntax: python310 -m rust_parser.gll <input_grammar> <output_parser> <output_ast>",
            file=sys.stderr,
        )
        print(file=sys.stderr)
        print(
            f"use '-' instead of <input_grammar> or <output_ast> to use stdin/stdout.",
            file=sys.stderr,
        )
        exit(1)

    code = read_input_file(input_grammar_filename)

    tokens = tokenize_gll(code)
    gll_grammar = parse_gll(tokens)
    tatsu_grammar = generate_tatsu_grammar(gll_grammar)
    with open(output_parser_filename, "wb") as fd:
        pickle.dump(tatsu_grammar, fd)
    write_output_file(output_ast_filename, generate_semantics_code(gll_grammar))


main()
