"""Shared test infrastructure for piped input tests"""

import os
import pty
import subprocess
from typing import Iterator

import pytest

from juffi.helpers.curses_utils import Size
from tests.infra.utils import set_terminal_size
from tests.piped.piped_test_app import PipedTestApp


@pytest.fixture(scope="function", name="piped_test_app")
def piped_test_app_fixture() -> Iterator[PipedTestApp]:
    """Run the app with piped input and capture its output"""
    master, slave = pty.openpty()
    terminal_size = Size(80, 80)
    set_terminal_size(slave, terminal_size)

    stdin_read, stdin_write = os.pipe()

    with subprocess.Popen(
        ["python", "-m", "juffi"],
        stdin=stdin_read,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        env=os.environ.copy() | {"TERM": "linux"},
    ) as process:
        os.close(slave)
        os.close(stdin_read)

        juffi_test_app = PipedTestApp(master, stdin_write, terminal_size)
        juffi_test_app.read_text_until("Press 'h' for help", timeout=3)
        yield juffi_test_app
        os.close(master)
        os.close(stdin_write)
        process.terminate()
