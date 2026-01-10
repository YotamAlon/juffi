"""Mock implementations of OutputController and Window for testing"""

from typing import NamedTuple

from juffi.helpers.curses_utils import Color, Position, Size, TextAttribute, Viewport
from juffi.output_controller import OutputController, Window


class CharCell(NamedTuple):
    """Represents a single character cell in the screen buffer"""

    char: str
    color: Color | None
    attributes: list[TextAttribute] | None


class MockWindow(Window):
    """Mock implementation of Window for testing views

    All windows (main and derived) share the same content buffer.
    Derived windows have a viewport that defines their position and size
    relative to the parent window.
    """

    def __init__(
        self,
        content: dict[Position, CharCell],
        viewport: Viewport,
        cursor_position: list[Position],
    ) -> None:
        self._content = content
        self._viewport = viewport
        self._cursor_position = cursor_position

    def derwin(self, viewport: Viewport) -> Window:
        absolute_viewport = Viewport(
            Position(
                self._viewport.pos.y + viewport.pos.y,
                self._viewport.pos.x + viewport.pos.x,
            ),
            viewport.size,
        )
        derived = MockWindow(self._content, absolute_viewport, self._cursor_position)
        return derived

    def resize(self, size: Size) -> None:
        self._viewport = Viewport(self._viewport.pos, size)

    def mvderwin(self, position: Position) -> None:
        self._viewport = Viewport(position, self._viewport.size)

    def getmaxyx(self) -> Size:
        return self._viewport.size

    def clear(self) -> None:
        for y in range(self._viewport.height):
            for x in range(self._viewport.width):
                abs_pos = Position(self._viewport.pos.y + y, self._viewport.pos.x + x)
                self._content.pop(abs_pos, None)

    def refresh(self) -> None:
        pass

    def noutrefresh(self) -> None:
        pass

    def addstr(
        self,
        position: Position,
        text: str,
        *,
        color: Color | None = None,
        attributes: list[TextAttribute] | None = None,
    ) -> None:
        for i, char in enumerate(text):
            local_pos = Position(position.y, position.x + i)
            if (
                local_pos.x < self._viewport.width
                and local_pos.y < self._viewport.height
            ):
                abs_pos = Position(
                    self._viewport.pos.y + local_pos.y,
                    self._viewport.pos.x + local_pos.x,
                )
                self._content[abs_pos] = CharCell(char, color, attributes)

    def get_content(self) -> dict[Position, CharCell]:
        """Get a copy of the window content (only this window's viewport)"""
        result = {}
        for y in range(self._viewport.height):
            for x in range(self._viewport.width):
                abs_pos = Position(self._viewport.pos.y + y, self._viewport.pos.x + x)
                if abs_pos in self._content:
                    local_pos = Position(y, x)
                    result[local_pos] = self._content[abs_pos]
        return result

    def get_text_at(self, position: Position) -> str | None:
        """Get the text at a specific position (relative to this window)"""
        abs_pos = Position(
            self._viewport.pos.y + position.y, self._viewport.pos.x + position.x
        )
        if abs_pos in self._content:
            return self._content[abs_pos].char
        return None

    def get_line(self, y: int) -> str:
        """Get the text content of a line (relative to this window)"""
        line_chars = []
        for x in range(self._viewport.width):
            abs_pos = Position(self._viewport.pos.y + y, self._viewport.pos.x + x)
            if abs_pos in self._content:
                line_chars.append(self._content[abs_pos].char)
            else:
                line_chars.append(" ")
        return "".join(line_chars).rstrip()

    def get_all_lines(self) -> list[str]:
        """Get all lines as a list of strings (relative to this window)"""
        return [self.get_line(y) for y in range(self._viewport.height)]

    def move(self, position: Position) -> None:
        abs_pos = Position(
            self._viewport.pos.y + position.y, self._viewport.pos.x + position.x
        )
        self._cursor_position[0] = abs_pos


class MockOutputController(OutputController):
    """Mock implementation of OutputController for testing views

    Maintains a shared screen buffer that all windows draw to.
    """

    def __init__(self, terminal_size: Size = Size(24, 80)) -> None:
        self._terminal_size = terminal_size
        self._cursor_visibility = 0
        self._color_attrs: dict[Color, int] = {
            color: i for i, color in enumerate(Color)
        }
        self._screen_content: dict[Position, CharCell] = {}
        self._cursor_position = [Position(0, 0)]

    def create_main_window(self) -> Window:
        viewport = Viewport(Position(0, 0), self._terminal_size)
        return MockWindow(self._screen_content, viewport, self._cursor_position)

    def get_color_attr(self, color: Color) -> int:
        return self._color_attrs.get(color, 0)

    def curs_set(self, visibility: int) -> None:
        self._cursor_visibility = visibility

    def update_lines_cols(self) -> None:
        pass

    def get_lines(self) -> int:
        return self._terminal_size.height

    def get_cols(self) -> int:
        return self._terminal_size.width

    def get_terminal_size(self) -> Size:
        return self._terminal_size

    def set_terminal_size(self, size: Size) -> None:
        """Set the terminal size for testing"""
        self._terminal_size = size

    def get_screen_content(self) -> dict[Position, CharCell]:
        """Get the entire screen content (all windows combined)"""
        return self._screen_content.copy()

    def get_screen_line(self, y: int) -> str:
        """Get a line from the entire screen"""
        line_chars = []
        for x in range(self._terminal_size.width):
            pos = Position(y, x)
            if pos in self._screen_content:
                line_chars.append(self._screen_content[pos].char)
            else:
                line_chars.append(" ")
        return "".join(line_chars).rstrip()

    def get_screen(self) -> str:
        """Get all lines from the entire screen"""
        return "\n".join(
            self.get_screen_line(y) for y in range(self._terminal_size.height)
        )

    @property
    def cursor_visibility(self) -> int:
        """Get the current cursor visibility"""
        return self._cursor_visibility

    @property
    def cursor_position(self) -> Position:
        """Get the current cursor position"""
        return self._cursor_position[0]
