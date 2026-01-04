"""Common terminal parsing utilities for tests"""

import enum
import re
from typing import NamedTuple

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


class Char(NamedTuple):
    """Character with type information"""

    type: CharType
    value: bytes


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
        char = Char(CharType.ACTIVATE_G0, data[0:1])
        result = ParseResult(char, data[1:], b"")
    else:
        char = Char(CharType.REGULAR, data[0:1])
        result = ParseResult(char, data[1:], b"")
    return result


def _parse_ansi_char(data: bytes) -> ParseResult:
    if len(data) == 1:
        result = ParseResult(None, b"", data)

    elif (matches := ansi_escape.match(data, 0, 20)) and matches.start() == 0:
        ansi_type = CharType.ANSI_GENERAL
        if data[1:3] == b"[J":
            ansi_type = CharType.ANSI_ERASE
        elif ansi_color.match(data, 0, 20):
            ansi_type = CharType.ANSI_COLOR
        char = Char(ansi_type, data[: matches.end()])
        result = ParseResult(char, data[matches.end() :], b"")
    elif data[1:3] == b")0":
        char = Char(CharType.DEFINE_G1, data[0:3])
        result = ParseResult(char, data[3:], b"")
    elif 0x1B not in data[1:]:
        result = ParseResult(None, b"", data)
    else:
        raise ValueError(f"Unknown escape sequence: {data[:20]!r}")
    return result
