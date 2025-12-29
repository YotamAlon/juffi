"""Common terminal parsing utilities for tests"""

import enum
import re

ansi_escape = re.compile(rb"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class CharType(enum.Enum):
    """Character types for testing"""

    REGULAR = enum.auto()
    ANSI_GENERAL = enum.auto()
    ANSI_ERASE = enum.auto()
    DEFINE_G1 = enum.auto()
    ACTIVATE_G0 = enum.auto()
    UNKNOWN = enum.auto()


class Char:
    """Character with type information"""

    def __init__(self, type_: CharType, value: bytes):
        self._type = type_
        self._value = value

    @property
    def type(self) -> CharType:
        """Get the character type"""
        return self._type

    @property
    def value(self) -> bytes:
        """Get the character value"""
        return self._value

    def __repr__(self):
        return f"Char({self.type}, {self.value})"
