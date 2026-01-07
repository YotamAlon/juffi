"""Main state of the Juffi application"""

import collections
from enum import Enum

from juffi.helpers.curses_utils import Size
from juffi.helpers.indexed_dict import IndexedDict
from juffi.helpers.state import Field, State
from juffi.models.column import Column
from juffi.models.log_entry import LogEntry


class ViewMode(Enum):
    """Enumeration of different view modes in the application"""

    BROWSE = "browse"
    HELP = "help"
    DETAILS = "details"
    COLUMN_MANAGEMENT = "column_management"


class JuffiState(
    State
):  # pylint: disable=too-many-instance-attributes,protected-access
    """State of the Juffi application"""

    filters = Field[dict[str, str]](dict)
    entries = Field[list[LogEntry]](list)
    filtered_entries = Field[list[LogEntry]](list)
    columns = Field[IndexedDict[Column]](IndexedDict)
    all_discovered_columns = Field[set[str]](set)
    terminal_size = Field[Size](Size(0, 0))
    current_mode = Field[ViewMode](ViewMode.BROWSE)
    previous_mode = Field[ViewMode](ViewMode.BROWSE)
    follow_mode = Field[bool](True)
    current_row = Field[int | None](None)
    current_column = Field[str]("#")
    sort_column = Field[str]("#")
    sort_reverse = Field[bool](True)
    input_mode = Field[str | None](None)
    input_column = Field[str | None](None)
    input_buffer = Field[str]("")
    input_cursor_pos = Field[int](0)
    search_term = Field[str]("")

    @property
    def filters_count(self) -> int:
        """Number of active filters"""
        return len(self.filters) + bool(self.search_term)

    def update_filters(self, filters: dict[str, str]) -> None:
        """Set the active filters"""
        self.filters.update(filters)

    def clear_filters(self) -> None:
        """Clear the active filters"""
        self.filters.clear()

    def clear_entries(self) -> None:
        """Clear all entries"""
        self.entries.clear()

    @property
    def num_entries(self) -> int:
        """Number of entries"""
        return len(self.entries)

    def extend_entries(self, entries: list[LogEntry]) -> None:
        """Add more entries"""
        if not entries:
            return
        self.entries.extend(entries)

    def set_entries(self, entries: list[LogEntry]) -> None:
        """Set the entries"""
        self.entries = entries

    def set_filtered_entries(self, filtered_entries: list[LogEntry]) -> None:
        """Set the filtered entries"""
        self.filtered_entries = filtered_entries
        self._detect_columns()

    def move_column(self, from_idx: int, to_idx: int) -> None:
        """Move a column"""
        values = list(self.columns.values())
        values.insert(to_idx, values.pop(from_idx))
        self.columns = IndexedDict[Column]([(col.name, col) for col in values])

    def set_column_width(self, column: str, width: int) -> None:
        """Set the width of a column"""
        self.columns[column].width = width
        self._changed("columns")

    def set_columns_from_names(self, column_names: list[str]) -> None:
        """
        Set columns from a list of column names,
        preserving existing column data where possible
        """
        new_columns = IndexedDict[Column]()
        for col_name in column_names:
            if col_name in self.columns:
                new_columns[col_name] = self.columns[col_name]
            else:
                new_columns[col_name] = Column(col_name)

        self.columns = new_columns
        self._calculate_column_widths()

    def get_default_sorted_columns(self) -> list[str]:
        """Get all discovered columns sorted by default priority"""
        all_columns_list = list(self.all_discovered_columns)
        all_columns_with_counts = {col: 1 for col in all_columns_list}
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

        for entry in self.filtered_entries:
            if entry.is_valid_json:
                all_keys.update([k for k, v in entry.data.items() if v])
            else:
                all_keys.update({"message"})

        self.all_discovered_columns.update(all_keys.keys())

        self.columns = IndexedDict[Column](
            (name, Column(name))
            for name in sorted(
                all_keys.keys(),
                key=lambda k: self._calculate_column_priority(k, all_keys[k]),
                reverse=True,
            )
        )

        self._calculate_column_widths()

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
        num_cols_without_line_number = len(self.columns) - 1
        if num_cols_without_line_number <= 0:
            return

        line_number_column_width = len(str(len(self.entries))) + 2

        width_without_line_number = width - line_number_column_width
        max_col_width = min(
            max(50, width // num_cols_without_line_number),
            width_without_line_number,
        )

        for column in self.columns.values():
            max_width = len(column.name)

            for entry in self.filtered_entries:
                value_len = len(entry.get_value(column.name))
                max_width = max(max_width, value_len)

            content_width = max(max_width, len(column.name) + 2)
            column.width = min(content_width + 1, max_col_width)
