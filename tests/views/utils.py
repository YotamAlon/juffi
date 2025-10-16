"""Test utilities for views"""

import codecs
import enum
import os
import pathlib
import re
import select
from typing import Callable

from juffi.helpers.list_utils import find_first_index

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


class JuffiTestApp:
    """Collect output from the app"""

    def __init__(self, fd: int):
        self._fd = fd
        self._data: list[Char] = []
        self._leftovers = b""
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        os.set_blocking(self._fd, False)

    @property
    def raw(self) -> bytes:
        """Get the raw output as bytes"""
        return self._get_joined_bytes(self._data)

    @property
    def text(self) -> str:
        """Get the text output as a string without display characters"""
        return self._get_joined_bytes(
            self._data, lambda c: c.type == CharType.REGULAR
        ).decode()

    @property
    def latest_text(self) -> str:
        """Get the latest text output as a string without display characters"""
        reversed_index = find_first_index(
            list(reversed(self._data)),
            lambda c: c.type == CharType.ANSI_ERASE,
            len(self._data),
        )
        last_erase_index = len(self._data) - reversed_index
        return self._get_joined_bytes(
            self._data[last_erase_index:], lambda c: c.type == CharType.REGULAR
        ).decode()

    def read_text_until(self, string_to_check: str, timeout: float = 5) -> str:
        """Read until the predicate is met"""

        while string_to_check not in self.text:
            ready, _, _ = select.select([self._fd], [], [], timeout)
            if not ready:
                raise TimeoutError(f"Timeout waiting for data after {timeout} seconds")
            data = os.read(self._fd, 64)
            decoded = self._decoder.decode(data, False)
            self._add_bytes(decoded.encode())

        i = -1
        while True:
            try:
                screen = self._get_screen(i, lambda c: c.type == CharType.REGULAR)
            except IndexError as e:
                raise RuntimeError(
                    f"Unable to find {string_to_check!r} in saved data, even though I just read it"
                ) from e

            if string_to_check in screen.decode():
                break
            i -= 1
        return screen.decode()

    def send_keys(self, keys: str) -> None:
        """Send keys to the app"""
        for key in keys:
            os.write(self._fd, key.encode())

    def reset(self) -> None:
        """Reset the test app"""
        self.send_keys("R")

    @staticmethod
    def _get_joined_bytes(
        data: list[Char], filter_: Callable[[Char], bool] = lambda _: True
    ):
        return b"".join(c.value for c in data if filter_(c))

    def _get_screen(
        self, index: int = -1, filter_: Callable[[Char], bool] = lambda _: True
    ) -> bytes:
        erase_indexes = [
            i for i, c in enumerate(self._data) if c.type == CharType.ANSI_ERASE
        ]
        screen_indexes = (
            [(0, erase_indexes[0])]
            + [
                (erase_indexes[i] + 1, erase_indexes[i + 1])
                for i in range(len(erase_indexes) - 1)
            ]
            + [(erase_indexes[-1] + 1, len(self._data))]
        )

        if index < 0:
            screen_index = len(screen_indexes) + index
        else:
            screen_index = index

        if screen_index >= len(screen_indexes) or screen_index < 0:
            raise IndexError(
                f"Unable to get screen {index}, only {len(screen_indexes)} screens available"
            )

        data_start_index, data_end_index = screen_indexes[screen_index]
        screen_data = self._data[data_start_index:data_end_index]
        return self._get_joined_bytes(screen_data, filter_)

    def _add_bytes(self, data: bytes) -> None:
        data = self._leftovers + data
        self._leftovers = b""
        while data:
            if data[0] == 0x1B:
                if len(data) == 1:
                    self._leftovers = data
                    return

                if (matches := ansi_escape.match(data, 0, 20)) and matches.start() == 0:
                    ansi_type = CharType.ANSI_GENERAL
                    if data[1:3] == b"[J":
                        ansi_type = CharType.ANSI_ERASE
                    self._data.append(Char(ansi_type, data[: matches.end()]))
                    data = data[matches.end() :]
                elif data[1:3] == b")0":
                    self._data.append(Char(CharType.DEFINE_G1, data[0:3]))
                    data = data[3:]
                elif 0x1B not in data[1:]:
                    self._leftovers = data
                    return
                else:
                    raise ValueError(f"Unknown escape sequence: {data[:20]!r}")
            elif data[0] == 0x0F:
                self._data.append(Char(CharType.ACTIVATE_G0, data[0:1]))
                data = data[1:]
            else:
                self._data.append(Char(CharType.REGULAR, data[0:1]))
                data = data[1:]


CURRENT_DIR = pathlib.Path(__file__).parent
LOG_FILE = CURRENT_DIR / "test.log"
