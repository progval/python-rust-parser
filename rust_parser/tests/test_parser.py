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

from ..gll import builtin_rules
from ..parser import Parser


@pytest.fixture(scope="session")
def parser():
    return Parser(start_rules={"ExprMain": "Expr", "ModuleMain": "ModuleContents"})


@pytest.fixture(scope="session")
def ast(parser):
    return parser.ast


def test_parse_addition(parser, ast):
    assert parser.parse("1 + 2", start_rule_name="ExprMain") == ast.Expr(
        attrs=[],
        kind=ast.ExprKind.Binary(
            left=ast.Expr(
                attrs=[],
                kind=ast.ExprKind.Literal(inner=builtin_rules.LITERAL(literal="1")),
            ),
            op=ast.BinaryOp.ADD,
            right=ast.Expr(
                attrs=[],
                kind=ast.ExprKind.Literal(inner=builtin_rules.LITERAL(literal="2")),
            ),
        ),
    )


def test_parse_const_declaration(parser, ast):
    assert parser.parse(
        'const foo: bar = "baz";', start_rule_name="ModuleMain"
    ) == ast.ModuleContents(
        attrs=[],
        items=[
            ast.Item(
                attrs=[],
                vis=None,
                kind=ast.ItemKind.Const(
                    name=builtin_rules.IDENT(ident="foo"),
                    ty=ast.Type.Path_(
                        inner=ast.QPath.Unqualified(
                            inner=ast.Path(
                                global_=False,
                                path=[
                                    ast.RelativePathInner(
                                        inner=ast.PathSegment(
                                            ident=builtin_rules.IDENT(ident="bar"),
                                            field_1=None,
                                        )
                                    )
                                ],
                            )
                        )
                    ),
                    value=ast.Expr(
                        attrs=[],
                        kind=ast.ExprKind.Literal(
                            inner=builtin_rules.LITERAL(literal='"baz"')
                        ),
                    ),
                ),
            )
        ],
    )


def test_parse_fn_declaration(parser, ast):
    def expected_ast(ret_ty):
        return [
            ast.Item(
                attrs=[],
                vis=None,
                kind=ast.ItemKind.Fn(
                    header=ast.FnHeader(
                        constness=False, unsafety=False, asyncness=False, abi=None
                    ),
                    decl=ast.FnDecl(
                        name=builtin_rules.IDENT(ident="foo"),
                        generics=None,
                        args=None,
                        ret_ty=ret_ty,
                        where_clause=None,
                    ),
                    body=ast.Block(
                        attrs=[],
                        stmts=[
                            ast.Stmt.Expr_(
                                inner=ast.Expr(
                                    attrs=[],
                                    kind=ast.ExprKind.Literal(
                                        inner=builtin_rules.LITERAL(literal="42")
                                    ),
                                )
                            )
                        ],
                    ),
                ),
            )
        ]

    assert parser.parse(
        "fn foo() { 42 }", start_rule_name="ModuleMain"
    ) == ast.ModuleContents(attrs=[], items=expected_ast(None))

    assert parser.parse(
        "fn foo() -> u64 { 42 }", start_rule_name="ModuleMain"
    ) == ast.ModuleContents(
        attrs=[],
        items=expected_ast(
            ast.Type.Path_(
                inner=ast.QPath.Unqualified(
                    inner=ast.Path(
                        global_=False,
                        path=[
                            ast.RelativePathInner(
                                inner=ast.PathSegment(
                                    ident=builtin_rules.IDENT(ident="u64"), field_1=None
                                )
                            )
                        ],
                    )
                )
            ),
        ),
    )
