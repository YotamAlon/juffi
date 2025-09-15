"""Details mode view - handles UI rendering and input delegation"""

import curses
import textwrap

from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
from juffi.viewmodels.details import DetailsViewModel
from juffi.views.entries import EntriesWindow


class DetailsMode:
    """Handles details mode input and drawing logic"""

    _CONTENT_START_LINE = 3

    def __init__(
        self,
        state: JuffiState,
        entries_window: EntriesWindow,
        colors: dict[str, int],
        entries_win: curses.window,
    ) -> None:
        self._colors = colors
        self._entries_win = entries_win

        # Create viewmodel to handle business logic
        self.viewmodel = DetailsViewModel(state, entries_window)

    def handle_input(self, key: int) -> None:
        """Handle input for details mode. Returns True if key was handled."""

        if key == curses.KEY_UP:
            self.viewmodel.navigate_field_up()
        elif key == curses.KEY_DOWN:
            self.viewmodel.navigate_field_down()
        elif key == curses.KEY_LEFT:
            self.viewmodel.navigate_entry_previous()
        elif key == curses.KEY_RIGHT:
            self.viewmodel.navigate_entry_next()

    def draw(self, filtered_entries: list[LogEntry]) -> None:
        """Draw details view"""
        if not filtered_entries:
            return

        entry = self.viewmodel.get_current_entry()
        if not entry:
            return

        # Clear the entries window
        self._entries_win.clear()
        self._entries_win.noutrefresh()
        height, width = self._entries_win.getmaxyx()

        # Draw title
        title = f"Details - Line {entry.line_number}"
        self._entries_win.addstr(0, 1, title[: width - 2], self._colors["HEADER"])
        self._entries_win.addstr(
            1, 1, "─" * min(len(title), width - 2), self._colors["HEADER"]
        )

        fields = self.viewmodel.get_entry_fields(entry)

        content_end_line = height - 3
        available_height = content_end_line - self._CONTENT_START_LINE
        available_height = max(1, available_height)

        # Update scroll position through viewmodel
        self.viewmodel.update_scroll_for_display(available_height, len(fields))

        # Draw visible fields
        scroll_offset = self.viewmodel.scroll_offset
        end_field_idx = min(len(fields), scroll_offset + available_height)

        field_indexes = list(range(scroll_offset, end_field_idx))
        if field_indexes:
            self._draw_fields(field_indexes, fields)

        # Add instructions at the bottom
        current_field = self.viewmodel.current_field
        field_info = (
            f"Field {current_field + 1}/{len(fields)}" if fields else "No fields"
        )
        instructions = (
            f"Press 'd' to return to browse mode,"
            f" ↑/↓ to navigate fields,"
            f" ←/→ to navigate entries | {field_info}"
        )
        self._entries_win.addstr(
            height - 2, 1, instructions[: width - 2], self._colors["INFO"]
        )

        self._entries_win.refresh()

    def enter_mode(self) -> None:
        """Called when entering details mode"""
        self.viewmodel.enter_mode()

    def _draw_fields(
        self, field_indexes: list[int], fields: list[tuple[str, str]]
    ) -> None:

        height, width = self._entries_win.getmaxyx()
        content_end_line = height - 3
        y_pos = self._CONTENT_START_LINE
        max_key_width = min(20, max(len(key) for key, _ in fields) if fields else 0)
        value_start_x = max_key_width + 2
        available_width = width - value_start_x - 1

        current_field = self.viewmodel.current_field

        for field_idx in field_indexes:
            key, value = fields[field_idx]

            if y_pos >= content_end_line:
                break

            is_selected = field_idx == current_field

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
        value_color = self._colors["SELECTED" if is_selected else "DEFAULT"]
        if is_selected:
            lines = self._break_value_into_lines(
                value, available_width, available_lines
            )
            self._write_selected_lines(lines, value_color, *start_yx)
            return len(lines)

        value_str = value.replace("\n", "\\n").replace("\r", "\\r")
        if value_str:
            value_str = textwrap.wrap(value_str, available_width, max_lines=1)[0]

        self._entries_win.addstr(*start_yx, value_str, value_color)
        return 1

    def _draw_field_header(
        self, key: str, is_selected: bool, y_pos: int, max_key_width: int
    ) -> None:
        key_color = self._colors["SELECTED" if is_selected else "HEADER"]

        prefix = "► " if is_selected else "  "
        key_text = f"{prefix}{key}:".ljust(max_key_width + 1)

        self._entries_win.addstr(y_pos, 1, key_text, key_color)

    def _write_selected_lines(
        self, lines: list[str], value_color: int, y_pos: int, value_start_x: int
    ):
        self._entries_win.addstr(y_pos, value_start_x, lines[0], value_color)
        for line in lines[1:]:
            y_pos += 1
            self._entries_win.addstr(y_pos, value_start_x, line, value_color)

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
