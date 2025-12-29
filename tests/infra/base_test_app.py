"""Base class for test applications"""

import codecs
import os
import select
import time
from typing import Callable

from juffi.helpers.curses_utils import Size
from tests.infra.terminal_parser import Char, CharType, ansi_escape


class BaseTestApp:
    """Base class for collecting output from the app"""

    def __init__(self, output_fd: int, terminal_size: Size):
        self._output_fd = output_fd
        self._terminal_size = terminal_size
        self._screens: list[list[Char]] = [[]]
        self._last_delivered_screen_index = 0
        self._leftovers = b""
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        os.set_blocking(self._output_fd, False)

    @property
    def terminal_height(self) -> int:
        """Get the terminal height"""
        return self._terminal_size.height

    @property
    def terminal_width(self) -> int:
        """Get the terminal width"""
        return self._terminal_size.width

    @property
    def entries_height(self) -> int:
        """Get the height available for entries (terminal height - header - footer)"""
        return self.terminal_height - 2

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
        ready, _, _ = select.select([self._output_fd], [], [], 0)
        if ready:
            data = os.read(self._output_fd, 256)
            return data
        return None

    def send_keys(self, keys: str) -> None:
        """Send keys to the app"""
        for key in keys:
            os.write(self._output_fd, key.encode())

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
