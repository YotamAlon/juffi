"""Test utilities for views"""

import json
import pathlib
from datetime import datetime
from typing import Iterable

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

    def append_to_log(self, lines: Iterable[str | dict]) -> None:
        """Append lines to the log file

        Args:
            lines: List of strings or dicts. Dicts will be converted to JSON strings.
                   Datetime objects in dicts are automatically converted to ISO format.
        """
        with self._log_file.open("a") as f:
            for line in lines:
                if isinstance(line, dict):
                    line = self._convert_dict_to_json(line)
                f.write(line + "\n")

    @staticmethod
    def _convert_dict_to_json(data: dict) -> str:
        """Convert a dict to JSON, handling datetime objects"""
        converted_data = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                converted_data[key] = value.isoformat()
            else:
                converted_data[key] = value
        return json.dumps(converted_data)
