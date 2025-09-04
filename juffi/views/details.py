import curses
import textwrap

from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
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
        self._state = state
        self._entries_window = entries_window
        self._colors = colors
        self._entries_win = entries_win

        self._field_count: int = 0
        self._current_field: int = 0
        self._scroll_offset: int = 0

    def handle_input(self, key: int) -> None:
        """Handle input for details mode. Returns True if key was handled."""

        if key == curses.KEY_UP:
            if self._current_field > 0:
                self._current_field -= 1
        elif key == curses.KEY_DOWN:
            if self._current_field < self._field_count - 1:
                self._current_field += 1
        elif key == curses.KEY_LEFT:
            self._entries_window.handle_navigation(curses.KEY_UP)
            self._reset_view()
        elif key == curses.KEY_RIGHT:
            self._entries_window.handle_navigation(curses.KEY_DOWN)
            self._reset_view()

    def draw(self, filtered_entries: list[LogEntry]) -> None:
        """Draw details view"""
        if not filtered_entries:
            return

        current_row = self._entries_window.get_current_row()
        if current_row >= len(filtered_entries):
            return

        entry = filtered_entries[current_row]

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

        fields = self._get_entry_fields(entry)

        # Ensure current field index is valid
        if self._current_field >= len(fields):
            self._current_field = max(0, len(fields) - 1)

        content_end_line = height - 3
        available_height = content_end_line - self._CONTENT_START_LINE
        available_height = max(1, available_height)

        # Simple scrolling: ensure selected field is visible
        if self._current_field < self._scroll_offset:
            self._scroll_offset = self._current_field
        elif self._current_field >= self._scroll_offset + available_height:
            self._scroll_offset = self._current_field - available_height + 1

        # Ensure scroll offset is not negative and not beyond the last possible position
        max_scroll = max(0, len(fields) - available_height)
        self._scroll_offset = max(0, min(self._scroll_offset, max_scroll))

        # Draw visible fields
        end_field_idx = min(len(fields), self._scroll_offset + available_height)

        field_indexes = list(range(self._scroll_offset, end_field_idx))
        if field_indexes:
            self._draw_fields(field_indexes, fields)

        # Add instructions at the bottom
        field_info = (
            f"Field {self._current_field + 1}/{len(fields)}" if fields else "No fields"
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

    def enter_mode(self):
        """Called when entering details mode"""

        self._reset_view()
        current_row = self._entries_window.get_current_row()
        entry = self._state.filtered_entries[current_row]
        field_count = len(entry.data.keys())
        self._field_count = field_count

    def _reset_view(self):
        self._current_field = 0
        self._scroll_offset = 0

    def _draw_fields(self, field_indexes: list[int], fields: list[tuple[str, str]]):

        height, width = self._entries_win.getmaxyx()
        content_end_line = height - 3
        y_pos = self._CONTENT_START_LINE
        max_key_width = min(20, max(len(key) for key, _ in fields) if fields else 0)

        for field_idx in field_indexes:
            key, value = fields[field_idx]

            if y_pos >= content_end_line:
                break

            is_selected = field_idx == self._current_field

            key_color = self._colors["SELECTED" if is_selected else "HEADER"]
            value_color = self._colors["SELECTED" if is_selected else "DEFAULT"]

            prefix = "► " if is_selected else "  "
            key_text = f"{prefix}{key}:".ljust(max_key_width + 1)
            self._entries_win.addstr(y_pos, 1, key_text[: width - 2], key_color)

            value_start_x = max_key_width + 2
            available_width = width - value_start_x - 1
            if is_selected:
                lines = self._break_value_into_lines(
                    value, available_width, content_end_line - y_pos
                )
                self._write_selected_lines(lines, value_color, y_pos, value_start_x)
                y_pos += len(lines)
            else:
                value_str = value.replace("\n", "\\n").replace("\r", "\\r")
                if value_str:
                    [value_str] = textwrap.wrap(value_str, available_width, max_lines=1)

                self._entries_win.addstr(y_pos, value_start_x, value_str, value_color)
                y_pos += 1

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

    @staticmethod
    def _get_entry_fields(entry: LogEntry) -> list[tuple[str, str]]:
        # Get all fields from the entry (excluding missing ones)
        fields = []
        # Add JSON fields if it's valid JSON
        if entry.is_valid_json:
            for key in sorted(entry.data.keys()):
                value = entry.get_value(key)
                fields.append((key, value))
        else:
            # For non-JSON entries, show the raw message
            fields.append(("message", entry.raw_line))
        return fields
