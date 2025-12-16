"""App viewmodel - handles business logic and state management"""

from typing import Callable

from juffi.helpers.curses_utils import get_curses_yx
from juffi.input_controller import InputController
from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry


class AppModel:
    """ViewModel class for the Juffi application"""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        state: JuffiState,
        input_controller: InputController,
        header_update: Callable[[], None],
        footer_update: Callable[[], None],
        size_update: Callable[[], None],
    ) -> None:
        self._state = state
        self._input_controller = input_controller
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
            "filtered_entries",
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
        self._state.clear_entries()
        self._input_controller.reset()
        self.load_entries()

    def update_entries(self) -> bool:
        """Update the entries"""
        old_count = len(self._state.entries)
        self.load_entries()
        if len(self._state.entries) > old_count:
            self.apply_filters()
            return True
        return False

    def load_entries(self) -> None:
        """Load entries from the input controller's data source"""
        new_entries: list[LogEntry] = []
        line_number: int = len(self._state.entries) + 1

        for line in self._input_controller.get_data():
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
            if entry.matches_filter(self._state.filters) and entry.matches_search(
                self._state.search_term
            ):
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
