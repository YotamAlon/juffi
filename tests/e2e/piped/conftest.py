"""Shared test infrastructure for piped input tests"""

import os
import pty
import subprocess
from typing import Iterator

import pytest

from juffi.helpers.curses_utils import Size
from tests.e2e.piped.piped_test_app import PipedTestApp
from tests.infra.utils import set_terminal_size


@pytest.fixture(scope="function", name="piped_test_app")
def piped_test_app_fixture() -> Iterator[PipedTestApp]:
    """Run the app with piped input and capture its output"""
    master, slave = pty.openpty()
    terminal_size = Size(80, 80)
    set_terminal_size(slave, terminal_size)

    stdin_read, stdin_write = os.pipe()
    slave_name = os.ttyname(slave)

    with subprocess.Popen(
        ["python", "-m", "juffi"],
        stdin=stdin_read,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        env=os.environ.copy() | {"TERM": "linux", "JUFFI_TTY": slave_name},
    ) as process:
        try:
            juffi_test_app = PipedTestApp(master, stdin_write, terminal_size)
            juffi_test_app.read_text_until("Press 'h' for help", timeout=3)
            yield juffi_test_app
        finally:
            os.close(master)
            os.close(stdin_write)
            process.terminate()
