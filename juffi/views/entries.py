"""Handles the entries display window with columns, scrolling, and navigation"""

import curses
from itertools import islice
from typing import Iterator

from juffi.helpers.list_utils import find_first_index
from juffi.models.column import Column
from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
from juffi.viewmodels.entries import EntriesModel


class EntriesWindow:  # pylint: disable=too-many-instance-attributes
    """Handles the entries display window with columns, scrolling, and navigation"""

    _HEADER_HEIGHT = 2

    def __init__(
        self,
        state: JuffiState,
        colors: dict[str, int],
        entries_win: curses.window,
    ) -> None:
        self._state = state
        self._colors = colors
        self._entries_model = EntriesModel(state, self._update_needs_redraw)

        self._needs_redraw = True
        self._current_row: int = 0
        self._scroll_row: int = 0
        self._old_data_count: int = 0

        self._entries_win = entries_win
        _, width = entries_win.getmaxyx()
        self._header_win: curses.window = self._entries_win.derwin(  # type: ignore
            self._HEADER_HEIGHT, width, 0, 0
        )

        self._data_win: curses.window = self._entries_win.derwin(  # type: ignore
            self._data_height,
            width,
            self._HEADER_HEIGHT,
            0,
        )

    def _update_needs_redraw(self) -> None:
        self._needs_redraw = True

    @property
    def _data_height(self) -> int:
        return self._entries_win.getmaxyx()[0] - self._HEADER_HEIGHT

    def set_data(self) -> None:
        """Update the entries data"""

        if self._state.sort_reverse and self._state.current_row == 0:
            pass
        elif (
            not self._state.sort_reverse
            and self._state.current_row == self._old_data_count - 1
        ):
            self._state.current_row = len(self._state.filtered_entries) - 1
        elif self._state.sort_reverse:
            self._state.current_row += (
                len(self._state.filtered_entries) - self._old_data_count
            )

        if self._state.current_row >= len(self._state.filtered_entries):
            self._state.current_row = max(0, len(self._state.filtered_entries) - 1)

        self._scroll_row = min(self._scroll_row, len(self._state.filtered_entries))
        self._old_data_count = len(self._state.filtered_entries)

    def _get_visible_columns(self, width: int) -> list[str]:
        """Get columns that fit in the given width"""
        visible_cols = []
        total_width = 0

        for col in self._iter_cols_from_current():
            if total_width + col.width > width - 2:
                break
            visible_cols.append(col.name)
            total_width += col.width

        return visible_cols

    def _iter_cols_from_current(self) -> Iterator[Column]:
        try:
            current_index = self._state.columns.index(self._state.current_column)
        except KeyError:
            current_index = 0

        return islice(
            self._state.columns.values(),
            current_index,
            None,
        )

    def resize(self) -> None:
        """Resize the entries window"""
        _, width = self._entries_win.getmaxyx()
        self._header_win.resize(self._HEADER_HEIGHT, width)
        self._header_win.mvderwin(0, 0)
        self._data_win.resize(self._data_height, width)
        self._data_win.mvderwin(self._HEADER_HEIGHT, 0)

    def draw(self) -> None:
        """Main drawing method with optimized redrawing"""
        if self._needs_redraw:
            self._draw_column_headers_to_window()
            self._draw_entries_to_window()

        self._needs_redraw = False

    def _draw_column_headers_to_window(self) -> None:
        """Draw column headers to the window"""
        self._header_win.clear()

        _, max_x = self._header_win.getmaxyx()

        x_pos = 1
        for col in self._iter_cols_from_current():
            visible_width = min(col.width, max_x - x_pos - 1)
            header_text = col.name[:visible_width].ljust(visible_width)

            color = self._colors["HEADER"]
            if col.name == self._state.sort_column:
                header_text = header_text[:-2] + (
                    " ↓" if self._state.sort_reverse else " ↑"
                )
                color |= curses.A_UNDERLINE

            self._header_win.addstr(0, x_pos, header_text, color)
            x_pos += visible_width + 1
            if x_pos >= max_x:
                break

        # Draw separator line
        separator_width = min(max_x - 2, x_pos - 1)
        self._header_win.addstr(1, 1, "─" * separator_width, self._colors["HEADER"])
        self._header_win.refresh()

    def _draw_entries_to_window(self) -> None:
        """Draw visible entries directly to the window"""
        self._data_win.clear()

        win_height, _ = self._data_win.getmaxyx()

        # Calculate which entries are visible
        start_entry = self._scroll_row
        end_entry = min(start_entry + win_height, len(self._state.filtered_entries))

        for win_row, entry_idx in enumerate(range(start_entry, end_entry)):
            entry = self._state.filtered_entries[entry_idx]
            self._draw_single_entry_to_window(win_row, entry_idx, entry)

        self._data_win.refresh()

    def _draw_single_entry_to_window(
        self, win_row: int, entry_idx: int, entry: LogEntry
    ) -> None:
        """Draw a single entry to the window at the specified window row"""
        is_selected = entry_idx == self._state.current_row
        _, win_width = self._data_win.getmaxyx()

        x_pos = 1
        for col in self._iter_cols_from_current():
            value = (
                entry.get_value(col.name)[: col.width]
                .ljust(col.width)
                .replace("\n", "\\n")
            )

            color = self._colors["DEFAULT"]
            if is_selected:
                color = self._colors["SELECTED"]
            elif entry.level:
                level_color = self._get_color_for_level(entry.level.upper())
                if level_color:
                    color = level_color

            visible_width = min(win_width - x_pos - 1, col.width)
            visible_value = value[:visible_width]
            self._data_win.addstr(win_row, x_pos, visible_value, color)

            x_pos += col.width + 1
            if x_pos >= win_width:
                break

    def _get_color_for_level(self, level: str) -> int | None:
        color = None
        if level in ["ERROR", "FATAL"]:
            color = self._colors["ERROR"]
        elif level in ["WARN", "WARNING"]:
            color = self._colors["WARNING"]
        elif level in ["INFO"]:
            color = self._colors["INFO"]
        elif level in ["DEBUG", "TRACE"]:
            color = self._colors["DEBUG"]
        return color

    def _update_selection_rows(self, old_row: int, new_row: int) -> None:
        """Update only the rows that changed selection status"""
        win_height, _ = self._data_win.getmaxyx()

        # Check if old row is visible and update it
        if (
            0 <= old_row < len(self._state.filtered_entries)
            and self._scroll_row <= old_row < self._scroll_row + win_height
        ):
            win_row = old_row - self._scroll_row
            self._draw_single_entry_to_window(
                win_row, old_row, self._state.filtered_entries[old_row]
            )

        # Check if new row is visible and update it
        if (
            0 <= new_row < len(self._state.filtered_entries)
            and self._scroll_row <= new_row < self._scroll_row + win_height
        ):
            win_row = new_row - self._scroll_row
            self._draw_single_entry_to_window(
                win_row, new_row, self._state.filtered_entries[new_row]
            )

        self._data_win.refresh()

    @property
    def _scroll_x(self) -> int:
        scroll_x = 0
        for i in range(self._state.columns.index(self._state.current_column)):
            if i < len(self._state.columns):
                scroll_x += next(islice(self._state.columns.values(), i, None)).width
        return scroll_x

    def move_column(self, to_the_right: bool) -> None:
        """Move column left or right"""
        if not self._state.columns:
            return

        width = self._header_win.getmaxyx()[1] if self._header_win else 80
        visible_cols = self._get_visible_columns(width)
        if not visible_cols:
            return

        current_col = visible_cols[0]
        current_idx = self._state.columns.index(current_col)

        new_idx = current_idx + (1 if to_the_right else -1)
        if 0 <= new_idx < len(self._state.columns):
            self._state.move_column(current_idx, new_idx)
            self._state.current_column = self._state.columns[new_idx].name

    def adjust_column_width(self, delta: int) -> None:
        """Adjust width of current column"""
        width = self._header_win.getmaxyx()[1] if self._header_win else 80
        visible_cols = self._get_visible_columns(width)
        if visible_cols:
            col = visible_cols[0]
            current_width = self._state.columns[col].width
            new_width = max(5, min(100, current_width + delta))
            self._state.set_column_width(col, new_width)

    def get_current_column(self) -> str:
        """Get the currently selected column"""
        width = self._header_win.getmaxyx()[1]
        visible_cols = self._get_visible_columns(width)
        return visible_cols[0] if visible_cols else ""

    def get_current_row(self) -> int:
        """Get the currently selected row"""
        return self._state.current_row

    def handle_navigation(self, key: int) -> bool:
        """Handle navigation keys, return True if handled"""
        if not self._state.filtered_entries:
            return False

        visible_rows = self._data_win.getmaxyx()[0]

        if key == curses.KEY_UP:
            self._state.current_row = max(0, self._state.current_row - 1)
        elif key == curses.KEY_DOWN:
            self._state.current_row = min(
                len(self._state.filtered_entries) - 1,
                self._state.current_row + 1,
            )
        elif key == curses.KEY_PPAGE:
            self._state.current_row = max(0, self._state.current_row - visible_rows)
            self._scroll_row = max(0, self._scroll_row - visible_rows)
        elif key == curses.KEY_NPAGE:
            self._state.current_row = min(
                len(self._state.filtered_entries) - 1,
                self._state.current_row + visible_rows,
            )
            self._scroll_row = min(
                len(self._state.filtered_entries) - visible_rows,
                self._scroll_row + visible_rows,
            )
        elif key == curses.KEY_HOME:
            self._state.current_row = 0
        elif key == curses.KEY_END:
            self._state.current_row = max(0, len(self._state.filtered_entries) - 1)
        elif key == curses.KEY_LEFT:
            self._state.current_column = self._state.columns[
                max(0, self._state.columns.index(self._state.current_column) - 1)
            ].name
        elif key == curses.KEY_RIGHT:
            self._state.current_column = self._state.columns[
                min(
                    len(self._state.columns) - 1,
                    self._state.columns.index(self._state.current_column) + 1,
                )
            ].name
        else:
            return False

        # Update scroll position to keep current row visible
        if self._state.current_row < self._scroll_row:
            self._scroll_row = self._state.current_row
        elif self._state.current_row >= self._scroll_row + visible_rows:
            self._scroll_row = self._state.current_row - visible_rows + 1

        return True

    def goto_line(self, line_num: int) -> None:
        """Go to specific line number (1-based)"""

        if line_num < 1:
            return

        if line_num <= len(self._state.filtered_entries):
            line_idx = find_first_index(
                self._state.filtered_entries,
                lambda e: e.line_number == line_num,
            )
            if line_idx is None:
                return
        else:
            line_idx, _ = max(
                enumerate(self._state.filtered_entries),
                key=lambda ie: ie[1].line_number,
            )

        self._state.current_row = line_idx

        visible_rows = self._data_win.getmaxyx()[0]
        self._scroll_row = max(0, line_idx - visible_rows // 2)

    def reset(self) -> None:
        """Reset scroll and current row"""
        self._state.current_row = 0
        self._state.current_column = "#"
        self._scroll_row = 0
