"""Details mode viewmodel - handles business logic and state management"""

from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry


class DetailsViewModel:
    """Handles details mode business logic and state management"""

    def __init__(
        self,
        state: JuffiState,
    ) -> None:
        self._state = state

        self._field_count: int = 0
        self._current_field: int = 0
        self._scroll_offset: int = 0

    @property
    def field_count(self) -> int:
        """Get the current field count"""
        return self._field_count

    @property
    def current_field(self) -> int:
        """Get the current field index"""
        return self._current_field

    @property
    def scroll_offset(self) -> int:
        """Get the current scroll offset"""
        return self._scroll_offset

    def navigate_field_up(self) -> None:
        """Navigate to the previous field"""
        if self._current_field > 0:
            self._current_field -= 1

    def navigate_field_down(self) -> None:
        """Navigate to the next field"""
        if self._current_field < self._field_count - 1:
            self._current_field += 1

    def navigate_entry_previous(self) -> None:
        """Navigate to the previous entry"""
        if self._state.current_row is not None and self._state.current_row > 0:
            self._state.current_row -= 1
        self._reset_view()

    def navigate_entry_next(self) -> None:
        """Navigate to the next entry"""
        if (
            self._state.current_row is not None
            and self._state.current_row < len(self._state.filtered_entries) - 1
        ):
            self._state.current_row += 1
        self._reset_view()

    def enter_mode(self) -> None:
        """Called when entering details mode"""
        self._reset_view()

        current_row = self._state.current_row
        if current_row is None:
            return

        entry = self._state.filtered_entries[current_row]
        field_count = len(self._get_entry_fields(entry))
        self._field_count = field_count

    def update_scroll_for_display(
        self, available_height: int, fields_count: int
    ) -> None:
        """Update scroll offset to ensure current field is visible"""
        # Simple scrolling: ensure selected field is visible
        if self._current_field < self._scroll_offset:
            self._scroll_offset = self._current_field
        elif self._current_field >= self._scroll_offset + available_height:
            self._scroll_offset = self._current_field - available_height + 1

        # Ensure scroll offset is not negative and not beyond the last possible position
        max_scroll = max(0, fields_count - available_height)
        self._scroll_offset = max(0, min(self._scroll_offset, max_scroll))

    def get_current_entry(self) -> LogEntry | None:
        """Get the currently selected entry"""
        if not self._state.filtered_entries:
            return None

        current_row = self._state.current_row
        if current_row is None or current_row >= len(self._state.filtered_entries):
            return None

        return self._state.filtered_entries[current_row]

    def get_entry_fields(self, entry: LogEntry) -> list[tuple[str, str]]:
        """Get all fields from the entry"""
        return self._get_entry_fields(entry)

    def _reset_view(self) -> None:
        """Reset view state"""
        self._current_field = 0
        self._scroll_offset = 0

    @staticmethod
    def _get_entry_fields(entry: LogEntry) -> list[tuple[str, str]]:
        """Get all fields from the entry (excluding missing ones)"""
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
