"""Test utilities for piped input tests"""

import os

from juffi.helpers.curses_utils import Size
from tests.infra.base_test_app import BaseTestApp


class PipedTestApp(BaseTestApp):
    """Collect output from the app running with piped input"""

    def __init__(
        self,
        output_fd: int,
        input_fd: int,
        terminal_size: Size,
    ):
        super().__init__(output_fd, terminal_size)
        self._input_fd = input_fd

    def pipe_data(self, lines: list[str]) -> None:
        """Pipe data to stdin"""
        for line in lines:
            os.write(self._input_fd, (line + "\n").encode())
