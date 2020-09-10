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

import pprint
import sys

from .tokens import tokenize_gll
from .grammar import parse_gll


def main():
    try:
        (_, filename) = sys.argv
        if filename in ("-h", "--help"):
            raise ValueError()
    except ValueError:
        print(f"Syntax: python310 -m rust_parser.gll <filename>", file=sys.stderr)
        print()
        print(f"use '-' as filename to use stdin.")
        exit(1)

    if filename == "-":
        code = sys.stdin.read()
    else:
        with open(filename, "rt") as fd:
            code = fd.read()

    tokens = tokenize_gll(code)
    grammar = parse_gll(tokens)
    print(repr(grammar))


main()
