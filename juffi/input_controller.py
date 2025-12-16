"""Abstract input controller and implementation for handling keyboard inputs and data"""

import curses
import io
import os
from abc import ABC, abstractmethod
from typing import Iterator


class InputController(ABC):
    """Abstract base class for input controllers"""

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
    def get_input_name(self) -> str:
        """
        Get the name of the input source.

        Returns:
            The name of the input source
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Reset the data source to the beginning.
        This allows re-reading data from the start.
        """


class FileInputController(InputController):
    """Concrete implementation of input controller for Juffi application"""

    def __init__(
        self, stdscr: curses.window, file: io.StringIO, input_name: str = "unknown"
    ) -> None:
        self._stdscr = stdscr
        self._file = file
        self._input_name = input_name

    def get_input(self) -> int:
        """Fetch keyboard input from curses"""
        return self._stdscr.getch()

    def get_data(self) -> Iterator[str]:
        """Fetch data as an iterator of strings from the log file"""
        if self._file is None:
            return iter([])

        # Return an iterator that reads lines from the file
        return iter(self._file)

    def get_input_name(self) -> str:
        """Get the basename of the input source"""
        return os.path.basename(self._input_name)

    def reset(self) -> None:
        """Reset the file pointer to the beginning"""
        self._file.seek(0)
