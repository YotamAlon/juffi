"""Test utilities"""

import fcntl
import struct
import termios

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
