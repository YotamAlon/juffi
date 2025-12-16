"""Test utilities for views"""

import codecs
import enum
import os
import pathlib
import re
import select
import time
from typing import Callable

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
        self._screens: list[list[Char]] = [[]]
        self._last_delivered_screen_index = 0
        self._leftovers = b""
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        os.set_blocking(self._fd, False)

    @property
    def latest_screen(self) -> str:
        """Get the latest text output as a string without display characters"""
        return self._get_joined_bytes(
            self._screens[-1], lambda c: c.type == CharType.REGULAR
        ).decode()

    def read_text_until(self, string_to_check: str, timeout: float = 1) -> str:
        """Read until the predicate is met"""

        start = time.time()
        while string_to_check not in self.latest_screen:
            data = self._read_from_stream()
            if data is None:
                time.sleep(0.001)
                continue

            decoded = self._decoder.decode(data, False)
            self._add_bytes(decoded.encode())
            if time.time() - start > timeout:
                raise TimeoutError(
                    f"Timeout waiting for desired text after {timeout} seconds. "
                    f"Last output was {self.latest_screen!r}"
                )
        for screen_index in range(
            self._last_delivered_screen_index, len(self._screens)
        ):
            screen = self._get_joined_bytes(
                self._screens[screen_index], lambda c: c.type == CharType.REGULAR
            )
            if string_to_check in screen.decode():
                break
        else:
            raise RuntimeError(
                f"Could not find string {string_to_check!r} in screens after reading it"
            )

        self._last_delivered_screen_index = screen_index

        return screen.decode()

    def _read_from_stream(self) -> bytes | None:
        ready, _, _ = select.select([self._fd], [], [], 0)
        if ready:
            data = os.read(self._fd, 256)
            return data
        return None

    def send_keys(self, keys: str) -> None:
        """Send keys to the app"""
        for key in keys:
            os.write(self._fd, key.encode())

    def reset(self) -> None:
        """Reset the test app"""
        self.send_keys("R")
        self._consume_all_output()
        assert self._read_from_stream() is None
        self._last_delivered_screen_index = len(self._screens) - 1

    def _consume_all_output(self) -> None:
        """Consume all output from the app"""
        while True:
            data = self._read_from_stream()
            if data is None:
                time.sleep(0.001)
                data = self._read_from_stream()
                if data is None:
                    break
            decoded = self._decoder.decode(data, False)
            self._add_bytes(decoded.encode())

    @staticmethod
    def _get_joined_bytes(
        data: list[Char], filter_: Callable[[Char], bool] = lambda _: True
    ):
        return b"".join(c.value for c in data if filter_(c))

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
                        self._screens.append([])
                    self._screens[-1].append(Char(ansi_type, data[: matches.end()]))
                    data = data[matches.end() :]
                elif data[1:3] == b")0":
                    self._screens[-1].append(Char(CharType.DEFINE_G1, data[0:3]))
                    data = data[3:]
                elif 0x1B not in data[1:]:
                    self._leftovers = data
                    return
                else:
                    raise ValueError(f"Unknown escape sequence: {data[:20]!r}")
            elif data[0] == 0x0F:
                self._screens[-1].append(Char(CharType.ACTIVATE_G0, data[0:1]))
                data = data[1:]
            else:
                self._screens[-1].append(Char(CharType.REGULAR, data[0:1]))
                data = data[1:]


CURRENT_DIR = pathlib.Path(__file__).parent
LOG_FILE = CURRENT_DIR / "test.log"
RIGHT_ARROW = "\x1b[C"
LEFT_ARROW = "\x1b[D"
DOWN_ARROW = "\x1b[B"
