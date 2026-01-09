"""Output controller for wrapping curses operations to enable testing"""

import curses
from abc import ABC, abstractmethod

from juffi.helpers.curses_utils import Color, Size, TextAttribute


class Window(ABC):
    """Abstract window interface for curses operations"""

    @abstractmethod
    def derwin(self, nlines: int, ncols: int, begin_y: int, begin_x: int) -> "Window":
        """Create a derived window"""

    @abstractmethod
    def resize(self, nlines: int, ncols: int) -> None:
        """Resize the window"""

    @abstractmethod
    def mvderwin(self, par_y: int, par_x: int) -> None:
        """Move the derived window"""

    @abstractmethod
    def getmaxyx(self) -> tuple[int, int]:
        """Get the maximum y and x coordinates"""

    @abstractmethod
    def clear(self) -> None:
        """Clear the window"""

    @abstractmethod
    def refresh(self) -> None:
        """Refresh the window"""

    @abstractmethod
    def noutrefresh(self) -> None:
        """Mark window for refresh without updating screen"""

    @abstractmethod
    def addstr(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        y: int,
        x: int,
        text: str,
        color: Color | None = None,
        attributes: list[TextAttribute] | None = None,
    ) -> None:
        """Add a string to the window"""

    @abstractmethod
    def move(self, y: int, x: int) -> None:
        """Move the cursor"""


class OutputController(ABC):
    """Abstract output controller interface for curses module operations"""

    @abstractmethod
    def create_window(self, curses_window) -> Window:
        """Create a Window instance wrapping the given curses window"""

    @abstractmethod
    def get_color_attr(self, color: Color) -> int:
        """Get the color attribute for a Color enum"""

    @abstractmethod
    def curs_set(self, visibility: int) -> None:
        """Set cursor visibility"""

    @abstractmethod
    def update_lines_cols(self) -> None:
        """Update LINES and COLS after terminal resize"""

    @abstractmethod
    def get_lines(self) -> int:
        """Get the number of lines in the terminal"""

    @abstractmethod
    def get_cols(self) -> int:
        """Get the number of columns in the terminal"""

    @abstractmethod
    def get_terminal_size(self) -> Size:
        """Get the terminal size as a Size tuple"""


class CursesWindow(Window):
    """Concrete implementation of Window wrapping a curses window"""

    def __init__(self, curses_window, color_to_pair: dict[Color, int]) -> None:
        self._window = curses_window
        self._color_to_pair = color_to_pair

    def derwin(self, nlines: int, ncols: int, begin_y: int, begin_x: int) -> Window:
        """Create a derived window"""
        return CursesWindow(
            self._window.derwin(nlines, ncols, begin_y, begin_x),
            self._color_to_pair,
        )

    def resize(self, nlines: int, ncols: int) -> None:
        """Resize the window"""
        self._window.resize(nlines, ncols)

    def mvderwin(self, par_y: int, par_x: int) -> None:
        """Move the derived window"""
        self._window.mvderwin(par_y, par_x)

    def getmaxyx(self) -> tuple[int, int]:
        """Get the maximum y and x coordinates"""
        return self._window.getmaxyx()

    def clear(self) -> None:
        """Clear the window"""
        self._window.clear()

    def refresh(self) -> None:
        """Refresh the window"""
        self._window.refresh()

    def noutrefresh(self) -> None:
        """Mark window for refresh without updating screen"""
        self._window.noutrefresh()

    def addstr(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        y: int,
        x: int,
        text: str,
        color: Color | None = None,
        attributes: list[TextAttribute] | None = None,
    ) -> None:
        """Add a string to the window"""
        attr = 0
        if color is not None:
            attr = self._color_to_pair.get(color, 0)
        if attributes:
            for text_attr in attributes:
                attr |= text_attr.value
        self._window.addstr(y, x, text, attr)

    def move(self, y: int, x: int) -> None:
        """Move the cursor"""
        self._window.move(y, x)


class CursesOutputController(OutputController):
    """Concrete implementation of OutputController wrapping the curses module"""

    def __init__(self) -> None:
        self._color_to_pair: dict[Color, int] = {}
        self._start_color()
        self._use_default_colors()

    @staticmethod
    def _start_color() -> None:
        """Initialize color support"""
        curses.start_color()

    def _use_default_colors(self) -> None:
        """Use default terminal colors"""
        curses.use_default_colors()
        for i, color in enumerate(Color):
            pair_num = i + 1
            curses.init_pair(pair_num, color.value, -1)
            self._color_to_pair[color] = curses.color_pair(pair_num)

    def create_window(self, curses_window) -> Window:
        """Create a Window instance wrapping the given curses window"""
        return CursesWindow(curses_window, self._color_to_pair)

    def get_color_attr(self, color: Color) -> int:
        """Get the color attribute for a Color enum"""
        return self._color_to_pair.get(color, 0)

    def curs_set(self, visibility: int) -> None:
        """Set cursor visibility"""
        curses.curs_set(visibility)

    def update_lines_cols(self) -> None:
        """Update LINES and COLS after terminal resize"""
        curses.update_lines_cols()

    def get_lines(self) -> int:
        """Get the number of lines in the terminal"""
        return curses.LINES  # pylint: disable=no-member

    def get_cols(self) -> int:
        """Get the number of columns in the terminal"""
        return curses.COLS  # pylint: disable=no-member

    def get_terminal_size(self) -> Size:
        """Get the terminal size as a Size tuple"""
        return Size(curses.LINES, curses.COLS)  # pylint: disable=no-member
