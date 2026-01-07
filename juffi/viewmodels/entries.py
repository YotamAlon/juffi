"""Entries viewmodel - handles business logic and state management"""

import curses
import logging
from typing import Callable

from juffi.models.juffi_model import JuffiState

logger = logging.getLogger(__name__)


class EntriesModel:
    """ViewModel class for the entries window"""

    def __init__(self, state: JuffiState, needs_redraw: Callable[[], None]) -> None:
        self._state = state
        self._scroll_row: int = 0
        self._old_data_count: int = 0
        self._visible_rows: int = 1
        self._saved_line_number: int | None = None

        for field in [
            "current_mode",
            "terminal_size",
            "entries",
            "current_row",
            "current_column",
            "sort_column",
            "sort_reverse",
            "filters",
            "search_term",
            "columns",
            "filtered_entries",
        ]:
            self._state.register_watcher(field, needs_redraw)

    @property
    def scroll_row(self) -> int:
        """Get the current scroll row"""
        return self._scroll_row

    def set_visible_rows(self, visible_rows: int) -> None:
        """Update the number of visible rows"""
        self._visible_rows = visible_rows

    def prepare_for_data_update(self) -> None:
        """Save current line number before data changes"""
        if self._saved_line_number is not None:
            return
        if self._state.current_row is not None:
            filtered = self._state.filtered_entries
            self._saved_line_number = filtered[self._state.current_row].line_number

    def set_data(self, preserve_line: bool = False) -> None:
        """Update the entries data and adjust current row position

        Args:
            preserve_line: If True, try to keep the current row on the same line number
        """
        current_line_number = self._get_current_line_number(preserve_line)

        if self._state.current_row is None:
            logger.info("No current row. Sort reversed is %s", self._state.sort_reverse)
            if self._state.sort_reverse:
                self._state.current_row = 0
            else:
                self._state.current_row = max(0, len(self._state.filtered_entries) - 1)
        elif current_line_number is not None:
            new_row = None
            for idx, entry in enumerate(self._state.filtered_entries):
                if entry.line_number == current_line_number:
                    new_row = idx
                    break

            if new_row is not None:
                self._state.current_row = new_row
                self._saved_line_number = None
            else:
                if self._state.current_row >= len(self._state.filtered_entries):
                    self._state.current_row = max(
                        0, len(self._state.filtered_entries) - 1
                    )
        elif self._state.sort_reverse and self._state.current_row == 0:
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

        self._set_scroll_row()

        self._old_data_count = len(self._state.filtered_entries)

    def _get_current_line_number(self, preserve_line: bool) -> int | None:
        if preserve_line and self._saved_line_number is not None:
            return self._saved_line_number
        return None

    def _set_scroll_row(self) -> None:
        self._scroll_row = min(self._scroll_row, len(self._state.filtered_entries))
        if self._state.current_row is None:
            return

        if self._state.current_row < self._scroll_row:
            self._scroll_row = self._state.current_row
        elif self._state.current_row >= self._scroll_row + self._visible_rows:
            self._scroll_row = self._state.current_row - self._visible_rows + 1

    def handle_navigation(self, key: int) -> bool:
        """Handle navigation keys, return True if handled"""
        if self._state.current_row is None:
            return False

        if key == curses.KEY_UP:
            self._state.current_row = max(0, self._state.current_row - 1)
        elif key == curses.KEY_DOWN:
            self._state.current_row = min(
                len(self._state.filtered_entries) - 1,
                self._state.current_row + 1,
            )
        elif key == curses.KEY_PPAGE:
            self._state.current_row = max(
                0, self._state.current_row - self._visible_rows
            )
            self._scroll_row = max(0, self._scroll_row - self._visible_rows)
        elif key == curses.KEY_NPAGE:
            self._state.current_row = min(
                len(self._state.filtered_entries) - 1,
                self._state.current_row + self._visible_rows,
            )
            self._scroll_row = min(
                len(self._state.filtered_entries) - self._visible_rows,
                self._scroll_row + self._visible_rows,
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

        if self._state.current_row < self._scroll_row:
            self._scroll_row = self._state.current_row
        elif self._state.current_row >= self._scroll_row + self._visible_rows:
            self._scroll_row = self._state.current_row - self._visible_rows + 1

        return True

    def move_column(self, to_the_right: bool, visible_cols: list[str]) -> None:
        """Move column left or right"""
        if not self._state.columns or not visible_cols:
            return

        current_col = visible_cols[0]
        current_idx = self._state.columns.index(current_col)

        new_idx = current_idx + (1 if to_the_right else -1)
        if 0 <= new_idx < len(self._state.columns):
            self._state.move_column(current_idx, new_idx)
            self._state.current_column = self._state.columns[new_idx].name

    def adjust_column_width(self, delta: int, visible_cols: list[str]) -> None:
        """Adjust width of current column"""
        if visible_cols:
            col = visible_cols[0]
            current_width = self._state.columns[col].width
            new_width = max(5, min(100, current_width + delta))
            self._state.set_column_width(col, new_width)

    def goto_line(self, row_num: int) -> None:
        """Go to specific row number in the filtered entries."""
        if not self._state.filtered_entries:
            return

        row_num = max(0, min(row_num, len(self._state.filtered_entries) - 1))

        self._state.current_row = row_num
        self._scroll_row = max(0, row_num - self._visible_rows // 2)
        self._saved_line_number = None

    def reset(self) -> None:
        """Reset scroll and current row"""
        self._state.current_row = (
            0
            if self._state.sort_reverse
            else max(0, len(self._state.filtered_entries) - 1)
        )
        self._state.current_column = "#"
        self._scroll_row = 0
