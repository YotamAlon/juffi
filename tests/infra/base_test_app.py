"""Base class for test applications"""

import codecs
import os
import select
import time

from juffi.helpers.curses_utils import Size
from tests.infra.screen_data import ScreenData
from tests.infra.terminal_parser import Char, CharType, get_joined_bytes, parse_char


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
        return get_joined_bytes(
            self._screens[-1], lambda c: c.type == CharType.REGULAR
        ).decode()

    def read_text_until(self, string_to_check: str, timeout: float = 1) -> ScreenData:
        """Read until the predicate is met"""

        start = time.time()
        while string_to_check not in self.latest_screen:
            if time.time() - start > timeout:
                raise TimeoutError(
                    f"Timeout waiting for desired text after {timeout} seconds. "
                    f"Last output was {self.latest_screen!r}"
                )

            data = self._read_from_stream()
            if data is None:
                time.sleep(0.001)
                continue

            decoded = self._decoder.decode(data, False)
            self._add_bytes(decoded.encode())

        for screen_index in range(
            self._last_delivered_screen_index, len(self._screens)
        ):
            screen_chars = self._screens[screen_index]
            screen_text = get_joined_bytes(
                screen_chars, lambda c: c.type == CharType.REGULAR
            ).decode()
            if string_to_check in screen_text:
                break
        else:
            raise RuntimeError(
                f"Could not find string {string_to_check!r} in screens after reading it"
            )

        self._last_delivered_screen_index = screen_index

        return ScreenData(screen_chars)

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

    def _add_bytes(self, data: bytes) -> None:
        data = self._leftovers + data
        self._leftovers = b""
        while data:
            result = parse_char(data)
            if result.leftovers:
                self._leftovers = result.leftovers
                return
            if result.char:
                if result.char.type == CharType.ANSI_ERASE:
                    self._screens.append([])
                self._screens[-1].append(result.char)
            data = result.remaining_data
