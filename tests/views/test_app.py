"""Test the app view"""

import codecs
import enum
import fcntl
import os
import pathlib
import pty
import re
import select
import struct
import subprocess
import termios
from typing import Callable, Iterator

import pytest

from juffi.helpers.list_utils import find_first_index

CURRENT_DIR = pathlib.Path(__file__).parent
LOG_FILE = CURRENT_DIR / "test.log"

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


class Output:
    """Collect output from the app"""

    def __init__(self, fd: int):
        self._fd = fd
        self._data: list[Char] = []
        self._leftovers = b""
        os.set_blocking(self._fd, False)
        # flags = fcntl.fcntl(self._fd, fcntl.F_GETFL)
        # fcntl.fcntl(self._fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

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

                if (matches := ansi_escape.match(data, 0, 10)) and matches.start() == 0:
                    ansi_type = CharType.ANSI_GENERAL
                    if data[1:3] == b"[J":
                        ansi_type = CharType.ANSI_ERASE
                    self._data.append(Char(ansi_type, data[: matches.end()]))
                    data = data[matches.end() :]
                elif data[1:3] == b")0":
                    self._data.append(Char(CharType.DEFINE_G1, data[0:3]))
                    data = data[3:]
                else:
                    raise ValueError(f"Unknown escape sequence: {data[:10]!r}")
            elif data[0] == 0x0F:
                self._data.append(Char(CharType.ACTIVATE_G0, data[0:1]))
                data = data[1:]
            else:
                self._data.append(Char(CharType.REGULAR, data[0:1]))
                data = data[1:]

    def read_until(
        self, predicate: Callable[[bytes], bool], timeout: float = 5
    ) -> None:
        """Read until the predicate is met"""
        incremental_decoder = codecs.getincrementaldecoder("utf-8")()

        while not predicate(self.raw):
            ready, _, _ = select.select([self._fd], [], [], timeout)
            if not ready:
                raise TimeoutError(f"Timeout waiting for data after {timeout} seconds")
            data = os.read(self._fd, 64)
            decoded = incremental_decoder.decode(data)
            self._add_bytes(decoded.encode())


@pytest.fixture(name="app_output")
def app_output_fixture() -> Iterator[Output]:
    """Run the app and capture its output"""
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 80, 80, 80, 80))
    with subprocess.Popen(
        ["python", "-m", "juffi", LOG_FILE],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        env=os.environ.copy() | {"TERM": "linux"},
    ) as process:
        os.close(slave)
        yield Output(master)
        os.close(master)
        process.terminate()


def test_app_title_included_file_name(app_output: Output):
    """Test the app"""
    app_output.read_until(lambda data: LOG_FILE.name.encode() in data)
    assert app_output.latest_text.startswith(
        f" Juffi - JSON Log Viewer - {LOG_FILE.name}"
    ), app_output.latest_text
