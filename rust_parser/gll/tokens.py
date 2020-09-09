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

from dataclasses import dataclass
import enum
from typing import sealed, Dict, Iterator, List, Optional

@sealed 
class Token:
    pass

class SimpleToken(Token, enum.Enum):
    GROUP_START = "{"
    GROUP_END = "}"
    PIPE = "|"
    QUESTION_MARK = "?"
    STAR = "*"
    PLUS = "+"
    PERCENT = "?"
    SEMICOLON = ";"

@dataclass
class String(Token):
    value: str

@dataclass
class CharacterRange(Token):
    from_char: str
    to_char: str

@dataclass
class Name(Token):
    value: str


def tokenize_gll(code: str) -> Iterator[str]:
    index = 0
    while index < len(code):
        char = code[index]
        index += 1

        match char:
            case " ":
                continue
            case "{" | "}" | "|" | "?" | "*" | "+" | "?" | ";":
                yield SimpleToken(char)
            case '"':
                # find the next quote
                new_index = code.find('"', index)
                assert new_index > 0, f"Unclosed quote at index {index-1}"
                assert new_index >= index
                yield String(value=code[index:new_index])
                index = new_index+1
            case "'":
                raise NotImplementedError("Character ranges.")

            case _:
                new_index = code.find(' ', index)
                if new_index == -1:
                    yield Name(value=code[index-1:])
                    return
                else:
                    assert new_index >= index
                    yield Name(value=code[index-1:new_index])
                    index = new_index+1
