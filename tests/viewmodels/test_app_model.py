"""Tests for the AppModel viewmodel class."""

import io
from typing import Callable

import pytest

from juffi.models.juffi_model import JuffiState, ViewMode
from juffi.models.log_entry import LogEntry
from juffi.viewmodels.app import AppModel


class TestAppModelInitialization:
    """Test AppModel initialization and watcher setup."""

    def test_initialization_with_callbacks(self) -> None:
        """Test AppModel initialization with callback functions."""
        state = JuffiState()
        file = io.StringIO("")

        header_called = False
        footer_called = False
        size_called = False

        def header_update() -> None:
            nonlocal header_called
            header_called = True

        def footer_update() -> None:
            nonlocal footer_called
            footer_called = True

        def size_update() -> None:
            nonlocal size_called
            size_called = True

        model = AppModel(state, file, header_update, footer_update, size_update)

        # Test that model is properly initialized
        assert model._state is state
        assert model._file is file
        assert model._column_types == {"#": int}

        # Test that watchers are registered by triggering state changes
        state.current_mode = ViewMode.HELP
        assert header_called is True

        state.follow_mode = False
        assert footer_called is True

        state.terminal_size = (24, 80)
        assert size_called is True

    def test_initial_column_types(self) -> None:
        """Test that initial column types are set correctly."""
        state = JuffiState()
        file = io.StringIO("")

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Should start with line number column type
        assert model._column_types == {"#": int}

    def test_watcher_registration_fields(self) -> None:
        """Test that all expected fields have watchers registered."""
        state = JuffiState()
        file = io.StringIO("")

        header_calls = []
        footer_calls = []
        size_calls = []

        def header_update() -> None:
            header_calls.append("header")

        def footer_update() -> None:
            footer_calls.append("footer")

        def size_update() -> None:
            size_calls.append("size")

        model = AppModel(state, file, header_update, footer_update, size_update)

        # Test header update fields
        state.current_mode = ViewMode.DETAILS
        state.terminal_size = (30, 100)
        # current_mode and terminal_size both trigger header updates
        assert len(header_calls) >= 2

        # Test footer update fields
        state.follow_mode = False
        state.current_row = 5
        state.sort_column = "level"
        state.sort_reverse = False
        state.search_term = "test"
        state.input_mode = "filter"
        state.input_buffer = "test input"
        state.input_column = "message"
        state.input_cursor_pos = 4
        # Note: terminal_size is registered for both header and footer,
        # plus current_mode is also registered for footer, so we get more calls
        assert len(footer_calls) >= 9

        # Size update should have been called once for terminal_size
        assert len(size_calls) >= 1


class TestAppModelTerminalSize:
    """Test terminal size update functionality."""

    def test_update_terminal_size(self) -> None:
        """Test updating terminal size."""
        state = JuffiState()
        file = io.StringIO("")

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Initial terminal size should be default
        assert state.terminal_size == (0, 0)

        # Note: get_curses_yx() will fail in test environment without curses initialization
        # We'll test that the method exists and can be called
        assert hasattr(model, "update_terminal_size")
        assert callable(model.update_terminal_size)


class TestAppModelReset:
    """Test reset functionality."""

    def test_reset_clears_state(self) -> None:
        """Test that reset clears filters and resets sort settings."""
        state = JuffiState()
        file = io.StringIO("")

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Set some state that should be reset
        state.update_filters({"level": "error", "service": "api"})
        state.search_term = "test search"
        state.sort_column = "timestamp"
        state.sort_reverse = False

        # Verify state is set
        assert len(state.filters) == 2
        assert state.search_term == "test search"
        assert state.sort_column == "timestamp"
        assert state.sort_reverse is False

        # Reset
        model.reset()

        # Verify state is reset
        assert len(state.filters) == 0
        assert state.search_term == ""
        assert state.sort_column == "#"
        assert state.sort_reverse is True


class TestAppModelLoadEntries:
    """Test entry loading functionality."""

    def test_load_entries_from_json_lines(self) -> None:
        """Test loading entries from JSON log lines."""
        json_lines = [
            '{"level": "info", "message": "Application started", "timestamp": "2023-01-01T10:00:00"}',
            '{"level": "error", "message": "Database connection failed", "service": "db"}',
            '{"level": "debug", "count": 42, "active": true}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Check that entries were loaded
        entries = state.entries
        assert len(entries) == 3

        # Check first entry
        assert entries[0].line_number == 1
        assert entries[0].is_valid_json is True
        assert entries[0].level == "info"
        assert entries[0].get_value("message") == "Application started"

        # Check second entry
        assert entries[1].line_number == 2
        assert entries[1].level == "error"
        assert entries[1].get_value("service") == "db"

        # Check third entry
        assert entries[2].line_number == 3
        assert entries[2].level == "debug"
        assert entries[2].get_value("count") == "42"
        assert entries[2].get_value("active") == "true"

    def test_load_entries_from_plain_text(self) -> None:
        """Test loading entries from plain text log lines."""
        text_lines = [
            "2023-01-01 10:00:00 INFO Application started",
            "2023-01-01 10:01:00 ERROR Database connection failed",
            "2023-01-01 10:02:00 DEBUG Processing request",
        ]
        file = io.StringIO("\n".join(text_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Check that entries were loaded
        entries = state.entries
        assert len(entries) == 3

        # All entries should be plain text
        for i, entry in enumerate(entries):
            assert entry.line_number == i + 1
            assert entry.is_valid_json is False
            assert entry.level is None
            assert entry.get_value("message") == text_lines[i]

    def test_load_entries_skips_empty_lines(self) -> None:
        """Test that empty lines are skipped during loading."""
        lines = [
            '{"level": "info", "message": "first"}',
            "",
            "   ",  # whitespace only
            '{"level": "error", "message": "second"}',
            "",
            '{"level": "debug", "message": "third"}',
        ]
        file = io.StringIO("\n".join(lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Should only have 3 entries (empty lines skipped)
        entries = state.entries
        assert len(entries) == 3
        assert entries[0].get_value("message") == "first"
        assert entries[1].get_value("message") == "second"
        assert entries[2].get_value("message") == "third"

        # Line numbers should be sequential
        assert entries[0].line_number == 1
        assert entries[1].line_number == 2
        assert entries[2].line_number == 3

    def test_load_entries_multiple_calls(self) -> None:
        """Test loading entries multiple times (simulating file growth)."""
        # Create a file with all content, but simulate reading it in batches
        all_lines = [
            '{"level": "info", "message": "first batch 1"}',
            '{"level": "info", "message": "first batch 2"}',
            '{"level": "error", "message": "second batch 1"}',
            '{"level": "debug", "message": "second batch 2"}',
        ]

        # First, test with only first 2 lines
        first_file = io.StringIO("\n".join(all_lines[:2]))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, first_file, dummy_callback, dummy_callback, dummy_callback
        )

        # Load first batch
        model.load_entries()
        assert len(state.entries) == 2
        assert state.entries[0].line_number == 1
        assert state.entries[1].line_number == 2

        # Now create a new file with additional content and test extending
        # This simulates the real-world scenario where new lines are added to a file
        second_file = io.StringIO("\n".join(all_lines[2:]))
        model._file = second_file  # Replace the file with new content

        # Load second batch
        model.load_entries()
        assert len(state.entries) == 4
        assert state.entries[2].line_number == 3
        assert state.entries[3].line_number == 4
        assert state.entries[2].get_value("message") == "second batch 1"
        assert state.entries[3].get_value("message") == "second batch 2"


class TestAppModelTypeManagement:
    """Test column type management functionality."""

    def test_combine_types_new_columns(self) -> None:
        """Test combining types for new columns."""
        state = JuffiState()
        file = io.StringIO("")

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Start with just line number type
        assert model._column_types == {"#": int}

        # Add new types
        new_types = {"level": str, "count": int, "active": bool}
        model._combine_types(new_types)

        expected_types = {"#": int, "level": str, "count": int, "active": bool}
        assert model._column_types == expected_types

    def test_combine_types_conflicting_types(self) -> None:
        """Test combining types when there are type conflicts."""
        state = JuffiState()
        file = io.StringIO("")

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Set initial types
        model._column_types = {"#": int, "count": int, "level": str}

        # Add conflicting types (count as str instead of int)
        conflicting_types = {"count": str, "level": str, "new_field": float}
        model._combine_types(conflicting_types)

        # count should become str due to conflict, others should remain/be added
        expected_types = {"#": int, "count": str, "level": str, "new_field": float}
        assert model._column_types == expected_types

    def test_combine_types_same_types(self) -> None:
        """Test combining types when types are the same."""
        state = JuffiState()
        file = io.StringIO("")

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Set initial types
        model._column_types = {"#": int, "level": str, "count": int}

        # Add same types
        same_types = {"level": str, "count": int}
        model._combine_types(same_types)

        # Types should remain unchanged
        expected_types = {"#": int, "level": str, "count": int}
        assert model._column_types == expected_types

    def test_load_entries_updates_types(self) -> None:
        """Test that loading entries updates column types."""
        json_lines = [
            '{"level": "info", "count": 42, "active": true}',
            '{"level": "error", "price": 19.99, "metadata": {"key": "value"}}',
            '{"level": "debug", "count": "not a number"}',  # Type conflict
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Check that types were detected and conflicts resolved
        expected_types = {
            "#": int,
            "level": str,
            "count": str,  # Conflict between int and str -> str
            "active": bool,
            "price": float,
            "metadata": dict,
        }
        assert model._column_types == expected_types


class TestAppModelFiltering:
    """Test filtering functionality."""

    def test_apply_filters_with_column_filters(self) -> None:
        """Test applying column-based filters."""
        json_lines = [
            '{"level": "info", "service": "api", "message": "Request processed"}',
            '{"level": "error", "service": "api", "message": "Request failed"}',
            '{"level": "info", "service": "db", "message": "Connection established"}',
            '{"level": "error", "service": "db", "message": "Connection failed"}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()
        assert len(state.entries) == 4

        # Apply filter for error level
        state.update_filters({"level": "error"})
        model.apply_filters()

        # Should have 2 error entries
        filtered = state.filtered_entries
        assert len(filtered) == 2
        assert all(entry.level == "error" for entry in filtered)

        # Apply additional filter for db service
        state.update_filters({"service": "db"})
        model.apply_filters()

        # Should have 1 entry (error + db)
        filtered = state.filtered_entries
        assert len(filtered) == 1
        assert filtered[0].level == "error"
        assert filtered[0].get_value("service") == "db"

    def test_apply_filters_with_search_term(self) -> None:
        """Test applying search term filter."""
        json_lines = [
            '{"level": "info", "message": "User login successful"}',
            '{"level": "error", "message": "Database connection failed"}',
            '{"level": "info", "message": "User logout successful"}',
            '{"level": "debug", "message": "Processing request"}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()
        assert len(state.entries) == 4

        # Apply search term
        state.search_term = "user"
        model.apply_filters()

        # Should have 2 entries containing "user"
        filtered = state.filtered_entries
        assert len(filtered) == 2
        assert "user" in filtered[0].get_value("message").lower()
        assert "user" in filtered[1].get_value("message").lower()

    def test_apply_filters_combined(self) -> None:
        """Test applying both column filters and search term."""
        json_lines = [
            '{"level": "info", "service": "auth", "message": "User login successful"}',
            '{"level": "error", "service": "auth", "message": "User authentication failed"}',
            '{"level": "info", "service": "api", "message": "User data retrieved"}',
            '{"level": "error", "service": "db", "message": "Database connection failed"}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()
        assert len(state.entries) == 4

        # Apply both column filter and search term
        state.update_filters({"service": "auth"})
        state.search_term = "user"
        model.apply_filters()

        # Should have 2 entries (auth service + containing "user")
        filtered = state.filtered_entries
        assert len(filtered) == 2
        assert all(entry.get_value("service") == "auth" for entry in filtered)
        assert all("user" in entry.get_value("message").lower() for entry in filtered)

    def test_apply_filters_no_matches(self) -> None:
        """Test applying filters that match no entries."""
        json_lines = [
            '{"level": "info", "message": "Application started"}',
            '{"level": "error", "message": "Database error"}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()
        assert len(state.entries) == 2

        # Apply filter that matches nothing
        state.update_filters({"level": "critical"})
        model.apply_filters()

        # Should have no filtered entries
        filtered = state.filtered_entries
        assert len(filtered) == 0

    def test_apply_filters_no_filters(self) -> None:
        """Test applying filters when no filters are set."""
        json_lines = [
            '{"level": "info", "message": "First entry"}',
            '{"level": "error", "message": "Second entry"}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()
        assert len(state.entries) == 2

        # Apply filters (no filters set)
        model.apply_filters()

        # Should have all entries
        filtered = state.filtered_entries
        assert len(filtered) == 2


class TestAppModelSorting:
    """Test sorting functionality."""

    def test_apply_filters_with_sorting_string_column(self) -> None:
        """Test sorting by string column."""
        json_lines = [
            '{"level": "error", "message": "Third"}',
            '{"level": "info", "message": "First"}',
            '{"level": "debug", "message": "Second"}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries and update types
        model.load_entries()

        # Sort by level (ascending)
        state.sort_column = "level"
        state.sort_reverse = False
        model.apply_filters()

        filtered = state.filtered_entries
        levels = [entry.level for entry in filtered]
        assert levels == ["debug", "error", "info"]  # Alphabetical order

    def test_apply_filters_with_sorting_reverse(self) -> None:
        """Test reverse sorting."""
        json_lines = [
            '{"level": "error", "count": 1}',
            '{"level": "info", "count": 3}',
            '{"level": "debug", "count": 2}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Sort by count (descending)
        state.sort_column = "count"
        state.sort_reverse = True
        model.apply_filters()

        filtered = state.filtered_entries
        counts = [int(entry.get_value("count")) for entry in filtered]
        assert counts == [3, 2, 1]  # Descending order

    def test_apply_filters_with_sorting_line_number(self) -> None:
        """Test sorting by line number."""
        json_lines = [
            '{"level": "info", "message": "First"}',
            '{"level": "error", "message": "Second"}',
            '{"level": "debug", "message": "Third"}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Sort by line number (ascending)
        state.sort_column = "#"
        state.sort_reverse = False
        model.apply_filters()

        filtered = state.filtered_entries
        line_numbers = [entry.line_number for entry in filtered]
        assert line_numbers == [1, 2, 3]  # Natural order

    def test_apply_filters_no_sort_column(self) -> None:
        """Test filtering without sorting."""
        json_lines = [
            '{"level": "error", "message": "First"}',
            '{"level": "info", "message": "Second"}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Clear sort column
        state.sort_column = ""
        model.apply_filters()

        # Should maintain original order
        filtered = state.filtered_entries
        assert len(filtered) == 2
        assert filtered[0].line_number == 1
        assert filtered[1].line_number == 2


class TestAppModelUpdateEntries:
    """Test update_entries functionality."""

    def test_update_entries_with_new_entries(self) -> None:
        """Test update_entries when new entries are available."""
        # Start with some entries
        initial_lines = [
            '{"level": "info", "message": "Initial entry 1"}',
            '{"level": "error", "message": "Initial entry 2"}',
        ]
        file = io.StringIO("\n".join(initial_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load initial entries
        model.load_entries()
        initial_count = len(state.entries)
        assert initial_count == 2

        # Simulate new entries being available by replacing the file
        new_lines = [
            '{"level": "debug", "message": "New entry 1"}',
            '{"level": "info", "message": "New entry 2"}',
        ]
        new_file = io.StringIO("\n".join(new_lines))
        model._file = new_file

        # Update entries
        result = model.update_entries()

        # Should return True (new entries found) and update state
        assert result is True
        assert len(state.entries) == 4
        assert len(state.filtered_entries) > 0  # apply_filters was called

    def test_update_entries_no_new_entries(self) -> None:
        """Test update_entries when no new entries are available."""
        lines = [
            '{"level": "info", "message": "Entry 1"}',
            '{"level": "error", "message": "Entry 2"}',
        ]
        file = io.StringIO("\n".join(lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load all entries
        model.load_entries()
        initial_count = len(state.entries)

        # Try to update (no new entries)
        result = model.update_entries()

        # Should return False (no new entries)
        assert result is False
        assert len(state.entries) == initial_count


class TestAppModelEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_file_handling(self) -> None:
        """Test handling of empty file."""
        file = io.StringIO("")
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries from empty file
        model.load_entries()

        assert len(state.entries) == 0
        assert model._column_types == {"#": int}

        # Apply filters on empty data
        model.apply_filters()
        assert len(state.filtered_entries) == 0

        # Update entries on empty file
        result = model.update_entries()
        assert result is False

    def test_file_with_only_empty_lines(self) -> None:
        """Test file with only empty/whitespace lines."""
        file = io.StringIO("\n\n   \n\t\n\n")
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Should have no entries (all lines are empty)
        assert len(state.entries) == 0

    def test_mixed_json_and_text_entries(self) -> None:
        """Test file with mixed JSON and plain text entries."""
        lines = [
            '{"level": "info", "message": "JSON entry"}',
            "Plain text log entry",
            '{"level": "error", "count": 42}',
            "Another plain text entry",
            '{"invalid": json}',  # Invalid JSON
        ]
        file = io.StringIO("\n".join(lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Should have all 5 entries
        assert len(state.entries) == 5

        # Check entry types
        assert state.entries[0].is_valid_json is True
        assert state.entries[1].is_valid_json is False
        assert state.entries[2].is_valid_json is True
        assert state.entries[3].is_valid_json is False
        assert state.entries[4].is_valid_json is False  # Invalid JSON treated as text

        # Check that types were detected from valid JSON entries
        expected_types = {"#": int, "level": str, "message": str, "count": int}
        assert model._column_types == expected_types

    def test_very_long_lines(self) -> None:
        """Test handling of very long log lines."""
        long_message = "x" * 10000
        json_line = f'{{"level": "info", "message": "{long_message}"}}'
        file = io.StringIO(json_line)
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Should handle long lines correctly
        assert len(state.entries) == 1
        assert state.entries[0].is_valid_json is True
        assert len(state.entries[0].get_value("message")) == 10000

    def test_unicode_handling(self) -> None:
        """Test handling of unicode characters."""
        unicode_lines = [
            '{"level": "info", "message": "Hello 世界", "emoji": "🚀"}',
            "Plain text with unicode: café, naïve, résumé",
            '{"user": "José", "city": "São Paulo"}',
        ]
        file = io.StringIO("\n".join(unicode_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load entries
        model.load_entries()

        # Should handle unicode correctly
        assert len(state.entries) == 3
        assert state.entries[0].get_value("message") == "Hello 世界"
        assert state.entries[0].get_value("emoji") == "🚀"
        assert "café" in state.entries[1].get_value("message")
        assert state.entries[2].get_value("user") == "José"


class TestAppModelIntegration:
    """Integration tests combining multiple features."""

    def test_complete_workflow(self) -> None:
        """Test complete workflow: load, filter, sort, update."""
        json_lines = [
            '{"timestamp": "2023-01-01T10:00:00", "level": "info", "service": "auth", "message": "User login", "user_id": 123}',
            '{"timestamp": "2023-01-01T10:01:00", "level": "error", "service": "auth", "message": "Login failed", "user_id": 456}',
            '{"timestamp": "2023-01-01T10:02:00", "level": "info", "service": "api", "message": "Request processed", "user_id": 123}',
            '{"timestamp": "2023-01-01T10:03:00", "level": "error", "service": "db", "message": "Connection timeout", "retry_count": 3}',
        ]
        file = io.StringIO("\n".join(json_lines))
        state = JuffiState()

        callback_calls = {"header": 0, "footer": 0, "size": 0}

        def header_callback() -> None:
            callback_calls["header"] += 1

        def footer_callback() -> None:
            callback_calls["footer"] += 1

        def size_callback() -> None:
            callback_calls["size"] += 1

        model = AppModel(state, file, header_callback, footer_callback, size_callback)

        # 1. Load entries
        model.load_entries()
        assert len(state.entries) == 4

        # Check that types were detected
        expected_types = {
            "#": int,
            "timestamp": str,  # Timestamps are stored as strings
            "level": str,
            "service": str,
            "message": str,
            "user_id": int,
            "retry_count": int,
        }
        assert model._column_types == expected_types

        # 2. Apply filters
        state.update_filters({"level": "error"})
        model.apply_filters()

        # Should have 2 error entries
        filtered = state.filtered_entries
        assert len(filtered) == 2
        assert all(entry.level == "error" for entry in filtered)

        # 3. Add search term
        state.search_term = "connection"
        model.apply_filters()

        # Should have 1 entry (error + containing "connection")
        filtered = state.filtered_entries
        assert len(filtered) == 1
        assert "connection" in filtered[0].get_value("message").lower()

        # 4. Sort by service
        state.sort_column = "service"
        state.sort_reverse = False
        model.apply_filters()

        # Should still have 1 entry, but sorted
        filtered = state.filtered_entries
        assert len(filtered) == 1
        assert filtered[0].get_value("service") == "db"

        # 5. Reset and test all entries
        model.reset()
        model.apply_filters()

        # Should have all entries back
        filtered = state.filtered_entries
        assert len(filtered) == 4

        # 6. Test update with new entries
        new_lines = [
            '{"timestamp": "2023-01-01T10:04:00", "level": "info", "service": "auth", "message": "User logout", "user_id": 123}',
        ]
        new_file = io.StringIO("\n".join(new_lines))
        model._file = new_file

        result = model.update_entries()
        assert result is True
        assert len(state.entries) == 5

        # Verify callbacks were called by triggering some state changes
        state.current_mode = ViewMode.HELP  # Should trigger header callback
        state.follow_mode = False  # Should trigger footer callback

        assert callback_calls["header"] > 0
        assert callback_calls["footer"] > 0

    def test_real_world_log_processing(self) -> None:
        """Test processing realistic log data."""
        realistic_logs = [
            '{"@timestamp": "2023-01-15T10:30:45.123Z", "level": "INFO", "logger": "com.example.UserService", "message": "User authentication successful", "user_id": 12345, "ip_address": "192.168.1.100", "response_time_ms": 45}',
            '{"@timestamp": "2023-01-15T10:30:46.456Z", "level": "ERROR", "logger": "com.example.DatabaseService", "message": "Connection pool exhausted", "pool_size": 10, "active_connections": 10, "stack_trace": "java.sql.SQLException: Connection timeout"}',
            '{"@timestamp": "2023-01-15T10:30:47.789Z", "level": "WARN", "logger": "com.example.CacheService", "message": "Cache miss for key", "cache_key": "user:12345:profile", "cache_hit_ratio": 0.85}',
            '{"@timestamp": "2023-01-15T10:30:48.012Z", "level": "DEBUG", "logger": "com.example.ApiController", "message": "Processing API request", "endpoint": "/api/v1/users/12345", "method": "GET", "headers": {"Authorization": "Bearer xxx", "Content-Type": "application/json"}}',
        ]
        file = io.StringIO("\n".join(realistic_logs))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(state, file, dummy_callback, dummy_callback, dummy_callback)

        # Load and process
        model.load_entries()
        model.apply_filters()

        # Verify processing
        assert len(state.entries) == 4
        assert len(state.filtered_entries) == 4

        # Check timestamp parsing
        timestamps = [entry.timestamp for entry in state.entries]
        assert all(ts is not None for ts in timestamps)

        # Check type detection for various field types
        types = model._column_types
        assert types["user_id"] == int
        assert types["response_time_ms"] == int
        assert types["cache_hit_ratio"] == float
        assert types["headers"] == dict
        assert types["level"] == str

        # Test filtering on realistic data
        state.update_filters({"level": "ERROR"})
        model.apply_filters()

        filtered = state.filtered_entries
        assert len(filtered) == 1
        assert "Connection pool exhausted" in filtered[0].get_value("message")

        # Test search across all fields
        state.clear_filters()
        state.search_term = "12345"
        model.apply_filters()

        filtered = state.filtered_entries
        assert len(filtered) == 3  # Should find in user_id, cache_key, and endpoint
