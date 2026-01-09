"""Handles the entries display window with columns, scrolling, and navigation"""

from itertools import islice
from typing import Iterator

from juffi.helpers.curses_utils import Color, Position, Size, TextAttribute, Viewport
from juffi.models.column import Column
from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
from juffi.output_controller import Window
from juffi.viewmodels.entries import EntriesModel

COLOR_LEVEL_MAP: dict[str, Color] = {
    "ERROR": Color.ERROR,
    "FATAL": Color.ERROR,
    "WARN": Color.WARNING,
    "WARNING": Color.WARNING,
    "INFO": Color.INFO,
    "DEBUG": Color.DEBUG,
    "TRACE": Color.DEBUG,
}


class EntriesWindow:  # pylint: disable=too-many-instance-attributes
    """Handles the entries display window with columns, scrolling, and navigation"""

    _HEADER_HEIGHT = 2

    def __init__(
        self,
        state: JuffiState,
        entries_win: Window,
    ) -> None:
        self._state = state
        self._entries_model = EntriesModel(state, self._update_needs_redraw)

        self._needs_redraw = True

        self._entries_win = entries_win
        size = entries_win.getmaxyx()
        self._header_win: Window = self._entries_win.derwin(
            Viewport(Position(0, 0), Size(self._HEADER_HEIGHT, size.width))
        )

        self._data_win: Window = self._entries_win.derwin(
            Viewport(
                Position(self._HEADER_HEIGHT, 0), Size(self._data_height, size.width)
            )
        )
        self._entries_model.set_visible_rows(self._data_height)

    def _update_needs_redraw(self) -> None:
        self._needs_redraw = True

    @property
    def _data_height(self) -> int:
        return self._entries_win.getmaxyx().height - self._HEADER_HEIGHT

    def prepare_for_data_update(self) -> None:
        """Prepare for data update by saving current line number"""
        self._entries_model.prepare_for_data_update()

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
        size = self._entries_win.getmaxyx()
        self._header_win.resize(Size(self._HEADER_HEIGHT, size.width))
        self._header_win.mvderwin(Position(0, 0))
        self._data_win.resize(Size(self._data_height, size.width))
        self._entries_model.set_visible_rows(self._data_height)
        self._data_win.mvderwin(Position(self._HEADER_HEIGHT, 0))

    def draw(self) -> None:
        """Main drawing method with optimized redrawing"""
        if self._needs_redraw:
            self._draw_column_headers_to_window()
            self._draw_entries_to_window()

        self._needs_redraw = False

    def _draw_column_headers_to_window(self) -> None:
        """Draw column headers to the window"""
        self._header_win.clear()

        size = self._header_win.getmaxyx()

        x_pos = 1
        for col in self._iter_cols_from_current():
            visible_width = min(col.width, size.width - x_pos - 1)
            header_text = col.name[:visible_width].ljust(visible_width)

            attributes = None
            if col.name == self._state.sort_column:
                header_text = header_text[:-2] + (
                    " ↓" if self._state.sort_reverse else " ↑"
                )
                attributes = [TextAttribute.UNDERLINE]

            self._header_win.addstr(
                Position(0, x_pos),
                header_text,
                color=Color.HEADER,
                attributes=attributes,
            )
            x_pos += visible_width + 1
            if x_pos >= size.width:
                break

        separator_width = min(size.width - 2, x_pos - 1)
        self._header_win.addstr(
            Position(1, 1), "─" * separator_width, color=Color.HEADER
        )
        self._header_win.refresh()

    def _draw_entries_to_window(self) -> None:
        """Draw visible entries directly to the window"""
        self._data_win.clear()

        size = self._data_win.getmaxyx()

        start_entry = self._entries_model.scroll_row
        end_entry = min(start_entry + size.height, len(self._state.filtered_entries))

        for win_row, entry_idx in enumerate(range(start_entry, end_entry)):
            entry = self._state.filtered_entries[entry_idx]
            self._draw_single_entry_to_window(win_row, entry_idx, entry)

        self._data_win.refresh()

    def _draw_single_entry_to_window(
        self, win_row: int, entry_idx: int, entry: LogEntry
    ) -> None:
        """Draw a single entry to the window at the specified window row"""
        is_selected = entry_idx == self._state.current_row
        size = self._data_win.getmaxyx()

        x_pos = 1
        for col in self._iter_cols_from_current():
            value = (
                entry.get_value(col.name)[: col.width]
                .ljust(col.width)
                .replace("\n", "\\n")
            )

            color = Color.DEFAULT
            if is_selected:
                color = Color.SELECTED
            elif entry.level:
                level_color = self._get_color_for_level(entry.level.upper())
                if level_color:
                    color = level_color

            visible_width = min(size.width - x_pos - 1, col.width)
            visible_value = value[:visible_width]
            self._data_win.addstr(Position(win_row, x_pos), visible_value, color=color)

            x_pos += col.width + 1
            if x_pos >= size.width:
                break

    @staticmethod
    def _get_color_for_level(level: str) -> Color | None:
        if level in COLOR_LEVEL_MAP:
            return COLOR_LEVEL_MAP[level]
        return None

    def _update_selection_rows(self, old_row: int, new_row: int) -> None:
        """Update only the rows that changed selection status"""
        size = self._data_win.getmaxyx()
        scroll_row = self._entries_model.scroll_row

        if (
            0 <= old_row < len(self._state.filtered_entries)
            and scroll_row <= old_row < scroll_row + size.height
        ):
            win_row = old_row - scroll_row
            self._draw_single_entry_to_window(
                win_row, old_row, self._state.filtered_entries[old_row]
            )

        if (
            0 <= new_row < len(self._state.filtered_entries)
            and scroll_row <= new_row < scroll_row + size.height
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
        width = self._header_win.getmaxyx().width if self._header_win else 80
        visible_cols = self._get_visible_columns(width)
        self._entries_model.move_column(to_the_right, visible_cols)

    def adjust_column_width(self, delta: int) -> None:
        """Adjust width of current column"""
        width = self._header_win.getmaxyx().width if self._header_win else 80
        visible_cols = self._get_visible_columns(width)
        self._entries_model.adjust_column_width(delta, visible_cols)

    def get_current_column(self) -> str:
        """Get the currently selected column"""
        width = self._header_win.getmaxyx().width
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
