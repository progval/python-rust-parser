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

from ..tokens import tokenize_gll, Name, SimpleToken, String


def test_simple_operators():
    assert list(tokenize_gll("{ } | ? * + %  %%   ;: = \n } |")) == [
        SimpleToken.GROUP_START,
        SimpleToken.GROUP_END,
        SimpleToken.PIPE,
        SimpleToken.QUESTION_MARK,
        SimpleToken.STAR,
        SimpleToken.PLUS,
        SimpleToken.PERCENT,
        SimpleToken.DOUBLE_PERCENT,
        SimpleToken.SEMICOLON,
        SimpleToken.COLON,
        SimpleToken.EQUAL,
        SimpleToken.GROUP_END,
        SimpleToken.PIPE,
    ]


def test_string():
    assert list(tokenize_gll('"bar" "baz qux" "" "quux"')) == [
        String("bar"),
        String("baz qux"),
        String(""),
        String("quux"),
    ]


def test_name():
    assert list(tokenize_gll("foo BAR baz a qux")) == [
        Name("foo"),
        Name("BAR"),
        Name("baz"),
        Name("a"),
        Name("qux"),
    ]


def test_comments():
    assert list(tokenize_gll("foo // bar\n baz /* qux \n quux */ foo")) == [
        Name("foo"),
        Name("baz"),
        Name("foo"),
    ]


def test_separators():
    assert list(tokenize_gll("foo? bar* baz+")) == [
        Name("foo"),
        SimpleToken.QUESTION_MARK,
        Name("bar"),
        SimpleToken.STAR,
        Name("baz"),
        SimpleToken.PLUS,
    ]
