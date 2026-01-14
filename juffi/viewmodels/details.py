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
        self._intended_field_position: int = 0
        self._in_fullscreen_mode: bool = False
        self._field_content_scroll_offset: int = 0

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

    @property
    def field_content_scroll_offset(self) -> int:
        """Get the current field content scroll offset"""
        return self._field_content_scroll_offset

    @property
    def in_fullscreen_mode(self) -> bool:
        """Check if currently in fullscreen field view mode"""
        return self._in_fullscreen_mode

    def navigate_field_up(self) -> None:
        """Navigate to the previous field"""
        if self._current_field > 0:
            self._current_field -= 1
            self._intended_field_position = self._current_field

    def navigate_field_down(self) -> None:
        """Navigate to the next field"""
        if self._current_field < self._field_count - 1:
            self._current_field += 1
            self._intended_field_position = self._current_field

    def navigate_entry_previous(self) -> None:
        """Navigate to the previous entry"""
        if self._state.current_row is not None and self._state.current_row > 0:
            self._state.current_row -= 1
            self._update_field_count_and_position()

    def navigate_entry_next(self) -> None:
        """Navigate to the next entry"""
        if (
            self._state.current_row is not None
            and self._state.current_row < len(self._state.filtered_entries) - 1
        ):
            self._state.current_row += 1
            self._update_field_count_and_position()

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
        self._field_content_scroll_offset = 0
        self._in_fullscreen_mode = False

    def _update_field_count_and_position(self) -> None:
        """Update field count and restore intended field position"""
        entry = self.get_current_entry()
        if not entry:
            self._reset_view()
            return

        fields = self._get_entry_fields(entry)
        self._field_count = len(fields)
        self._current_field = min(self._intended_field_position, self._field_count - 1)
        self._scroll_offset = 0

    def scroll_field_content_up(self, scroll_lines: int) -> None:
        """Scroll up within the current field's content (fullscreen mode only)"""
        self._field_content_scroll_offset = max(
            0, self._field_content_scroll_offset - scroll_lines
        )

    def scroll_field_content_down(self, scroll_lines: int, max_lines: int) -> None:
        """Scroll down within the current field's content (fullscreen mode only)"""
        max_scroll = max(0, max_lines - scroll_lines)
        self._field_content_scroll_offset = min(
            max_scroll, self._field_content_scroll_offset + scroll_lines
        )

    def toggle_fullscreen_mode(self) -> None:
        """Toggle fullscreen mode for the current field"""
        self._in_fullscreen_mode = not self._in_fullscreen_mode
        if not self._in_fullscreen_mode:
            self._field_content_scroll_offset = 0

    def exit_fullscreen_mode(self) -> None:
        """Exit fullscreen mode"""
        self._in_fullscreen_mode = False
        self._field_content_scroll_offset = 0

    @staticmethod
    def _get_entry_fields(entry: LogEntry) -> list[tuple[str, str]]:
        """Get all fields from the entry (excluding missing ones)"""
        fields = []
        if entry.is_valid_json:
            for key in sorted(entry.data.keys()):
                value = entry.get_value(key)
                fields.append((key, value))
        else:
            fields.append(("message", entry.raw_line))
        return fields
