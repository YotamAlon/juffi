"""Test utilities"""

import contextlib
import fcntl
import os
import pathlib
import pty
import struct
import subprocess
import termios
from typing import Iterator

from juffi.helpers.curses_utils import Size

RIGHT_ARROW = "\x1b[C"
LEFT_ARROW = "\x1b[D"
DOWN_ARROW = "\x1b[B"
UP_ARROW = "\x1b[A"


def set_terminal_size(slave: int, terminal_size: Size) -> None:
    """Set the terminal size"""
    fcntl.ioctl(
        slave,
        termios.TIOCSWINSZ,
        struct.pack(
            "HHHH",
            terminal_size.height,
            terminal_size.width,
            terminal_size.height,
            terminal_size.width,
        ),
    )


@contextlib.contextmanager
def juffi_process(log_file: pathlib.Path, terminal_size: Size) -> Iterator[int]:
    """Context manager for running juffi process with a test app."""
    master, slave = pty.openpty()
    set_terminal_size(slave, terminal_size)
    with subprocess.Popen(
        ["python", "-m", "juffi", str(log_file)],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        env=os.environ.copy() | {"TERM": "linux"},
    ) as process:
        try:
            yield master
        finally:
            os.close(master)
            process.terminate()
