"""Details mode view - handles UI rendering and input delegation"""

import curses
import textwrap

from juffi.helpers.curses_utils import Color, Position
from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
from juffi.output_controller import Window
from juffi.viewmodels.details import DetailsViewModel


class DetailsMode:
    """Handles details mode input and drawing logic"""

    _CONTENT_START_LINE = 3

    def __init__(
        self,
        state: JuffiState,
        entries_win: Window,
    ) -> None:
        self._entries_win = entries_win
        self._needs_redraw_flag = True
        self._last_entry_id: str | None = None
        self._last_window_size: tuple[int, int] | None = None

        # Create viewmodel to handle business logic
        self.viewmodel = DetailsViewModel(state)

        # Register watchers for state changes that require redraw
        for field in ["filtered_entries", "current_row"]:
            state.register_watcher(field, self.force_redraw)

    def handle_input(self, key: int) -> None:
        """Handle input for details mode. Returns True if key was handled."""

        if key == curses.KEY_UP:
            self.viewmodel.navigate_field_up()
            self._needs_redraw_flag = True
        elif key == curses.KEY_DOWN:
            self.viewmodel.navigate_field_down()
            self._needs_redraw_flag = True
        elif key == curses.KEY_LEFT:
            self.viewmodel.navigate_entry_previous()
            self._needs_redraw_flag = True
        elif key == curses.KEY_RIGHT:
            self.viewmodel.navigate_entry_next()
            self._needs_redraw_flag = True

    def draw(self, filtered_entries: list[LogEntry]) -> None:
        """Draw details view"""
        if not filtered_entries:
            return

        entry = self.viewmodel.get_current_entry()
        if not entry:
            return

        # Check if redraw is needed
        if not self._needs_redraw():
            return

        self._entries_win.clear()
        self._entries_win.noutrefresh()
        size = self._entries_win.getmaxyx()

        self._draw_title(entry, size.width)

        fields = self.viewmodel.get_entry_fields(entry)

        content_end_line = size.height - 3
        available_height = max(1, content_end_line - self._CONTENT_START_LINE)

        self.viewmodel.update_scroll_for_display(available_height, len(fields))

        scroll_offset = self.viewmodel.scroll_offset
        end_field_idx = min(len(fields), scroll_offset + available_height)

        field_indexes = list(range(scroll_offset, end_field_idx))
        if field_indexes:
            self._draw_fields(field_indexes, fields)

        self._draw_instructions(fields, size.height, size.width)

        self._entries_win.refresh()

        self._needs_redraw_flag = False
        self._last_entry_id = f"{entry.line_number}:{hash(entry.raw_line)}"
        self._last_window_size = (size.height, size.width)

    def _draw_title(self, entry, width):
        title = f"Details - Line {entry.line_number}"
        self._entries_win.addstr(Position(0, 1), title[: width - 2], color=Color.HEADER)
        self._entries_win.addstr(
            Position(1, 1), "─" * min(len(title), width - 2), color=Color.HEADER
        )

    def _draw_instructions(self, fields, height, width):
        current_field = self.viewmodel.current_field
        field_info = (
            f"Field {current_field + 1}/{len(fields)}" if fields else "No fields"
        )
        instructions = (
            f"Press 'd' to return to browse mode,"
            f" ↑/↓ to navigate fields,"
            f" ←/→ to navigate entries | {field_info}"
        )

        text_lines = textwrap.wrap(instructions, width - 2, max_lines=2)
        self._entries_win.addstr(
            Position(height - 2, 1), text_lines[0], color=Color.INFO
        )
        if len(text_lines) > 1:
            self._entries_win.addstr(
                Position(height - 1, 1), text_lines[1], color=Color.INFO
            )

    def enter_mode(self) -> None:
        """Called when entering details mode"""
        self.viewmodel.enter_mode()
        self._needs_redraw_flag = True

    def _needs_redraw(self) -> bool:
        """Check if the details view needs to be redrawn"""
        if self._needs_redraw_flag:
            return True

        size = self._entries_win.getmaxyx()
        current_size = (size.height, size.width)
        if self._last_window_size != current_size:
            self._needs_redraw_flag = True
            return True

        entry = self.viewmodel.get_current_entry()
        if not entry:
            return False

        current_entry_id = f"{entry.line_number}:{hash(entry.raw_line)}"
        if self._last_entry_id != current_entry_id:
            self._needs_redraw_flag = True
            return True

        return False

    def force_redraw(self) -> None:
        """Force a redraw on the next draw call"""
        self._needs_redraw_flag = True

    def resize(self) -> None:
        """Handle window resize"""
        self._needs_redraw_flag = True

    def _draw_fields(
        self, field_indexes: list[int], fields: list[tuple[str, str]]
    ) -> None:

        size = self._entries_win.getmaxyx()
        content_end_line = size.height - self._CONTENT_START_LINE
        y_pos = self._CONTENT_START_LINE
        max_key_width = max(len(key) for key, _ in fields) + 3 if fields else 0
        max_value_width = max(len(value) for _, value in fields) if fields else 0
        if max_key_width + max_value_width > size.width:
            max_key_width = max(size.width - max_value_width, 20)

        value_start_x = max_key_width + 2
        available_width = size.width - value_start_x - 1

        for field_idx in field_indexes:
            key, value = fields[field_idx]

            if y_pos >= content_end_line:
                break

            is_selected = field_idx == self.viewmodel.current_field

            self._draw_field_header(key, is_selected, y_pos, max_key_width)

            y_pos += self._draw_field_value(
                value,
                (y_pos, value_start_x),
                available_width,
                content_end_line - y_pos,
                is_selected,
            )

    def _draw_field_value(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        value: str,
        start_yx: tuple[int, int],
        available_width: int,
        available_lines: int,
        is_selected: bool,
    ) -> int:
        value_color = Color.SELECTED if is_selected else Color.DEFAULT
        if is_selected:
            lines = self._break_value_into_lines(
                value, available_width, available_lines
            )
            self._write_selected_lines(lines, value_color, *start_yx)
            return len(lines)

        value_str = value.replace("\n", "\\n").replace("\r", "\\r")
        if value_str:
            value_str = textwrap.wrap(value_str, available_width, max_lines=1)[0]

        self._entries_win.addstr(Position(*start_yx), value_str, color=value_color)
        return 1

    def _draw_field_header(
        self, key: str, is_selected: bool, y_pos: int, max_key_width: int
    ) -> None:
        key_color = Color.SELECTED if is_selected else Color.HEADER

        prefix = "► " if is_selected else "  "
        key_text = f"{prefix}{key}:".ljust(max_key_width + 3)

        self._entries_win.addstr(Position(y_pos, 1), key_text, color=key_color)

    def _write_selected_lines(
        self, lines: list[str], value_color: Color, y_pos: int, value_start_x: int
    ):
        self._entries_win.addstr(
            Position(y_pos, value_start_x), lines[0], color=value_color
        )
        for line in lines[1:]:
            y_pos += 1
            self._entries_win.addstr(
                Position(y_pos, value_start_x), line, color=value_color
            )

    @staticmethod
    def _break_value_into_lines(
        value: str, available_width: int, available_lines: int
    ) -> list[str]:
        value_lines = value.split("\n")
        lines: list[str] = []
        for line in value_lines:
            line_lines = textwrap.wrap(
                line,
                available_width,
                max_lines=available_lines - len(lines),
            )
            lines.extend(line_lines or [""])

        if len(lines) > available_lines:
            lines = lines[: available_lines - 1] + ["[...]"]
        return lines
