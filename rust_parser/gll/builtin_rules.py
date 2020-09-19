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

"""Defines the built-in rules of GLL grammars: IDENT, PUNCT, LITERAL, and TOKEN_TREE."""

from __future__ import annotations

from dataclasses import dataclass

from tatsu import grammars
from tatsu.ast import AST


@dataclass
class IDENT:
    ident: str

    # from https://doc.rust-lang.org/reference/identifiers.html
    _IDENTIFIER_OR_KEYWORD = "([a-zA-Z][a-zA-Z0-9_]*|_[a-zA-Z0-9_]+)"
    _RAW_IDENTIFIER = (
        "r#" + _IDENTIFIER_OR_KEYWORD
    )  # TODO: Except crate, self, super, Self
    _NON_KEYWORD_IDENTIFIER = (
        _IDENTIFIER_OR_KEYWORD
    )  # TODO: Except a strict or reserved keyword
    _IDENTIFIER = rf"({_NON_KEYWORD_IDENTIFIER}|{_RAW_IDENTIFIER})"

    RULE = grammars.Rule(
        ast=None,
        name="IDENT",
        exp=grammars.Pattern("\s*" + _IDENTIFIER),
        params=None,
        kwparams=None,
    )

    @classmethod
    def from_ast(cls, ast: str) -> IDENT:
        return cls(ast.strip())


@dataclass
class LIFETIME:
    lifetime: str

    RULE = grammars.Rule(
        ast=None,
        name="LIFETIME",
        exp=grammars.Pattern("\s*'\s*" + IDENT._IDENTIFIER),
        params=None,
        kwparams=None,
    )

    @classmethod
    def from_ast(cls, ast: str) -> LIFETIME:
        return cls(ast.strip()[1:].strip())


@dataclass
class PUNCT:
    punct: str

    # from https://github.com/rust-lang/rust/blob/1.46.0/src/librustc_lexer/src/lib.rs#L72-L126
    # minus (){}[] (which mess with TokenTree
    RULE = grammars.Rule(
        ast=None,
        name="PUNCT",
        exp=grammars.Pattern(r"\s*[;,.@#~?:$=!<>\-&+*/^%]"),
        params=None,
        kwparams=None,
    )

    @classmethod
    def from_ast(cls, ast: str) -> PUNCT:
        return cls(ast.strip())


@dataclass
class LITERAL:
    literal: str

    # from https://github.com/rust-lang/rust/blob/1.46.0/src/librustc_lexer/src/lib.rs#L133-L150
    _PATTERNS = [
        r"0b([01_]+\.?[01_]*|[01_]*\.[01_]+)([fui][0-9]+)?",  # int/float (bin)
        r"0x([0-9a-f_]+\.?[0-9a-f_]*|[0-9a-f_]*\.[0-9a-f_]+)([fui][0-9]+)?",  # int/float (hex)
        r"([0-9][0-9_]*\.?[0-9_]*|([0-9][0-9_]*)?\.[0-9_]+)([fui][0-9]+)?",  # int/float (dec)
        r"b?'(\\\\|[^\\])'",  # char and byte
        r'b?"([^\\]|\\\\)*"',  # str and bytestr
        # TODO: rawstr and rawbytestr
    ]

    RULE = grammars.Rule(
        ast=None,
        name="LITERAL",
        exp=grammars.Pattern(f"\s*({'|'.join(_PATTERNS)})"),
        params=None,
        kwparams=None,
    )

    @classmethod
    def from_ast(cls, ast: str) -> PUNCT:
        return cls(ast.strip())


@dataclass
class TOKEN_TREE:
    tokens: list

    RULE = grammars.Rule(
        ast=None,
        name="TOKEN_TREE",
        exp=grammars.Choice(
            [
                grammars.RuleRef("LITERAL"),
                grammars.RuleRef("IDENT"),
                grammars.RuleRef("LIFETIME"),
                grammars.RuleRef("PUNCT"),
                grammars.Sequence(
                    AST(
                        sequence=[
                            grammars.Token("("),
                            grammars.Closure(grammars.RuleRef("TOKEN_TREE")),
                            grammars.Token(")"),
                        ]
                    )
                ),
                grammars.Sequence(
                    AST(
                        sequence=[
                            grammars.Token("{"),
                            grammars.Closure(grammars.RuleRef("TOKEN_TREE")),
                            grammars.Token("}"),
                        ]
                    )
                ),
                grammars.Sequence(
                    AST(
                        sequence=[
                            grammars.Token("["),
                            grammars.Closure(grammars.RuleRef("TOKEN_TREE")),
                            grammars.Token("]"),
                        ]
                    )
                ),
            ]
        ),
        params=None,
        kwparams=None,
    )

    @classmethod
    def from_ast(cls, ast) -> TOKEN_TREE:
        return cls(ast)


class BuiltinSemantics:
    @staticmethod
    def IDENT(ast):
        return IDENT.from_ast(ast)

    @staticmethod
    def LIFETIME(ast):
        return LIFETIME.from_ast(ast)

    @staticmethod
    def PUNCT(ast):
        return PUNCT.from_ast(ast)

    @staticmethod
    def LITERAL(ast):
        return LITERAL.from_ast(ast)

    @staticmethod
    def TOKEN_TREE(ast):
        return TOKEN_TREE.from_ast(ast)


BUILTIN_RULES = [TOKEN_TREE.RULE, IDENT.RULE, LIFETIME.RULE, PUNCT.RULE, LITERAL.RULE]
