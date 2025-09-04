import collections
import dataclasses
from enum import Enum

from juffi.helpers.state import State
from juffi.models.column import Column
from juffi.models.log_entry import LogEntry
from juffi.helpers.indexed_dict import IndexedDict


class ViewMode(Enum):
    """Enumeration of different view modes in the application"""

    BROWSE = "browse"
    HELP = "help"
    DETAILS = "details"
    COLUMN_MANAGEMENT = "column_management"


@dataclasses.dataclass
class JuffiState(State):  # pylint: disable=too-many-instance-attributes
    """State of the Juffi application"""

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
    _columns: IndexedDict[Column] = dataclasses.field(default_factory=IndexedDict)
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
