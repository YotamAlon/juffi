"""Handles the entries display window with columns, scrolling, and navigation"""

import curses
from itertools import islice
from typing import Iterator

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
        self._entries_model.set_visible_rows(self._data_height)

    def _update_needs_redraw(self) -> None:
        self._needs_redraw = True

    @property
    def _data_height(self) -> int:
        return self._entries_win.getmaxyx()[0] - self._HEADER_HEIGHT

    def set_data(self, preserve_line: bool = False) -> None:
        """Update the entries data

        Args:
            preserve_line: If True, try to keep the current row on the same line number
        """
        self._entries_model.set_data(preserve_line=preserve_line)

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
        self._entries_model.set_visible_rows(self._data_height)
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
        start_entry = self._entries_model.scroll_row
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
        scroll_row = self._entries_model.scroll_row

        # Check if old row is visible and update it
        if (
            0 <= old_row < len(self._state.filtered_entries)
            and scroll_row <= old_row < scroll_row + win_height
        ):
            win_row = old_row - scroll_row
            self._draw_single_entry_to_window(
                win_row, old_row, self._state.filtered_entries[old_row]
            )

        # Check if new row is visible and update it
        if (
            0 <= new_row < len(self._state.filtered_entries)
            and scroll_row <= new_row < scroll_row + win_height
        ):
            win_row = new_row - scroll_row
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
        width = self._header_win.getmaxyx()[1] if self._header_win else 80
        visible_cols = self._get_visible_columns(width)
        self._entries_model.move_column(to_the_right, visible_cols)

    def adjust_column_width(self, delta: int) -> None:
        """Adjust width of current column"""
        width = self._header_win.getmaxyx()[1] if self._header_win else 80
        visible_cols = self._get_visible_columns(width)
        self._entries_model.adjust_column_width(delta, visible_cols)

    def get_current_column(self) -> str:
        """Get the currently selected column"""
        width = self._header_win.getmaxyx()[1]
        visible_cols = self._get_visible_columns(width)
        return visible_cols[0] if visible_cols else ""

    def handle_navigation(self, key: int) -> bool:
        """Handle navigation keys, return True if handled"""
        return self._entries_model.handle_navigation(key)

    def goto_line(self, line_num: int) -> None:
        """Go to specific line number (1-based)"""
        self._entries_model.goto_line(line_num)

    def reset(self) -> None:
        """Reset scroll and current row"""
        self._entries_model.reset()
