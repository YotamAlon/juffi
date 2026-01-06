"""Common terminal parsing utilities for tests"""

import enum
import re
from typing import Literal, NamedTuple, TypeAlias

from juffi.helpers.curses_utils import Color
from juffi.helpers.list_utils import find_first

ansi_escape = re.compile(rb"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
ansi_color = re.compile(rb"\x1b\[[0-9;]*m")


class CharType(enum.Enum):
    """Character types for testing"""

    REGULAR = enum.auto()
    ANSI_GENERAL = enum.auto()
    ANSI_ERASE = enum.auto()
    ANSI_COLOR = enum.auto()
    DEFINE_G1 = enum.auto()
    ACTIVATE_G0 = enum.auto()
    UNKNOWN = enum.auto()


class SimpleChar(NamedTuple):
    """Simple character with no additional information"""

    type: CharType
    value: bytes


class AnsiColorChar(NamedTuple):
    """ANSI color character"""

    type: Literal[CharType.ANSI_COLOR]
    value: bytes
    color: Color


Char: TypeAlias = SimpleChar | AnsiColorChar


class ParseResult(NamedTuple):
    """Result of parsing a character"""

    char: Char | None
    remaining_data: bytes
    leftovers: bytes


def parse_char(data: bytes) -> ParseResult:
    """Parse a character from the given data"""
    if not data:
        return ParseResult(None, b"", b"")

    if data[0] == 0x1B:
        result = _parse_ansi_char(data)

    elif data[0] == 0x0F:
        char = SimpleChar(CharType.ACTIVATE_G0, data[0:1])
        result = ParseResult(char, data[1:], b"")
    else:
        char = SimpleChar(CharType.REGULAR, data[0:1])
        result = ParseResult(char, data[1:], b"")
    return result


def _get_color(char_data: bytes) -> Color:
    color_str = char_data[2:-1].decode()
    if not color_str:
        return Color.DEFAULT

    codes = [int(code) for code in color_str.split(";") if code]
    foreground_code = find_first(codes, lambda code: 30 <= code <= 39)

    if foreground_code is None or foreground_code == 39:
        return Color.DEFAULT

    return Color(foreground_code - 30)


def _parse_ansi_char(data: bytes) -> ParseResult:
    if len(data) == 1:
        result = ParseResult(None, b"", data)

    elif (matches := ansi_escape.match(data, 0, 20)) and matches.start() == 0:
        char_data = data[: matches.end()]
        char: Char
        if data[1:3] == b"[J":
            char = SimpleChar(CharType.ANSI_ERASE, char_data)
        elif ansi_color.match(data, 0, 20):
            char = AnsiColorChar(CharType.ANSI_COLOR, char_data, _get_color(char_data))
        else:
            char = SimpleChar(CharType.ANSI_GENERAL, char_data)
        result = ParseResult(char, data[matches.end() :], b"")
    elif data[1:3] == b")0":
        char = SimpleChar(CharType.DEFINE_G1, data[0:3])
        result = ParseResult(char, data[3:], b"")
    elif 0x1B not in data[1:]:
        result = ParseResult(None, b"", data)
    else:
        raise ValueError(f"Unknown escape sequence: {data[:20]!r}")
    return result
