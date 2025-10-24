"""Shared test infrastructure for view tests"""

import fcntl
import os
import pty
import struct
import subprocess
import termios
from typing import Iterator

import pytest

from tests.views.utils import LOG_FILE, JuffiTestApp


@pytest.fixture(scope="session", name="test_app")
def test_app_fixture() -> Iterator[JuffiTestApp]:
    """Run the app and capture its output"""
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 80, 80, 80, 80))
    with subprocess.Popen(
        ["python", "-m", "juffi", str(LOG_FILE)],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        env=os.environ.copy() | {"TERM": "linux"},
    ) as process:
        os.close(slave)
        juffi_test_app = JuffiTestApp(master)
        juffi_test_app.read_text_until("Press 'h' for help", timeout=3)
        yield juffi_test_app
        os.close(master)
        process.terminate()


@pytest.fixture(autouse=True)
def _reset_test_app(test_app: JuffiTestApp) -> None:
    """Reset the test app to its initial state"""
    test_app.reset()
