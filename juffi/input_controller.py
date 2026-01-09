"""Abstract input controller and implementation for handling keyboard inputs and data"""

import contextlib
import curses
import fcntl
import functools
import os
from abc import ABC, abstractmethod
from typing import Callable, Iterator, TextIO


class InputController(ABC):
    """Abstract base class for input controllers"""

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of the input source.

        Returns:
            The name of the input source
        """

    @abstractmethod
    def get_input(self) -> int:
        """
        Fetch keyboard input.

        Returns:
            The input key code
        """

    @abstractmethod
    def get_data(self) -> Iterator[str]:
        """
        Fetch data as an iterator of strings.

        Returns:
            An iterator of strings
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Reset the data source to the beginning.
        This allows re-reading data from the start.
        """

    @abstractmethod
    def timeout(self, delay: int) -> None:
        """
        Set blocking or non-blocking read.

        Args:
            delay: Timeout in milliseconds. -1 for blocking, 0 for non-blocking.
        """


class FileInputController(InputController):
    """Concrete implementation of input controller for Juffi application"""

    def __init__(self, stdscr: curses.window, file: TextIO) -> None:
        self._stdscr = stdscr
        self._file = file
        self._stdscr.keypad(True)

    @property
    def name(self) -> str:
        """Get the basename of the input source"""
        return os.path.basename(self._file.name)

    def get_input(self) -> int:
        """Fetch keyboard input from curses"""
        return self._stdscr.getch()

    def get_data(self) -> Iterator[str]:
        """Fetch data as an iterator of strings from the log file"""
        return iter(self._file)

    def reset(self) -> None:
        """Reset the file pointer to the beginning"""
        self._file.seek(0)

    def timeout(self, delay: int) -> None:
        """Set blocking or non-blocking read"""
        self._stdscr.timeout(delay)


class StdinInputController(InputController):
    """Input controller for reading from stdin (piped input)"""

    def __init__(self, stdscr, input_stream: TextIO) -> None:
        self._stdscr = stdscr
        self._input_stream = input_stream
        self._all_lines: list[str] = []
        self._last_read_index: int = 0
        self._stdscr.keypad(True)

    @property
    def name(self) -> str:
        """Get the name of the input source"""
        return "<stdin>"

    def get_input(self) -> int:
        """Fetch keyboard input from curses"""
        return self._stdscr.getch()

    def get_data(self) -> Iterator[str]:
        """Fetch data as an iterator of strings from stdin"""
        while True:
            line = self._input_stream.readline()
            if not line:
                break
            self._all_lines.append(line)

        new_lines = self._all_lines[self._last_read_index :]
        self._last_read_index = len(self._all_lines)
        return iter(new_lines)

    def reset(self) -> None:
        """Reset the read index to the beginning"""
        self._last_read_index = 0

    def timeout(self, delay: int) -> None:
        """Set blocking or non-blocking read"""
        self._stdscr.timeout(delay)


@contextlib.contextmanager
def _create_file_input_controller(
    file_name: str,
) -> Iterator[Callable[[curses.window], FileInputController]]:
    """Create a FileInputController from a file path"""
    with open(file_name, "r", encoding="utf-8", errors="ignore") as file:
        yield functools.partial(FileInputController, file=file)


@contextlib.contextmanager
def _create_stdin_input_controller() -> (
    Iterator[Callable[[curses.window], StdinInputController]]
):
    """Create a StdinInputController"""
    input_stream = _get_pipe_input_stream()
    tty_path = os.environ.get("JUFFI_TTY", "/dev/tty")
    with open(tty_path, encoding="utf-8") as tty:
        os.dup2(tty.fileno(), 0)
        yield functools.partial(StdinInputController, input_stream=input_stream)


def _get_pipe_input_stream() -> TextIO:
    original_stdin_fd = os.dup(0)
    flags = fcntl.fcntl(original_stdin_fd, fcntl.F_GETFL)
    fcntl.fcntl(original_stdin_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    input_stream = os.fdopen(original_stdin_fd, "r", encoding="utf-8")
    return input_stream


@contextlib.contextmanager
def create_input_controller(
    file_name: str | None,
) -> Iterator[Callable[[curses.window], InputController]]:
    """Create an InputController based on the provided file name"""
    if file_name:
        with _create_file_input_controller(file_name) as partial_controller:
            yield partial_controller
    else:
        with _create_stdin_input_controller() as partial_controller:
            yield partial_controller
