#!/usr/bin/env python3
# pylint: disable=too-many-lines
"""
JSON Log Viewer TUI - A terminal user interface for viewing and analyzing JSON log files
"""
import argparse
import collections
import curses
import dataclasses
import io
import json
import math
import os
import sys
import textwrap
from datetime import datetime
from enum import Enum
from itertools import islice
from types import NoneType
from typing import (
    NewType,
    Any,
    TypeVar,
    Callable,
    Type,
    OrderedDict,
    Iterator,
)

DEL = 127

ESC = 27

Height = NewType("Height", int)
Width = NewType("Width", int)
X = NewType("X", int)
Y = NewType("Y", int)

MISSING = object()

COLORS = {
    "DEFAULT": (curses.COLOR_WHITE, -1),
    "INFO": (curses.COLOR_GREEN, -1),
    "WARNING": (curses.COLOR_YELLOW, -1),
    "ERROR": (curses.COLOR_RED, -1),
    "DEBUG": (curses.COLOR_BLUE, -1),
    "HEADER": (curses.COLOR_CYAN, -1),
    "SELECTED": (curses.COLOR_MAGENTA, -1),
}

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class IndexedDict(OrderedDict[str, V]):
    """Ordered Dictionary that can access values by index"""

    def __getitem__(self, key: int | str | slice) -> Any:
        """Get the value of the key"""
        if isinstance(key, slice):
            return islice(self.values(), key.start, key.stop, key.step)
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

    def index(self, key: str) -> int:
        """Get the index of the key"""
        for i, k in enumerate(self.keys()):
            if k == key:
                return i
        raise KeyError(key)

    def copy(self) -> "IndexedDict[V]":
        """Copy the dictionary"""
        return IndexedDict[V](super().copy())


class LogEntry:
    """Represents a single log entry"""

    def __init__(self, raw_line: str, line_number: int) -> None:
        self.raw_line: str = raw_line.strip()
        self.line_number: int = line_number
        self.data: dict[str, Any] = {}
        self.timestamp: datetime | None = None
        self.level: str | None = None
        self.is_valid_json: bool = False

        try:
            data = json.loads(self.raw_line)
            if not isinstance(data, dict):
                raise ValueError("Not a dictionary")

            self.data = data
            self.is_valid_json = True
        except ValueError:
            self.data = {"message": self.raw_line}

        for ts_field in [
            "timestamp",
            "time",
            "@timestamp",
            "datetime",
            "date",
        ]:
            if ts_field in self.data:
                ts_str = str(self.data[ts_field])
                timestamp = _try_parse_datetime(ts_str)
                if timestamp:
                    self.timestamp = timestamp
                    break

        if "level" in self.data:
            self.level = str(self.data["level"])

    @classmethod
    def from_line(
        cls, line: str, line_number: int
    ) -> tuple["LogEntry", dict[str, type]]:
        """Create a LogEntry from a line of text and return the types of its fields"""
        entry = LogEntry(line, line_number)
        return entry, entry._types

    @property
    def _types(self) -> dict[str, type]:
        types = {}
        for key, value in self.data.items():
            types[key] = type(value)
        return types

    def get_value(self, key: str) -> str:
        """Get the value of a field, formatted as a string"""
        if key == "#":
            value = self.line_number
        else:
            value = self.data.get(key, MISSING)

        if value is MISSING:
            return ""
        if value is None:
            return "null"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def get_sortable_value(self, key: str, type_: Type[T]) -> T:
        """Get the value of a field, formatted for sorting"""
        blank = {
            int: -math.inf,
            float: -math.inf,
        }
        value = self.data.get(key, MISSING)
        result: Any
        if key == "#":
            result = self.line_number

        elif key == "timestamp":
            if self.timestamp:
                result = self.timestamp
            else:
                result = ""
        elif type_ == NoneType:
            result = "null"

        elif value is MISSING:
            result = blank.get(type_, "")

        elif type_ in (int, float):
            result = value
        else:
            result = str(value)
        return result

    def matches_filter(self, filters: dict[str, str]) -> bool:
        """Check if the entry matches all the given filters"""
        for key, filter_value in filters.items():
            if not filter_value:
                continue
            entry_value = self.get_value(key).lower()
            if filter_value.lower() not in entry_value:
                return False
        return True

    def matches_search(self, search_term: str) -> bool:
        """Check if the entry matches the search term"""
        if not search_term:
            return True
        search_lower = search_term.lower()

        for value in self.data.values():
            if search_lower in str(value).lower():
                return True

        return search_lower in self.raw_line.lower()


class ViewMode(Enum):
    """Enumeration of different view modes in the application"""

    BROWSE = "browse"
    HELP = "help"
    DETAILS = "details"
    COLUMN_MANAGEMENT = "column_management"


class State:
    """A simple state dataclass that tracks changes to its attributes."""

    _CHANGES: set[str] = set()
    _WATCHERS: dict[str, list[Callable[[], None]]] = collections.defaultdict(
        list
    )

    def __setattr__(self, name: str, value: Any) -> None:
        """Override setattr to track changes to public attributes."""
        # Only track changes for public attributes (not starting with _)
        old_value = getattr(self, name, MISSING)
        super().__setattr__(name, value)
        if not name.startswith("_") and old_value != value:
            self._changed(name)

    def _changed(self, name):
        self._CHANGES.add(name)
        self._notify_watchers(name)

    @property
    def changes(self) -> set[str]:
        """Get the list of attribute names that have changed."""
        return self._CHANGES.copy()

    def clear_changes(self) -> None:
        """Clear the changes list."""
        self._CHANGES.clear()

    def register_watcher(self, name: str, callback: Callable[[], None]):
        """Register a callback to be notified when an attribute changes"""
        self._WATCHERS[name].append(callback)

    def _notify_watchers(self, name: str) -> None:
        """Notify watchers of a change"""
        for callback in self._WATCHERS[name]:
            callback()


@dataclasses.dataclass
class Column:
    """Represents a column in the table"""

    name: str
    width: int = 0


@dataclasses.dataclass
class JLessState(State):  # pylint: disable=too-many-instance-attributes
    """State of the JLess application"""

    terminal_size: tuple[int, int] = (0, 0)
    current_mode: ViewMode = ViewMode.BROWSE
    previous_mode: ViewMode = ViewMode.BROWSE
    follow_mode: bool = True
    current_row: int = 0
    current_column: str = "#"
    sort_column: str = "#"
    sort_reverse: bool = True
    input_mode: str | None = None
    input_column: str | None = None
    input_buffer: str = ""
    input_cursor_pos: int = 0
    search_term: str = ""
    _filters: dict[str, str] = dataclasses.field(default_factory=dict)
    _filters_count: int = 0
    _entries: list[LogEntry] = dataclasses.field(default_factory=list)
    _num_entries: int = 0
    _filtered_entries: list[LogEntry] = dataclasses.field(default_factory=list)
    _columns: IndexedDict[Column] = dataclasses.field(
        default_factory=IndexedDict
    )
    _all_discovered_columns: set[str] = dataclasses.field(default_factory=set)

    @property
    def filters_count(self) -> int:
        """Number of active filters"""
        return self._filters_count

    @property
    def filters(self) -> dict[str, str]:
        """Get the active filters"""
        return self._filters.copy()

    def update_filters(self, filters: dict[str, str]) -> None:
        """Set the active filters"""
        self._filters = self._filters | filters
        self._filters_count = len(self._filters) + bool(self.search_term)

    def clear_filters(self) -> None:
        """Clear the active filters"""
        self._filters.clear()
        self._filters_count = len(self._filters) + bool(self.search_term)

    @property
    def entries(self) -> list[LogEntry]:
        """Get the entries"""
        return self._entries.copy()

    @property
    def num_entries(self):
        """Number of entries"""
        return self._num_entries

    @property
    def filtered_entries(self) -> list[LogEntry]:
        """Get the filtered entries"""
        return self._filtered_entries.copy()

    def extend_entries(self, entries: list[LogEntry]) -> None:
        """Add more entries"""
        if not entries:
            return
        self._entries.extend(entries)
        self._changed("entries")
        self._num_entries += len(entries)
        self._changed("num_entries")

    def set_entries(self, entries: list[LogEntry]) -> None:
        """Set the entries"""
        self._entries = entries
        self._num_entries = len(entries)
        self._changed("num_entries")

    def set_filtered_entries(self, filtered_entries: list[LogEntry]) -> None:
        """Set the filtered entries"""
        self._filtered_entries = filtered_entries
        self._detect_columns()
        self._changed("filtered_entries")

    @property
    def columns(self) -> IndexedDict[Column]:
        """Get the columns"""
        return self._columns.copy()

    @property
    def all_discovered_columns(self) -> set[str]:
        """Get all discovered columns"""
        return self._all_discovered_columns.copy()

    def move_column(self, from_idx: int, to_idx: int) -> None:
        """Move a column"""
        values = list(self._columns.values())
        values.insert(to_idx, values.pop(from_idx))
        self._columns = IndexedDict[Column]([(col.name, col) for col in values])
        self._changed("columns")

    def set_column_width(self, column: str, width: int) -> None:
        """Set the width of a column"""
        self._columns[column].width = width
        self._changed("columns")

    def set_columns_from_names(self, column_names: list[str]) -> None:
        """Set columns from a list of column names, preserving existing column data where possible"""
        new_columns = IndexedDict[Column]()
        for col_name in column_names:
            if col_name in self._columns:
                new_columns[col_name] = self._columns[col_name]
            else:
                new_columns[col_name] = Column(col_name)

        self._columns = new_columns
        self._calculate_column_widths()
        self._changed("columns")

    def get_default_sorted_columns(self) -> list[str]:
        """Get all discovered columns sorted by default priority"""
        all_columns_list = list(self._all_discovered_columns)
        all_columns_with_counts = {
            col: 1 for col in all_columns_list
        }  # Assume count of 1 for all
        return sorted(
            all_columns_list,
            key=lambda k: self._calculate_column_priority(
                k, all_columns_with_counts[k]
            ),
            reverse=True,
        )

    def _detect_columns(self) -> None:
        """Detect columns from entries data"""
        all_keys = collections.Counter()  # type: ignore
        all_keys.update({"#"})

        for entry in self._filtered_entries:
            if entry.is_valid_json:
                all_keys.update([k for k, v in entry.data.items() if v])
            else:
                all_keys.update({"message"})

        self._all_discovered_columns.update(all_keys.keys())

        self._columns = IndexedDict[Column](
            (name, Column(name))
            for name in sorted(
                all_keys.keys(),
                key=lambda k: self._calculate_column_priority(k, all_keys[k]),
                reverse=True,
            )
        )

        self._calculate_column_widths()
        self._CHANGES.add("columns")
        self._CHANGES.add("all_discovered_columns")

    @staticmethod
    def _calculate_column_priority(column: str, count: int) -> tuple[int, int]:
        field_priority_map = {
            "#": 4,
            "timestamp": 3,
            "time": 3,
            "@timestamp": 3,
            "level": 2,
            "message": 1,
        }

        return field_priority_map.get(column, 0), count

    def _calculate_column_widths(self) -> None:
        """Calculate optimal column widths based on content"""
        width = self.terminal_size[1]
        num_cols_without_line_number = len(self._columns) - 1
        if num_cols_without_line_number <= 0:
            return

        width_without_line_number = width - 20
        max_col_width = min(
            max(50, width // num_cols_without_line_number),
            width_without_line_number,
        )

        for column in self._columns.values():
            max_width = len(column.name)

            sample_entries = self._filtered_entries[:100]
            for entry in sample_entries:
                value_len = len(entry.get_value(column.name))
                max_width = max(max_width, value_len)

            column.width = min(max_width + 1, max_col_width)


def find_first_index(
    iterable: list[T], predicate: Callable[[T], bool]
) -> int | None:
    """Find the index of the first item in the iterable that matches the predicate"""
    for i, item in enumerate(iterable):
        if predicate(item):
            return i
    return None


def get_curses_yx() -> tuple[int, int]:
    """Get the current terminal size"""
    return curses.LINES, curses.COLS  # pylint: disable=no-member


def _try_parse_datetime(ts_str: str) -> datetime | None:
    no_z_ts_str = ts_str.replace("Z", "")
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            return datetime.strptime(no_z_ts_str, fmt)
        except ValueError:
            pass

    return None


class EntriesModel:
    """ViewModel class for the entries window"""

    def __init__(
        self, state: JLessState, needs_redraw: Callable[[], None]
    ) -> None:
        self._state = state
        for field in [
            "current_mode",
            "terminal_size",
            "num_entries",
            "current_row",
            "current_column",
            "sort_column",
            "sort_reverse",
            "filters_count",
            "search_term",
            "columns",
            "filtered_entries",
        ]:
            self._state.register_watcher(field, needs_redraw)


class EntriesWindow:  # pylint: disable=too-many-instance-attributes
    """Handles the entries display window with columns, scrolling, and navigation"""

    _HEADER_HEIGHT = 2

    def __init__(
        self,
        state: JLessState,
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
            self._state.current_row = max(
                0, len(self._state.filtered_entries) - 1
            )

        self._scroll_row = min(
            self._scroll_row, len(self._state.filtered_entries)
        )
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
            current_index = self._state.columns.index(
                self._state.current_column
            )
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
            if col == self._state.sort_column:
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
        self._header_win.addstr(
            1, 1, "─" * separator_width, self._colors["HEADER"]
        )
        self._header_win.refresh()

    def _draw_entries_to_window(self) -> None:
        """Draw visible entries directly to the window"""
        self._data_win.clear()

        win_height, _ = self._data_win.getmaxyx()

        # Calculate which entries are visible
        start_entry = self._scroll_row
        end_entry = min(
            start_entry + win_height, len(self._state.filtered_entries)
        )

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
                scroll_x += next(
                    islice(self._state.columns.values(), i, None)
                ).width
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
            self._state.current_row = max(
                0, self._state.current_row - visible_rows
            )
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
            self._state.current_row = max(
                0, len(self._state.filtered_entries) - 1
            )
        elif key == curses.KEY_LEFT:
            self._state.current_column = self._state.columns[
                max(
                    0, self._state.columns.index(self._state.current_column) - 1
                )
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


class BrowseMode:  # pylint: disable=too-many-instance-attributes
    """Handles browse mode input and drawing logic"""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        state: JLessState,
        no_follow: bool,
        entries_window: EntriesWindow,
        colors: dict[str, int],
        on_apply_filters: Callable[[], None],
        on_load_entries: Callable[[], None],
        on_reset: Callable[[], None],
    ) -> None:
        self._state = state
        self.entries_window = entries_window
        self.colors = colors
        self.on_apply_filters = on_apply_filters
        self.on_load_entries = on_load_entries
        self.on_reset = on_reset

        # Browse mode specific state (not tracked in JLessState)
        self.filters: dict[str, str] = {}
        self.search_term: str = ""
        self._state.follow_mode = not no_follow

    def handle_input(self, key: int) -> None:
        """Handle input for browse mode. Returns True if key was handled."""
        if self._state.input_mode:
            self._handle_input_submode(key)

        elif key == ord("/"):
            self._state.input_mode = "search"
            self._state.input_buffer = self._state.search_term
        elif key == ord("f"):
            current_col = self.entries_window.get_current_column()
            if current_col:
                self._state.input_mode = "filter"
                self._state.input_column = current_col
                self._state.input_buffer = self._state.filters.get(
                    current_col, ""
                )
        elif key == ord("g"):
            self._state.input_mode = "goto"
            self._state.input_buffer = ""
        elif key == ord("c"):
            self._state.clear_filters()
            self.search_term = ""
            self.on_apply_filters()
        elif key == ord("s"):
            current_col = self.entries_window.get_current_column()
            if current_col:
                if self._state.sort_column == current_col:
                    self._state.sort_reverse = not self._state.sort_reverse
                else:
                    self._state.sort_column = current_col
                    self._state.sort_reverse = False
                self.on_apply_filters()
        elif key == ord("S"):
            current_col = self.entries_window.get_current_column()
            if current_col:
                self._state.sort_column = current_col
                self._state.sort_reverse = True
                self.on_apply_filters()
        elif key == ord("<"):
            self.entries_window.move_column(to_the_right=False)
        elif key == ord(">"):
            self.entries_window.move_column(to_the_right=True)
        elif key == ord("w"):
            self.entries_window.adjust_column_width(-5)
        elif key == ord("W"):
            self.entries_window.adjust_column_width(5)
        elif key == ord("F"):
            self._state.follow_mode = not self._state.follow_mode
        elif key == ord("r"):
            self.on_load_entries()
            self.on_apply_filters()
        elif key == ord("R"):
            self.on_reset()
            self.on_apply_filters()
        else:
            self.entries_window.handle_navigation(key)

    def _handle_input_submode(self, key: int) -> None:
        """Handle input for search/filter/goto submodes. Returns True if key was handled."""
        if key == ESC or key == ord("\n"):
            if key == ord("\n"):
                if self._state.input_mode == "search":
                    self._state.search_term = self._state.input_buffer
                elif (
                    self._state.input_mode == "filter"
                    and self._state.input_column
                ):
                    self._state.update_filters(
                        {self._state.input_column: self._state.input_buffer}
                    )
                elif self._state.input_mode == "goto":
                    try:
                        line_num = int(self._state.input_buffer)
                    except ValueError:
                        pass  # Invalid line number, ignore
                    else:
                        self.entries_window.goto_line(line_num)

                self.on_apply_filters()

            self._state.input_mode = None
            self._state.input_buffer = ""
            self._state.input_column = None
            self._state.input_cursor_pos = 0
        elif key in (curses.KEY_BACKSPACE, DEL):
            self._state.input_buffer = (
                self._state.input_buffer[: self._state.input_cursor_pos - 1]
                + self._state.input_buffer[self._state.input_cursor_pos :]
            )
            self._state.input_cursor_pos = max(
                0, self._state.input_cursor_pos - 1
            )
        elif key == curses.KEY_DC:
            self._state.input_buffer = (
                self._state.input_buffer[: self._state.input_cursor_pos]
                + self._state.input_buffer[self._state.input_cursor_pos + 1 :]
            )
        elif key == curses.KEY_LEFT:
            self._state.input_cursor_pos = max(
                0, self._state.input_cursor_pos - 1
            )
        elif key == curses.KEY_RIGHT:
            self._state.input_cursor_pos = min(
                len(self._state.input_buffer), self._state.input_cursor_pos + 1
            )
        else:
            # Add character to input buffer
            if 32 <= key <= 126:  # Printable ASCII characters
                self._state.input_buffer = (
                    self._state.input_buffer[: self._state.input_cursor_pos]
                    + chr(key)
                    + self._state.input_buffer[self._state.input_cursor_pos :]
                )
                self._state.input_cursor_pos += 1

    def draw(self) -> None:
        """Draw browse mode (entries view)"""
        self.entries_window.draw()


class HelpMode:
    """Handles help mode input and drawing logic"""

    def __init__(
        self,
        state: JLessState,
        colors: dict[str, int],
    ) -> None:
        self._state = state
        self._colors = colors

    def handle_input(self, _: int) -> None:
        """Handle input for help mode. Returns True if key was handled."""
        return

    def draw(self, stdscr: curses.window) -> None:
        """Draw help screen"""
        height, width = get_curses_yx()

        help_text = [
            "JSON LOG VIEWER - HELP",
            "",
            "Navigation:",
            "  ↑         - Move up",
            "  ↓         - Move down",
            "  PgUp      - Page up",
            "  PgDn      - Page down",
            "  Home      - Go to top",
            "  End       - Go to bottom",
            "  g         - Go to specific line",
            "",
            "Column Operations:",
            "  ←/→       - Scroll columns left/right",
            "  s         - Sort by current column",
            "  S         - Reverse sort by current column",
            "  </>       - Move column left/right",
            "  w/W       - Decrease/increase column width",
            "  m         - Column management screen",
            "",
            "Filtering & Search:",
            "  /         - Search all fields",
            "  f         - Filter by column",
            "  c         - Clear all filters",
            "  n/N       - Next/previous search result",
            "",
            "View Options:",
            "  d         - Toggle details view for current entry",
            "",
            "Details Mode Navigation:",
            "  ↑/↓       - Navigate between fields",
            "  ←/→       - Navigate between entries",
            "",
            "File Operations:",
            "  F         - Toggle follow mode",
            "  r         - Refresh/reload",
            "  R         - Reset view (clear filters, sort)",
            "",
            "Other:",
            "  h/?       - Toggle this help",
            "  q/Esc     - Quit",
            "",
            "Press any key to continue...",
        ]

        stdscr.clear()

        start_row = max(0, (height - len(help_text)) // 2)
        x_pos = max(0, width // 4)
        for i, line in enumerate(help_text):
            if start_row + i < height - 1:
                color = (
                    self._colors["HEADER"]
                    if i == 0
                    else self._colors["DEFAULT"]
                )
                stdscr.addstr(start_row + i, x_pos, line, color)

        stdscr.refresh()


@dataclasses.dataclass
class ColumnManagementViewModel:
    """View-model for column management logic, separate from UI concerns"""

    focus: str = "available"  # "available", "selected", "buttons"
    available_selection: int = 0
    selected_selection: int = 0
    button_selection: int = 0  # 0=OK, 1=Cancel, 2=Reset
    selected_column: str | None = None  # Currently selected column for movement
    available_columns: list[str] = dataclasses.field(default_factory=list)
    selected_columns: list[str] = dataclasses.field(default_factory=list)
    all_columns: set[str] = dataclasses.field(
        default_factory=set
    )  # Track all discovered columns

    def initialize_from_columns(self, columns: IndexedDict[Column]) -> None:
        """Initialize column management with current column state"""
        currently_selected = list(columns.keys())  # Current visible columns

        # Update all_columns with any new columns from the current visible set
        self.all_columns.update(currently_selected)

        self.selected_columns = currently_selected.copy()
        self.available_columns = [
            col for col in self.all_columns if col not in currently_selected
        ]
        self.available_columns.sort()  # Keep available columns sorted

        # Reset selections
        self.focus = "available"
        self.available_selection = 0
        self.selected_selection = 0
        self.button_selection = 0
        self.selected_column = None

    def update_all_columns(self, new_columns: set[str]) -> None:
        """Update the set of all discovered columns"""
        old_available = set(self.available_columns)
        self.all_columns.update(new_columns)

        # Update available columns with any new columns not currently selected
        self.available_columns = [
            col for col in self.all_columns if col not in self.selected_columns
        ]
        self.available_columns.sort()

        # Adjust available selection if the list changed
        if (
            set(self.available_columns) != old_available
            and self.available_columns
        ):
            self.available_selection = min(
                self.available_selection, len(self.available_columns) - 1
            )

    def reset_to_default(self, sorted_columns: list[str]) -> None:
        """Reset column management to default state with provided sorted columns"""
        self.selected_columns = sorted_columns.copy()
        self.available_columns = []

    def switch_focus(self) -> None:
        """Switch focus between panes and buttons"""
        if self.focus == "available":
            self.focus = "selected"
        elif self.focus == "selected":
            self.focus = "buttons"
        else:
            self.focus = "available"

    def move_focus_left(self) -> None:
        """Move focus to the left pane or move selected column to available"""
        if self.selected_column:
            self.move_selected_column_to_available()
        elif self.focus == "selected":
            self.focus = "available"
        elif self.focus == "buttons":
            self.focus = "selected"

    def move_focus_right(self) -> None:
        """Move focus to the right pane or move selected column to selected"""
        if self.selected_column:
            self.move_selected_column_to_selected()
        elif self.focus == "available":
            self.focus = "selected"
        elif self.focus == "selected":
            self.focus = "buttons"

    def move_selected_column_to_available(self) -> None:
        """Move the currently selected column to available list"""
        if not self.selected_column:
            return

        column = self.selected_column

        # Only move if it's currently in selected list
        if column in self.selected_columns:
            self.selected_columns.remove(column)
            self.available_columns.append(column)
            self.available_columns.sort()  # Keep available sorted

            # Update selections and focus
            self.focus = "available"
            self.available_selection = self.available_columns.index(column)

            # Adjust selected selection if needed
            if (
                self.selected_selection >= len(self.selected_columns)
                and self.selected_columns
            ):
                self.selected_selection = len(self.selected_columns) - 1

    def move_selected_column_to_selected(self) -> None:
        """Move the currently selected column to selected list"""
        if not self.selected_column:
            return

        column = self.selected_column

        # Only move if it's currently in available list
        if column in self.available_columns:
            self.available_columns.remove(column)
            self.selected_columns.append(column)

            # Update selections and focus
            self.focus = "selected"
            self.selected_selection = len(self.selected_columns) - 1

            # Adjust available selection if needed
            if (
                self.available_selection >= len(self.available_columns)
                and self.available_columns
            ):
                self.available_selection = len(self.available_columns) - 1

    def handle_enter(self) -> str | None:
        """Handle enter key based on current focus. Returns button action or None"""
        if self.focus == "available":
            self.select_column_from_available()
        elif self.focus == "selected":
            self.select_column_from_selected()
        elif self.focus == "buttons":
            return self.get_button_action()
        return None

    def select_column_from_available(self) -> None:
        """Select a column from available list for movement"""
        if not self.available_columns:
            return

        idx = self.available_selection
        if 0 <= idx < len(self.available_columns):
            column = self.available_columns[idx]
            if self.selected_column == column:
                # Deselect if already selected
                self.selected_column = None
            else:
                # Select this column
                self.selected_column = column

    def select_column_from_selected(self) -> None:
        """Select a column from selected list for movement"""
        if not self.selected_columns:
            return

        idx = self.selected_selection
        if 0 <= idx < len(self.selected_columns):
            column = self.selected_columns[idx]
            if self.selected_column == column:
                # Deselect if already selected
                self.selected_column = None
            else:
                # Select this column
                self.selected_column = column

    def get_button_action(self) -> str:
        """Get the current button action"""
        actions = ["ok", "cancel", "reset"]
        return actions[self.button_selection]

    def move_selection(self, delta: int) -> None:
        """Move selection up or down in current pane, or move selected column"""
        # If we have a selected column, move it instead of changing selection
        if self.selected_column:
            self.move_selected_column(delta)
            return

        # Otherwise, move the selection cursor
        if self.focus == "available":
            if self.available_columns:
                self.available_selection = max(
                    0,
                    min(
                        len(self.available_columns) - 1,
                        self.available_selection + delta,
                    ),
                )
        elif self.focus == "selected":
            if self.selected_columns:
                self.selected_selection = max(
                    0,
                    min(
                        len(self.selected_columns) - 1,
                        self.selected_selection + delta,
                    ),
                )
        elif self.focus == "buttons":
            self.button_selection = max(
                0, min(2, self.button_selection + delta)
            )

    def move_selected_column(self, delta: int) -> None:
        """Move the currently selected column up or down"""
        if not self.selected_column:
            return

        column = self.selected_column

        # Find which list contains the selected column
        if column in self.available_columns:
            items = self.available_columns
            current_idx = items.index(column)
            new_idx = max(0, min(len(items) - 1, current_idx + delta))

            if new_idx != current_idx:
                # Move the column
                items.insert(new_idx, items.pop(current_idx))
                self.available_selection = new_idx

        elif column in self.selected_columns:
            items = self.selected_columns
            current_idx = items.index(column)
            new_idx = max(0, min(len(items) - 1, current_idx + delta))

            if new_idx != current_idx:
                # Move the column
                items.insert(new_idx, items.pop(current_idx))
                self.selected_selection = new_idx


class ColumnManagementMode:
    """Handles the column management screen"""

    def __init__(
        self,
        state: JLessState,
        colors: dict[str, int],
    ) -> None:
        self._state = state
        self._colors = colors
        self._view_model = ColumnManagementViewModel()

        # Set up watcher to update view-model when new columns are discovered
        self._state.register_watcher(
            "all_discovered_columns", self._update_view_model_columns
        )

    def enter_mode(self) -> None:
        """Called when entering column management mode"""
        # Initialize with all discovered columns
        self._view_model.all_columns = self._state.all_discovered_columns.copy()
        self._view_model.initialize_from_columns(self._state.columns)

    def _update_view_model_columns(self) -> None:
        """Update view-model when new columns are discovered"""
        self._view_model.update_all_columns(self._state.all_discovered_columns)

    def handle_input(self, key: int) -> None:
        """Handle input for column management mode"""
        if key == 27:  # ESC - cancel
            self._state.current_mode = self._state.previous_mode
        elif key == ord("\t"):  # Tab - switch focus
            self._view_model.switch_focus()
        elif key == ord("\n"):  # Enter - action based on focus
            action = self._view_model.handle_enter()
            if action:
                self._handle_button_action(action)
        elif key == curses.KEY_UP:
            self._view_model.move_selection(-1)
        elif key == curses.KEY_DOWN:
            self._view_model.move_selection(1)
        elif key == curses.KEY_LEFT:
            self._view_model.move_focus_left()
        elif key == curses.KEY_RIGHT:
            self._view_model.move_focus_right()

    def _handle_button_action(self, action: str) -> None:
        """Handle button actions (OK, Cancel, Reset)"""
        if action == "ok":
            self._apply_column_changes()
            self._state.current_mode = self._state.previous_mode
        elif action == "cancel":
            self._state.current_mode = self._state.previous_mode
        elif action == "reset":
            sorted_columns = self._state.get_default_sorted_columns()
            self._view_model.reset_to_default(sorted_columns)

    def _apply_column_changes(self) -> None:
        """Apply column management changes to the main columns"""
        self._state.set_columns_from_names(self._view_model.selected_columns)

    def draw(self, stdscr: curses.window) -> None:
        """Draw the column management screen"""
        height, width = stdscr.getmaxyx()
        stdscr.clear()

        # Title
        title = "Column Management"
        stdscr.addstr(
            1, (width - len(title)) // 2, title, self._colors["HEADER"]
        )

        # Instructions
        instructions = "←→: Move between panes/Move column | ↑↓: Navigate/Move column | Enter: Select column | Tab: Buttons | Esc: Cancel"
        stdscr.addstr(
            2,
            (width - len(instructions)) // 2,
            instructions,
            self._colors["INFO"],
        )

        # Calculate pane dimensions
        pane_width = (width - 6) // 2
        pane_height = height - 8
        left_x = 2
        right_x = left_x + pane_width + 2
        pane_y = 4

        # Draw available columns pane
        self._draw_pane(
            stdscr,
            "Available Columns",
            self._view_model.available_columns,
            self._view_model.available_selection,
            left_x,
            pane_y,
            pane_width,
            pane_height,
            self._view_model.focus == "available",
        )

        # Draw selected columns pane
        self._draw_pane(
            stdscr,
            "Selected Columns",
            self._view_model.selected_columns,
            self._view_model.selected_selection,
            right_x,
            pane_y,
            pane_width,
            pane_height,
            self._view_model.focus == "selected",
        )

        # Draw buttons
        self._draw_buttons(stdscr, height - 3, width)

        stdscr.refresh()

    def _draw_pane(
        self,
        stdscr: curses.window,
        title: str,
        items: list[str],
        selection: int,
        x: int,
        y: int,
        width: int,
        height: int,
        is_focused: bool,
    ) -> None:
        """Draw a pane with title, border, and items"""
        # Draw border
        border_color = (
            self._colors["SELECTED"] if is_focused else self._colors["DEFAULT"]
        )

        # Top border
        stdscr.addstr(y, x, "┌" + "─" * (width - 2) + "┐", border_color)
        # Title
        title_x = x + (width - len(title)) // 2
        stdscr.addstr(y, title_x, title, self._colors["HEADER"])

        # Side borders and content
        for i in range(1, height - 1):
            stdscr.addstr(y + i, x, "│", border_color)
            stdscr.addstr(y + i, x + width - 1, "│", border_color)

            # Draw item if within range
            item_idx = i - 1
            if 0 <= item_idx < len(items):
                item = items[item_idx]

                # Determine color based on selection state
                if item == self._view_model.selected_column:
                    # Highlight selected column for movement
                    item_color = self._colors["HEADER"] | curses.A_REVERSE
                elif item_idx == selection and is_focused:
                    # Normal selection highlight
                    item_color = self._colors["SELECTED"]
                else:
                    # Default color
                    item_color = self._colors["DEFAULT"]

                item_text = item[
                    : width - 4
                ]  # Leave space for borders and padding
                stdscr.addstr(y + i, x + 2, item_text, item_color)

        # Bottom border
        stdscr.addstr(
            y + height - 1, x, "└" + "─" * (width - 2) + "┘", border_color
        )

    def _draw_buttons(self, stdscr: curses.window, y: int, width: int) -> None:
        """Draw the OK, Cancel, Reset buttons"""
        buttons = ["OK", "Cancel", "Reset"]
        button_width = 10
        total_width = len(buttons) * button_width + (len(buttons) - 1) * 2
        start_x = (width - total_width) // 2

        for i, button in enumerate(buttons):
            x = start_x + i * (button_width + 2)
            is_selected = (
                self._view_model.focus == "buttons"
                and self._view_model.button_selection == i
            )

            color = (
                self._colors["SELECTED"]
                if is_selected
                else self._colors["DEFAULT"]
            )
            button_text = f"[{button:^8}]"
            stdscr.addstr(y, x, button_text, color)


class DetailsMode:
    """Handles details mode input and drawing logic"""

    _CONTENT_START_LINE = 3

    def __init__(
        self,
        state: JLessState,
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
        self._entries_win.addstr(
            0, 1, title[: width - 2], self._colors["HEADER"]
        )
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
            f"Field {self._current_field + 1}/{len(fields)}"
            if fields
            else "No fields"
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

    def _draw_fields(
        self, field_indexes: list[int], fields: list[tuple[str, str]]
    ):

        height, width = self._entries_win.getmaxyx()
        content_end_line = height - 3
        y_pos = self._CONTENT_START_LINE
        max_key_width = min(
            20, max(len(key) for key, _ in fields) if fields else 0
        )

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
                self._write_selected_lines(
                    lines, value_color, y_pos, value_start_x
                )
                y_pos += len(lines)
            else:
                value_str = value.replace("\n", "\\n").replace("\r", "\\r")
                if value_str:
                    [value_str] = textwrap.wrap(
                        value_str, available_width, max_lines=1
                    )

                self._entries_win.addstr(
                    y_pos, value_start_x, value_str, value_color
                )
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


class JLessModel:
    """ViewModel class for the JLess application"""

    def __init__(
        self,
        state: JLessState,
        file: io.TextIOWrapper,
        header_update: Callable[[], None],
        footer_update: Callable[[], None],
        size_update: Callable[[], None],
    ) -> None:
        self._state = state
        self._file = file
        self._column_types: dict[str, type] = {"#": int}
        for field in ["current_mode", "terminal_size"]:
            self._state.register_watcher(field, header_update)
        for field in [
            "terminal_size",
            "current_mode",
            "follow_mode",
            "current_row",
            "sort_column",
            "sort_reverse",
            "filters_count",
            "search_term",
            "input_mode",
            "input_buffer",
            "input_column",
            "input_cursor_pos",
        ]:
            self._state.register_watcher(field, footer_update)
        self._state.register_watcher("terminal_size", size_update)

    def update_terminal_size(self) -> None:
        """Update the terminal size"""
        self._state.terminal_size = get_curses_yx()

    def reset(self) -> None:
        """Reset the model to its initial state"""
        self._state.clear_filters()
        self._state.search_term = ""
        self._state.sort_column = "#"
        self._state.sort_reverse = True

    def update_entries(self) -> bool:
        """Update the entries"""
        old_count = len(self._state.entries)
        self.load_entries()
        if len(self._state.entries) > old_count:
            self.apply_filters()
            return True
        return False

    def load_entries(self) -> None:
        """Temp"""
        new_entries: list[LogEntry] = []
        line_number: int = len(self._state.entries) + 1

        for line in self._file:
            if line.strip():
                entry, types = LogEntry.from_line(line, line_number)
                new_entries.append(entry)
                line_number += 1

                self._combine_types(types)

        self._state.extend_entries(new_entries)

    def _combine_types(self, new_types: dict[str, type]) -> None:
        for key, value_type in new_types.items():
            if key not in self._column_types:
                self._column_types[key] = value_type
            elif self._column_types[key] != value_type:
                self._column_types[key] = str

    def apply_filters(self) -> None:
        """Temp"""
        filtered_entries = []

        for entry in self._state.entries:
            if entry.matches_filter(
                self._state.filters
            ) and entry.matches_search(self._state.search_term):
                filtered_entries.append(entry)

        if self._state.sort_column:
            filtered_entries.sort(
                key=lambda e: e.get_sortable_value(
                    self._state.sort_column,
                    self._column_types[self._state.sort_column],
                ),
                reverse=self._state.sort_reverse,
            )

        self._state.set_filtered_entries(filtered_entries)


class JLess:  # pylint: disable=too-many-instance-attributes
    """Main application class"""

    HEADER_HEIGHT = 2
    FOOTER_HEIGHT = 2

    def __init__(
        self,
        stdscr: curses.window,
        file_name: str,
        file: io.TextIOWrapper,
        no_follow: bool,
    ) -> None:
        self._stdscr = stdscr
        self._log_file: str = file_name
        self._needs_header_redraw = True
        self._needs_footer_redraw = True
        self._needs_resize = True
        self._state = JLessState()
        self._model = JLessModel(
            self._state,
            file,
            header_update=self._update_needs_header_redraw,
            footer_update=self._update_needs_footer_redraw,
            size_update=self._update_needs_resize,
        )

        curses.start_color()
        curses.use_default_colors()

        self._colors: dict[str, int] = {}
        for i, (name, (fg, bg)) in enumerate(COLORS.items(), start=1):
            curses.init_pair(i, fg, bg)
            self._colors[name] = curses.color_pair(i)

        width = get_curses_yx()[1]

        self._header_win: curses.window = stdscr.derwin(  # type: ignore
            self.HEADER_HEIGHT, width, 0, 0
        )

        self._footer_win: curses.window = stdscr.derwin(  # type: ignore
            self.FOOTER_HEIGHT, width, self._footer_start, 0
        )

        self._entries_win: curses.window = stdscr.derwin(  # type: ignore
            self._entries_height, width, self.HEADER_HEIGHT, 0
        )

        self._entries_window = EntriesWindow(
            self._state, self._colors, self._entries_win
        )

        self._browse_mode = BrowseMode(
            self._state,
            no_follow=no_follow,
            entries_window=self._entries_window,
            colors=self._colors,
            on_apply_filters=self._apply_filters,
            on_load_entries=self._load_entries,
            on_reset=self._reset,
        )
        self._help_mode = HelpMode(
            self._state,
            colors=self._colors,
        )
        self._column_management_mode = ColumnManagementMode(
            self._state,
            colors=self._colors,
        )
        self._details_mode = DetailsMode(
            self._state,
            entries_window=self._entries_window,
            colors=self._colors,
            entries_win=self._entries_win,
        )

    def _update_needs_header_redraw(self) -> None:
        self._needs_header_redraw = True

    def _update_needs_footer_redraw(self) -> None:
        self._needs_footer_redraw = True

    def _update_needs_resize(self) -> None:
        self._needs_resize = True

    def _apply_filters(self) -> None:
        self._model.apply_filters()
        self._entries_window.set_data()

    def _load_entries(self) -> None:
        self._model.load_entries()
        self._apply_filters()
        self._entries_window.set_data()

    def _reset(self) -> None:
        self._model.reset()
        self._entries_window.reset()

    def _resize_windows(self) -> None:
        """Resize all windows to fit the new terminal size"""

        width = get_curses_yx()[1]
        self._header_win.resize(self.HEADER_HEIGHT, width)
        self._header_win.mvderwin(0, 0)

        self._footer_win.resize(self.FOOTER_HEIGHT, width)
        self._footer_win.mvderwin(self._footer_start, 0)

        self._entries_win.resize(self._entries_height, width)
        self._entries_win.mvderwin(self.HEADER_HEIGHT, 0)
        self._entries_window.resize()

    @property
    def _footer_start(self):
        return get_curses_yx()[0] - self.FOOTER_HEIGHT

    @property
    def _entries_height(self):
        return self._footer_start - self.HEADER_HEIGHT

    def _draw_header(self) -> None:
        _, width = self._header_win.getmaxyx()
        self._header_win.clear()

        title = f"JLess - JSON Log Viewer - {os.path.basename(self._log_file)}"
        self._header_win.addstr(
            0, 1, title[: width - 2], self._colors["HEADER"]
        )

        self._header_win.addstr(1, 1, "─" * (width - 2), self._colors["HEADER"])

        self._header_win.refresh()

    def _draw_footer(self) -> None:
        _, width = self._footer_win.getmaxyx()
        self._footer_win.clear()

        status = self._get_status_line()

        self._footer_win.addstr(0, 1, status[: width - 2], self._colors["INFO"])

        if self._state.input_mode:
            visible_prompt, input_text = self._get_prompt_and_input_text(width)
            self._footer_win.addstr(
                1, 1, visible_prompt, self._colors["DEFAULT"]
            )
            self._footer_win.addstr(
                1, 1 + len(visible_prompt), input_text, self._colors["DEFAULT"]
            )
            self._footer_win.move(
                1, 1 + len(visible_prompt) + self._state.input_cursor_pos
            )
            curses.curs_set(1)
        else:
            curses.curs_set(0)

        self._footer_win.refresh()

    def _get_prompt_and_input_text(self, width):
        prompt = ""
        if self._state.input_mode == "search":
            prompt = "Search: "
        elif self._state.input_mode == "filter" and self._state.current_column:
            prompt = f"Filter {self._state.current_column}: "
        elif self._state.input_mode == "goto":
            prompt = "Go to line: "

        visible_prompt = prompt[: width - 2]
        input_text = self._state.input_buffer[: width - 2 - len(visible_prompt)]

        return visible_prompt, input_text

    def _get_status_line(self):
        status_parts = []
        if self._state.current_mode == ViewMode.DETAILS:
            status_parts.append("DETAILS")
        if self._state.follow_mode:
            status_parts.append("FOLLOW")
        if self._state.filtered_entries:
            status_parts.append(
                f"Row {self._state.current_row + 1}/{len(self._state.filtered_entries)}"
            )
        else:
            status_parts.append("No entries")

        if self._state.sort_column:
            direction = "DESC" if self._state.sort_reverse else "ASC"
            status_parts.append(f"Sort: {self._state.sort_column} {direction}")

        if self._state.filters_count > 0:
            status_parts.append(f"Filters: {self._state.filters_count}")

        status_parts.append("Press 'h' for help")
        status = " | ".join(status_parts)
        return status

    def run(self) -> None:
        """Main TUI loop"""
        self._state.terminal_size = get_curses_yx()
        curses.curs_set(0)
        self._stdscr.timeout(1000)

        self._stdscr.keypad(True)

        while True:
            key = self._stdscr.getch()

            if key == -1 and self._model.update_entries():
                self._entries_window.set_data()

            elif key == curses.KEY_RESIZE:
                curses.update_lines_cols()
                self._model.update_terminal_size()

            elif key == ord("q") or key == 27:
                return
            elif key in {ord("d"), ord("h"), ord("?"), ord("m")}:
                self._switch_mode(key)
            elif self._state.current_mode == ViewMode.HELP:
                self._help_mode.handle_input(key)
            elif self._state.current_mode == ViewMode.COLUMN_MANAGEMENT:
                self._column_management_mode.handle_input(key)
            elif self._state.current_mode == ViewMode.BROWSE:
                self._browse_mode.handle_input(key)
            else:
                self._details_mode.handle_input(key)

            if "follow_mode" in self._state.changes:
                self._stdscr.timeout(1000 if self._state.follow_mode else -1)

            if self._needs_resize:
                self._resize_windows()
                self._needs_resize = False

            if self._needs_header_redraw:
                self._draw_header()
                self._needs_header_redraw = False

            if self._state.current_mode == ViewMode.HELP:
                self._help_mode.draw(self._stdscr)
            elif self._state.current_mode == ViewMode.COLUMN_MANAGEMENT:
                self._column_management_mode.draw(self._stdscr)
            elif self._state.current_mode == ViewMode.BROWSE:
                self._browse_mode.draw()
            else:
                self._details_mode.draw(self._state.filtered_entries)

            if self._needs_footer_redraw:
                self._draw_footer()
                self._needs_footer_redraw = False

            self._state.clear_changes()

    def _switch_mode(self, key: int) -> None:
        previous_mode = self._state.current_mode

        if key == ord("d"):
            self._state.current_mode = (
                ViewMode.DETAILS
                if self._state.current_mode == ViewMode.BROWSE
                else ViewMode.BROWSE
            )
        elif key == ord("m"):
            self._state.current_mode = (
                ViewMode.COLUMN_MANAGEMENT
                if self._state.current_mode == ViewMode.BROWSE
                else ViewMode.BROWSE
            )
        elif key in {ord("h"), ord("?")}:
            self._state.current_mode = (
                ViewMode.HELP
                if self._state.current_mode != ViewMode.HELP
                else self._state.previous_mode
            )

        self._state.previous_mode = previous_mode
        if self._state.current_mode == ViewMode.DETAILS:
            self._details_mode.enter_mode()
        elif self._state.current_mode == ViewMode.COLUMN_MANAGEMENT:
            self._column_management_mode.enter_mode()


def main(stdscr: curses.window) -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="JSON Log Viewer TUI - View and analyze JSON log files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s app.log
  %(prog)s -f app.log
  %(prog)s --follow app.log

Key Features:
  - Automatic column detection from JSON fields
  - Sortable columns (press 's' on any column)
  - Column reordering (use '<' and '>' keys)
  - Horizontal scrolling for wide tables
  - Filtering by any column (press 'f')
  - Search across all fields (press '/')
  - Real-time log following (press 'F' to toggle)

Navigation:
  ↑/↓ or k/j    - Move up/down
  ←/→           - Scroll columns left/right
  PgUp/PgDn     - Page up/down
  Home/End      - Go to top/bottom
  h or ?        - Show help
  q or Esc      - Quit
        """,
    )

    parser.add_argument("log_file", help="Path to the JSON log file to view")

    parser.add_argument(
        "-n",
        "--no-follow",
        action="store_true",
        help="Follow the log file for new entries (like tail -f)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.log_file):
        print(f"Error: Log file '{args.log_file}' not found", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(args.log_file):
        print(f"Error: '{args.log_file}' is not a file", file=sys.stderr)
        sys.exit(1)
    with open(args.log_file, "r", encoding="utf-8", errors="ignore") as file:
        viewer = JLess(stdscr, args.log_file, file, args.no_follow)
        viewer.run()


if __name__ == "__main__":
    curses.wrapper(main)  # type: ignore
