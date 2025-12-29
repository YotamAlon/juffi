"""Shared test infrastructure for view tests"""

import fcntl
import os
import pathlib
import pty
import shutil
import struct
import subprocess
import tempfile
import termios
from typing import Iterator

import pytest

from juffi.helpers.curses_utils import Size
from tests.views.file_test_app import LOG_FILE, FileTestApp


@pytest.fixture(scope="session", name="temp_log_file")
def temp_log_file_fixture() -> Iterator[pathlib.Path]:
    """Create a temporary copy of the test log file"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
        temp_path = pathlib.Path(tmp.name)
        shutil.copy(LOG_FILE, temp_path)
        yield temp_path


@pytest.fixture(scope="session", name="test_app")
def test_app_fixture(temp_log_file: pathlib.Path) -> Iterator[FileTestApp]:
    """Run the app and capture its output"""
    master, slave = pty.openpty()
    terminal_height = 80
    terminal_width = 80
    _set_terminal_size(slave, terminal_height, terminal_width)
    with subprocess.Popen(
        ["python", "-m", "juffi", str(temp_log_file)],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        env=os.environ.copy() | {"TERM": "linux"},
    ) as process:
        os.close(slave)
        juffi_test_app = FileTestApp(
            master, temp_log_file, Size(terminal_height, terminal_width)
        )
        juffi_test_app.read_text_until("Press 'h' for help", timeout=3)
        yield juffi_test_app
        os.close(master)
        process.terminate()


def _set_terminal_size(slave: int, terminal_height: int, terminal_width: int) -> None:
    fcntl.ioctl(
        slave,
        termios.TIOCSWINSZ,
        struct.pack(
            "HHHH", terminal_height, terminal_width, terminal_height, terminal_width
        ),
    )


@pytest.fixture(autouse=True)
def _reset_test_app(test_app: FileTestApp, temp_log_file: pathlib.Path) -> None:
    """Reset the test app to its initial state"""
    temp_log_file.write_text(LOG_FILE.read_text())
    test_app.reset()
    test_app.read_text_until("Press 'h' for help", timeout=3)
