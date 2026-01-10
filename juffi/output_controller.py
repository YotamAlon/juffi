"""Output controller for wrapping curses operations to enable testing"""

import curses
from abc import ABC, abstractmethod

from juffi.helpers.curses_utils import Color, Position, Size, TextAttribute, Viewport


class Window(ABC):
    """Abstract window interface for curses operations"""

    @abstractmethod
    def derwin(self, viewport: Viewport) -> "Window":
        """Create a derived window"""

    @abstractmethod
    def resize(self, size: Size) -> None:
        """Resize the window"""

    @abstractmethod
    def mvderwin(self, position: Position) -> None:
        """Move the derived window"""

    @abstractmethod
    def getmaxyx(self) -> Size:
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
    def addstr(
        self,
        position: Position,
        text: str,
        *,
        color: Color | None = None,
        attributes: list[TextAttribute] | None = None,
    ) -> None:
        """Add a string to the window"""

    @abstractmethod
    def move(self, position: Position) -> None:
        """Move the cursor"""


class OutputController(ABC):
    """Abstract output controller interface for curses module operations"""

    @abstractmethod
    def create_main_window(self) -> Window:
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

    def derwin(self, viewport: Viewport) -> Window:
        """Create a derived window"""
        return CursesWindow(
            self._window.derwin(
                viewport.height, viewport.width, viewport.y, viewport.x
            ),
            self._color_to_pair,
        )

    def resize(self, size: Size) -> None:
        """Resize the window"""
        self._window.resize(size.height, size.width)

    def mvderwin(self, position: Position) -> None:
        """Move the derived window"""
        self._window.mvderwin(position.y, position.x)

    def getmaxyx(self) -> Size:
        """Get the maximum y and x coordinates"""
        height, width = self._window.getmaxyx()
        return Size(height, width)

    def clear(self) -> None:
        """Clear the window"""
        self._window.clear()

    def refresh(self) -> None:
        """Refresh the window"""
        self._window.refresh()

    def noutrefresh(self) -> None:
        """Mark window for refresh without updating screen"""
        self._window.noutrefresh()

    def addstr(
        self,
        position: Position,
        text: str,
        *,
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
        self._window.addstr(position.y, position.x, text, attr)

    def move(self, position: Position) -> None:
        """Move the cursor"""
        self._window.move(position.y, position.x)


class CursesOutputController(OutputController):
    """Concrete implementation of OutputController wrapping the curses module"""

    def __init__(self, stdscr: curses.window) -> None:
        self._stdscr = stdscr
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

    def create_main_window(self) -> Window:
        """Create a Window instance wrapping the given curses window"""
        return CursesWindow(self._stdscr, self._color_to_pair)

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
