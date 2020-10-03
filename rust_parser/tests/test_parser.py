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

from ..gll import grammar
from ..gll import builtin_rules
from ..parser import Parser


def test_parse():
    p = Parser(start_rules={"ExprMain": "Expr", "ModuleMain": "ModuleContents"})

    assert p.parse("1 + 2", start_rule_name="ExprMain") == p.ast.Expr(
        attrs=[],
        kind=p.ast.ExprKind.Binary(
            left=p.ast.Expr(
                attrs=[],
                kind=p.ast.ExprKind.Literal(inner=builtin_rules.LITERAL(literal="1")),
            ),
            op=p.ast.BinaryOp.ADD,
            right=p.ast.Expr(
                attrs=[],
                kind=p.ast.ExprKind.Literal(inner=builtin_rules.LITERAL(literal="2")),
            ),
        ),
    )

    assert p.parse(
        'const foo: bar = "baz";', start_rule_name="ModuleMain"
    ) == p.ast.ModuleContents(
        attrs=[],
        items=[
            p.ast.Item(
                attrs=[],
                vis=None,
                kind=p.ast.ItemKind.Const(
                    name=builtin_rules.IDENT(ident="foo"),
                    ty=p.ast.Type.Path_(
                        inner=p.ast.QPath.Unqualified(
                            inner=p.ast.Path(
                                global_=False,
                                path=[
                                    p.ast.RelativePathInner(
                                        inner=p.ast.PathSegment(
                                            ident=builtin_rules.IDENT(ident="bar"), field_1=None
                                        )
                                    )
                                ],
                            )
                        )
                    ),
                    value=p.ast.Expr(
                        attrs=[],
                        kind=p.ast.ExprKind.Literal(
                            inner=builtin_rules.LITERAL(literal='"baz"')
                        ),
                    ),
                ),
            )
        ],
    )
