"""Curses utility functions"""

import curses
import enum
import functools
from typing import NamedTuple

DEL = 127

ESC = 27


class Position(NamedTuple):
    """A simple position class"""

    y: int
    x: int


class Size(NamedTuple):
    """A simple size class"""

    height: int
    width: int


class Viewport(NamedTuple):
    """A simple viewport class"""

    pos: Position
    size: Size

    @property
    def x(self):
        """Get the x position"""
        return self.pos.x

    @property
    def y(self):
        """Get the y position"""
        return self.pos.y

    @property
    def width(self):
        """Get the width"""
        return self.size.width

    @property
    def height(self):
        """Get the height"""
        return self.size.height


def get_curses_yx() -> Size:
    """Get the current terminal size"""
    return Size(curses.LINES, curses.COLS)  # pylint: disable=no-member


class Color(enum.IntEnum):
    """Enumeration of colors"""

    DEFAULT = curses.COLOR_WHITE
    INFO = curses.COLOR_GREEN
    WARNING = curses.COLOR_YELLOW
    ERROR = curses.COLOR_RED
    DEBUG = curses.COLOR_BLUE
    HEADER = curses.COLOR_CYAN
    SELECTED = curses.COLOR_MAGENTA


@functools.cache
def get_colors() -> dict[Color, int]:
    """Get a dictionary of colors"""
    colors = {}
    for i, color in enumerate(Color):
        curses.init_pair(i, color.value, -1)
        colors[color] = curses.color_pair(i)
    return colors
