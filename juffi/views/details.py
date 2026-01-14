"""Details mode view - handles UI rendering and input delegation"""

import curses
import textwrap

from juffi.helpers.curses_utils import Color, Position, Size
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

        if self.viewmodel.in_fullscreen_mode:
            self._handle_fullscreen_input(key)
        elif key == curses.KEY_UP:
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
        elif key == ord("\n"):
            self.viewmodel.toggle_fullscreen_mode()
            self._needs_redraw_flag = True

    def draw(self, filtered_entries: list[LogEntry]) -> None:
        """Draw details view"""
        if not filtered_entries:
            return

        entry = self.viewmodel.get_current_entry()
        if not entry:
            return

        if not self._needs_redraw():
            return

        self._entries_win.clear()
        self._entries_win.noutrefresh()
        size = self._entries_win.getmaxyx()

        if self.viewmodel.in_fullscreen_mode:
            self._draw_fullscreen_field(entry, size)
        else:
            self._draw_normal_view(entry, size)

        self._entries_win.refresh()

        self._needs_redraw_flag = False
        self._last_entry_id = f"{entry.line_number}:{hash(entry.raw_line)}"
        self._last_window_size = (size.height, size.width)

    def _draw_title(self, entry: LogEntry, width: int):
        title = f"Details - Line {entry.line_number}"
        self._entries_win.addstr(Position(0, 1), title[: width - 2], color=Color.HEADER)
        self._entries_win.addstr(
            Position(1, 1), "─" * min(len(title), width - 2), color=Color.HEADER
        )

    def _draw_instructions(self, fields: list[tuple[str, str]], size: Size):
        current_field = self.viewmodel.current_field
        field_info = (
            f"Field {current_field + 1}/{len(fields)}" if fields else "No fields"
        )
        instructions = (
            f"Press 'd' to return, ↑/↓ fields, ←/→ entries, "
            f"Enter fullscreen | {field_info}"
        )

        self._draw_instructions_lines(instructions, size)

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
                Position(y_pos, value_start_x),
                Size(available_width, content_end_line - y_pos),
                is_selected,
            )

    def _draw_field_value(
        self,
        value: str,
        start_yx: Position,
        available_size: Size,
        is_selected: bool,
    ) -> int:
        value_color = Color.SELECTED if is_selected else Color.DEFAULT
        if is_selected:
            all_lines = self._break_value_into_lines(value, available_size.width)
            visible_lines = all_lines[: available_size.height]

            if len(all_lines) > available_size.height:
                visible_lines = all_lines[: available_size.height - 1]
                remaining = len(all_lines) - len(visible_lines)
                visible_lines.append(
                    f"[...{remaining} more lines, Enter for fullscreen]"
                )

            if visible_lines:
                self._write_selected_lines(visible_lines, value_color, *start_yx)
            return len(visible_lines)

        value_str = value.replace("\n", "\\n").replace("\r", "\\r")
        if value_str:
            value_str = textwrap.wrap(value_str, available_size.width, max_lines=1)[0]

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

    def _draw_normal_view(self, entry: LogEntry, size: Size) -> None:
        """Draw the normal details view with all fields"""
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

        self._draw_instructions(fields, size)

    def _draw_fullscreen_field(self, entry: LogEntry, size: Size) -> None:
        fields = self.viewmodel.get_entry_fields(entry)
        key, value = fields[self.viewmodel.current_field]

        title = f"Field: {key} (Line {entry.line_number})"
        self._entries_win.addstr(
            Position(0, 1), title[: size.width - 2], color=Color.HEADER
        )
        self._entries_win.addstr(
            Position(1, 1), "─" * min(len(title), size.width - 2), color=Color.HEADER
        )

        content_end = size.height - self._CONTENT_START_LINE
        available_height = max(1, content_end - self._CONTENT_START_LINE)
        all_lines = self._break_value_into_lines(value, size.width - 2)

        scroll_offset = self.viewmodel.field_content_scroll_offset
        visible_lines = all_lines[scroll_offset : scroll_offset + available_height]

        for i, line in enumerate(visible_lines):
            self._entries_win.addstr(
                Position(self._CONTENT_START_LINE + i, 1), line, color=Color.DEFAULT
            )

        self._draw_fullscreen_instructions(
            scroll_offset, size, len(all_lines), len(visible_lines)
        )

    def _draw_fullscreen_instructions(
        self, scroll_offset: int, size: Size, total_lines: int, visible_lines: int
    ):
        end_line = scroll_offset + visible_lines
        scroll_info = f"Lines {scroll_offset + 1}-{end_line} of {total_lines}"
        instructions = (
            f"Press Enter/Esc to exit, ↑/↓ or PgUp/PgDn to scroll | {scroll_info}"
        )
        self._draw_instructions_lines(instructions, size)

    def _draw_instructions_lines(self, instructions: str, size: Size):
        text_lines = textwrap.wrap(instructions, size.width - 2, max_lines=2)
        self._entries_win.addstr(
            Position(size.height - 2, 1), text_lines[0], color=Color.INFO
        )
        if len(text_lines) > 1:
            self._entries_win.addstr(
                Position(size.height - 1, 1), text_lines[1], color=Color.INFO
            )

    def _handle_fullscreen_input(self, key: int) -> None:
        """Handle input when in fullscreen mode"""
        if key in {ord("\n"), 27}:
            self.viewmodel.exit_fullscreen_mode()
            self._needs_redraw_flag = True
        elif key == curses.KEY_UP:
            self._handle_fullscreen_line_up()
        elif key == curses.KEY_DOWN:
            self._handle_fullscreen_line_down()
        elif key == curses.KEY_PPAGE:
            self._handle_fullscreen_page_up()
        elif key == curses.KEY_NPAGE:
            self._handle_fullscreen_page_down()

    def _handle_fullscreen_line_up(self) -> None:
        """Handle up arrow in fullscreen mode"""
        self.viewmodel.scroll_field_content_up(1)
        self._needs_redraw_flag = True

    def _handle_fullscreen_line_down(self) -> None:
        """Handle down arrow in fullscreen mode"""
        all_lines = self._get_field_lines(self._entries_win.getmaxyx())
        self.viewmodel.scroll_field_content_down(1, len(all_lines))
        self._needs_redraw_flag = True

    def _handle_fullscreen_page_up(self) -> None:
        """Handle page up in fullscreen mode"""
        size = self._entries_win.getmaxyx()
        page_size = max(1, size.height - 6)
        self.viewmodel.scroll_field_content_up(page_size)
        self._needs_redraw_flag = True

    def _handle_fullscreen_page_down(self) -> None:
        """Handle page down in fullscreen mode"""
        size = self._entries_win.getmaxyx()
        all_lines = self._get_field_lines(size)

        if not all_lines:
            return
        page_size = max(1, size.height - 6)
        self.viewmodel.scroll_field_content_down(page_size, len(all_lines))
        self._needs_redraw_flag = True

    def _get_field_lines(self, size: Size):
        entry = self.viewmodel.get_current_entry()
        if not entry:
            return None

        fields = self.viewmodel.get_entry_fields(entry)
        if not fields or self.viewmodel.current_field >= len(fields):
            return None

        _, value = fields[self.viewmodel.current_field]
        available_width = size.width - 2
        all_lines = self._break_value_into_lines(value, available_width)
        return all_lines

    @staticmethod
    def _break_value_into_lines(value: str, available_width: int) -> list[str]:
        """Break value into all lines without truncation"""
        value_lines = value.split("\n")
        lines: list[str] = []
        for line in value_lines:
            if not line:
                lines.append("")
            else:
                wrapped = textwrap.wrap(line, available_width)
                lines.extend(wrapped if wrapped else [""])
        return lines
