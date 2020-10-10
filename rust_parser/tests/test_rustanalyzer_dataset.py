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

from ast import literal_eval
import os
from types import ModuleType
from typing import Iterable

import pytest


@pytest.fixture
def rast_dir(request):
    return os.path.join(
        request.fspath.dirname, "data/rust-analyzer/crates/syntax/test_data/parser/"
    )


@pytest.fixture
def rast_path(rast_dir):
    def opener(filename):
        return os.path.join(rast_dir, filename)

    return opener


def collapse_tree_to_level(tree, level):
    while level < len(tree):
        top = tree.pop()
        tree[-1].append(top)


def indented_file_to_tree(lines: Iterable[str]):
    tree = [[]]
    for line in lines:
        line = line.rstrip()
        stripped_line = line.lstrip()
        indent = (len(line) - len(stripped_line)) // 2
        tree_length = len(tree)

        stack_item = [stripped_line]

        if indent + 2 > tree_length:
            assert indent + 2 == tree_length + 1
        else:
            while indent + 1 < len(tree):
                del tree[-1]

        tree[-1].append(stack_item)
        tree.append(stack_item)

    assert len(tree[0]) == 1

    return tree[0][0]


def test_indented_file_to_tree():
    assert indented_file_to_tree(["a", "  b", "  c"]) == ["a", ["b"], ["c"]]
    assert indented_file_to_tree(["a", "  b", "    c"]) == ["a", ["b", ["c"]]]
    assert indented_file_to_tree(["a", "  b", "    c", "  d"]) == [
        "a",
        ["b", ["c"]],
        ["d"],
    ]


class LineTreeToAstVisitor:
    def __init__(self, ast: ModuleType):
        self.ast = ast

    def split_line(self, line: str):
        (node_name, rest) = line.split("@", 1)
        if " " in rest:
            (_, arg) = rest.split(" ", 1)
            arg = literal_eval(arg)
        else:
            arg = None

        return (node_name, arg)

    def visit(self, node):
        (root_line, *subtrees) = node
        assert isinstance(root_line, str), repr(root_line)

        (node_name, arg) = self.split_line(root_line)

        visit_method = getattr(self, "visit_" + node_name, None)
        if visit_method is None:
            raise NotImplementedError(f"Unhandled node: {node_name}")
        return visit_method(arg, subtrees)

    def visit_subtrees(self, st):
        return list(filter(None, map(self.visit, st)))

    def subtrees_dict(self, subtrees, singlelist=(), manylist=(), ignorelist=()):
        d = {}
        for subtree in subtrees:
            subtree_root = subtree[0]
            (subtree_root_node_name, _) = self.split_line(subtree_root)
            if subtree_root_node_name in singlelist:
                assert subtree_root_node_name not in d
                d[subtree_root_node_name] = self.visit(subtree)
            elif subtree_root_node_name in manylist:
                d.setdefault(subtree_root_node_name, []).append(self.visit(subtree))
            elif subtree_root_node_name in ignorelist:
                pass
            else:
                raise NotImplementedError(
                    f"Unexpected subtree root node name: {subtree_root_node_name}"
                )

        return d

    def visit_GENERIC_PARAM_LIST(self, arg, subtrees):
        children = self.subtrees_dict(
            subtrees,
            manylist=("TYPE_PARAM",),
            ignorelist=("L_ANGLE", "WHITESPACE", "R_ANGLE"),
        )
        return children["TYPE_PARAM"]

    def visit_IDENT(self, arg, subtrees):
        () = subtrees
        return arg

    def visit_NAME(self, arg, subtrees):
        (ident,) = subtrees
        return self.visit(ident)

    def visit_SOURCE_FILE(self, arg, subtrees):
        assert arg is None
        return self.ast.ModuleContents(
            attrs=[],
            items=[
                self.ast.Item(attrs=[], vis=None, kind=item)
                for item in self.visit_subtrees(subtrees)
            ],
        )

    def visit_STRUCT(self, arg, subtrees):
        assert subtrees
        children = self.subtrees_dict(
            subtrees,
            singlelist=("NAME", "GENERIC_PARAM_LIST", "RECORD_FIELD_LIST"),
            ignorelist=("STRUCT_KW", "WHITESPACE"),
        )

        return self.ast.ItemKind.Struct(
            name=self.visit(children["NAME"]),
            generics=children.get("GENERIC_PARAM_LIST", []),
            body=children["RECORD_FIELD_LIST"],
        )

    def visit_WHITESPACE(self, arg, subtrees):
        assert subtrees == []
        return None


def rast_file_to_ast(lines: Iterable[str], ast: ModuleType):
    """Converts one of rust-analyzer's .rast files to an AST of classes generated
    by this parser."""
    line_tree = indented_file_to_tree(lines)
    return LineTreeToAstVisitor(ast).visit(line_tree)


def test_empty(parser, ast, rast_path):
    assert rast_file_to_ast(["SOURCE_FILE@0..0"], ast) == ast.ModuleContents([], [])
    with open(rast_path("ok/0000_empty.rast")) as rast_fd:
        source = open(rast_path("ok/0000_empty.rs")).read()
        assert rast_file_to_ast(rast_fd, ast) == parser.parse(
            source, start_rule_name="ModuleMain"
        )


def test_struct_item(parser, ast, rast_path):
    with open(rast_path("ok/0001_struct_item.rast")) as rast_fd:
        source = open(rast_path("ok/0001_struct_item.rs")).read()
        assert rast_file_to_ast(rast_fd, ast) == parser.parse(
            source, start_rule_name="ModuleMain"
        )
