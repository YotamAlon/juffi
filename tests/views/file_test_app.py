"""Test utilities for views"""

import pathlib

from juffi.helpers.curses_utils import Size
from tests.infra.base_test_app import BaseTestApp

CURRENT_DIR = pathlib.Path(__file__).parent
LOG_FILE = CURRENT_DIR / "test.log"


class FileTestApp(BaseTestApp):
    """Collect output from the app"""

    def __init__(
        self,
        fd: int,
        log_file: pathlib.Path,
        terminal_size: Size,
    ):
        super().__init__(fd, terminal_size)
        self._log_file = log_file

    @property
    def log_file(self) -> pathlib.Path:
        """Get the log file path"""
        return self._log_file

    def append_to_log(self, lines: list[str]) -> None:
        """Append lines to the log file"""
        with self._log_file.open("a") as f:
            for line in lines:
                f.write(line + "\n")
