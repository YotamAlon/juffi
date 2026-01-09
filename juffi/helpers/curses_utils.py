"""Curses utility functions"""

import curses
import enum
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


class Color(enum.IntEnum):
    """Enumeration of colors"""

    DEFAULT = curses.COLOR_WHITE
    INFO = curses.COLOR_GREEN
    WARNING = curses.COLOR_YELLOW
    ERROR = curses.COLOR_RED
    DEBUG = curses.COLOR_BLUE
    HEADER = curses.COLOR_CYAN
    SELECTED = curses.COLOR_MAGENTA


class TextAttribute(enum.IntEnum):
    """Enumeration of text attributes"""

    UNDERLINE = curses.A_UNDERLINE
    REVERSE = curses.A_REVERSE
    BOLD = curses.A_BOLD
