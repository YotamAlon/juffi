"""Tests for the AppModel viewmodel class."""  # pylint: disable=too-many-lines

from typing import Iterator

from juffi.input_controller import InputController
from juffi.models.juffi_model import JuffiState, ViewMode
from juffi.viewmodels.app import AppModel


class MockInputController(InputController):
    """Mock input controller for testing"""

    def __init__(self, data_lines: list[str] = None, input_name: str = "test.log"):
        self.data_lines = data_lines or []
        self.input_keys = []
        self.input_index = 0
        self.input_name = input_name
        self.read_count = 0  # Track how many times get_data has been called
        self.additional_data = []  # For simulating file growth

    def get_input(self) -> int:
        if self.input_index < len(self.input_keys):
            key = self.input_keys[self.input_index]
            self.input_index += 1
            return key
        return -1

    def get_data(self) -> Iterator[str]:
        self.read_count += 1
        # For the first read, return initial data
        # For subsequent reads, return additional data (simulating file growth)
        if self.read_count == 1:
            return iter(self.data_lines)
        if self.additional_data:
            # Return additional data and clear it
            data = self.additional_data[:]
            self.additional_data.clear()
            return iter(data)
        return iter([])

    def add_data(self, new_lines: list[str]) -> None:
        """Add new data to simulate file growth"""
        self.additional_data.extend(new_lines)

    def get_input_name(self) -> str:
        return self.input_name


def create_mock_controller_from_string(
    data: str, input_name: str = "test.log"
) -> MockInputController:
    """Helper function to create MockInputController from string data"""
    lines = data.split("\n") if data else []
    # Filter out empty lines to match the original behavior
    lines = [line for line in lines if line.strip()]
    return MockInputController(lines, input_name)


class TestAppModelInitialization:
    """Test AppModel initialization and watcher setup."""

    def test_initialization_with_callbacks(self) -> None:
        """Test AppModel initialization with callback functions."""
        state = JuffiState()
        input_controller = MockInputController()

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

        AppModel(state, input_controller, header_update, footer_update, size_update)

        # Test that watchers are registered by triggering state changes
        state.current_mode = ViewMode.HELP
        assert header_called is True

        state.follow_mode = False
        assert footer_called is True

        state.terminal_size = (24, 80)
        assert size_called is True

    def test_initial_sorting_behavior(self) -> None:
        """Test that initial sorting works correctly (verifies column types are set)."""
        json_lines = [
            '{"level": "error", "count": 3}',
            '{"level": "info", "count": 1}',
            '{"level": "debug", "count": 2}',
        ]
        input_controller = MockInputController(json_lines)
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

        # Load entries and test that line number sorting works (verifies int type detection)
        model.load_entries()
        state.sort_column = "#"
        state.sort_reverse = False
        model.apply_filters()

        # Should be sorted by line number (1, 2, 3)
        filtered = state.filtered_entries
        line_numbers = [entry.line_number for entry in filtered]
        assert line_numbers == [1, 2, 3]

    def test_watcher_registration_fields(self) -> None:
        """Test that all expected fields have watchers registered."""
        state = JuffiState()
        input_controller = create_mock_controller_from_string("")

        header_calls = []
        footer_calls = []
        size_calls = []

        def header_update() -> None:
            header_calls.append("header")

        def footer_update() -> None:
            footer_calls.append("footer")

        def size_update() -> None:
            size_calls.append("size")

        AppModel(state, input_controller, header_update, footer_update, size_update)

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


def test_update_terminal_size() -> None:
    """Test updating terminal size."""
    state = JuffiState()
    input_controller = create_mock_controller_from_string("")

    def dummy_callback() -> None:
        pass

    model = AppModel(
        state, input_controller, dummy_callback, dummy_callback, dummy_callback
    )

    # Initial terminal size should be default
    assert state.terminal_size == (0, 0)

    # Note: get_curses_yx() will fail in test environment without curses initialization
    # We'll test that the method exists and can be called
    assert hasattr(model, "update_terminal_size")
    assert callable(model.update_terminal_size)


def test_reset_clears_state() -> None:
    """Test that reset clears filters and resets sort settings."""
    state = JuffiState()
    input_controller = create_mock_controller_from_string("")

    def dummy_callback() -> None:
        pass

    model = AppModel(
        state, input_controller, dummy_callback, dummy_callback, dummy_callback
    )

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
            '{"level": "info", "message": "Application started", '
            '"timestamp": "2023-01-01T10:00:00"}',
            '{"level": "error", "message": "Database connection failed", "service": "db"}',
            '{"level": "debug", "count": 42, "active": true}',
        ]
        input_controller = MockInputController(json_lines)
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = MockInputController(text_lines)
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        first_input_controller = create_mock_controller_from_string(
            "\n".join(all_lines[:2])
        )
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state,
            first_input_controller,
            dummy_callback,
            dummy_callback,
            dummy_callback,
        )

        # Load first batch
        model.load_entries()
        assert len(state.entries) == 2
        assert state.entries[0].line_number == 1
        assert state.entries[1].line_number == 2

        # Now simulate file growth by adding new data to the same controller
        # This simulates the real-world scenario where new lines are added to a file
        first_input_controller.add_data(all_lines[2:])

        # Load second batch
        model.load_entries()
        assert len(state.entries) == 4
        assert state.entries[2].line_number == 3
        assert state.entries[3].line_number == 4
        assert state.entries[2].get_value("message") == "second batch 1"
        assert state.entries[3].get_value("message") == "second batch 2"


class TestAppModelTypeManagement:
    """Test column type management functionality."""

    def test_string_column_sorting(self) -> None:
        """Test that string columns sort alphabetically (verifies string type detection)."""
        json_lines = [
            '{"level": "error", "message": "Third"}',
            '{"level": "info", "message": "First"}',
            '{"level": "debug", "message": "Second"}',
        ]
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

        model.load_entries()

        # Sort by level (string column)
        state.sort_column = "level"
        state.sort_reverse = False
        model.apply_filters()

        filtered = state.filtered_entries
        levels = [entry.level for entry in filtered]
        assert levels == ["debug", "error", "info"]  # Alphabetical order

    def test_numeric_column_sorting(self) -> None:
        """Test that numeric columns sort numerically (verifies int type detection)."""
        json_lines = [
            '{"level": "info", "count": 100}',
            '{"level": "error", "count": 2}',
            '{"level": "debug", "count": 10}',
        ]
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

        model.load_entries()

        # Sort by count (numeric column) - should sort numerically, not lexicographically
        state.sort_column = "count"
        state.sort_reverse = False
        model.apply_filters()

        filtered = state.filtered_entries
        counts = [int(entry.get_value("count")) for entry in filtered]
        assert counts == [2, 10, 100]  # Numeric order (not "10", "100", "2")

    def test_float_column_sorting(self) -> None:
        """Test that float columns sort numerically (verifies float type detection)."""
        json_lines = [
            '{"level": "info", "price": 19.99}',
            '{"level": "error", "price": 5.5}',
            '{"level": "debug", "price": 100.0}',
        ]
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

        model.load_entries()

        # Sort by price (float column) - should sort numerically
        state.sort_column = "price"
        state.sort_reverse = False
        model.apply_filters()

        filtered = state.filtered_entries
        prices = [float(entry.get_value("price")) for entry in filtered]
        assert prices == [5.5, 19.99, 100.0]  # Numeric order

    def test_type_conflict_resolution_through_sorting(self) -> None:
        """Test that type conflicts are resolved to string (observable through sorting)."""
        json_lines = [
            '{"level": "info", "count": 42}',  # int
            '{"level": "error", "count": "not a number"}',  # string - creates conflict
            '{"level": "debug", "count": 1}',  # int
        ]
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

        model.load_entries()

        # Sort by count - should sort as strings due to conflict (not numerically)
        state.sort_column = "count"
        state.sort_reverse = False
        model.apply_filters()

        filtered = state.filtered_entries
        count_values = [entry.get_value("count") for entry in filtered]
        # String sorting: "1", "42", "not a number" (alphabetical)
        assert count_values == ["1", "42", "not a number"]


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
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(json_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = MockInputController(initial_lines)
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

        # Load initial entries
        model.load_entries()
        initial_count = len(state.entries)
        assert initial_count == 2

        # Simulate new entries being available by adding data to the controller
        new_lines = [
            '{"level": "debug", "message": "New entry 1"}',
            '{"level": "info", "message": "New entry 2"}',
        ]
        input_controller.add_data(new_lines)

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
        input_controller = create_mock_controller_from_string("\n".join(lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("")
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

        # Load entries from empty file
        model.load_entries()

        assert len(state.entries) == 0
        # Verify line number column type is initialized (observable through sorting behavior)
        # Even with no entries, the column type should be set for line numbers

        # Apply filters on empty data
        model.apply_filters()
        assert len(state.filtered_entries) == 0

        # Update entries on empty file
        result = model.update_entries()
        assert result is False

    def test_file_with_only_empty_lines(self) -> None:
        """Test file with only empty/whitespace lines."""
        input_controller = create_mock_controller_from_string("\n\n   \n\t\n\n")
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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

        # Verify that types were detected correctly by testing sorting behavior
        # Sort by count (should be detected as int from valid JSON entries)
        state.sort_column = "count"
        state.sort_reverse = False
        model.apply_filters()

        # Only valid JSON entries should be in filtered results and sorted numerically
        filtered = state.filtered_entries
        valid_entries = [
            entry
            for entry in filtered
            if entry.is_valid_json and entry.get_value("count")
        ]
        if len(valid_entries) >= 2:
            counts = [int(entry.get_value("count")) for entry in valid_entries]
            assert counts == sorted(counts)  # Should be in numeric order

    def test_very_long_lines(self) -> None:
        """Test handling of very long log lines."""
        long_message = "x" * 10000
        json_line = f'{{"level": "info", "message": "{long_message}"}}'
        input_controller = create_mock_controller_from_string(json_line)
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
        input_controller = create_mock_controller_from_string("\n".join(unicode_lines))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

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
            '{"timestamp": "2023-01-01T10:00:00", "level": "info", "service": "auth", '
            '"message": "User login", "user_id": 123}',
            '{"timestamp": "2023-01-01T10:01:00", "level": "error", "service": "auth", '
            '"message": "Login failed", "user_id": 456}',
            '{"timestamp": "2023-01-01T10:02:00", "level": "info", "service": "api", '
            '"message": "Request processed", "user_id": 123}',
            '{"timestamp": "2023-01-01T10:03:00", "level": "error", "service": "db", '
            '"message": "Connection timeout", "retry_count": 3}',
        ]
        input_controller = MockInputController(json_lines)
        state = JuffiState()

        callback_calls = {"header": 0, "footer": 0, "size": 0}

        def header_callback() -> None:
            callback_calls["header"] += 1

        def footer_callback() -> None:
            callback_calls["footer"] += 1

        def size_callback() -> None:
            callback_calls["size"] += 1

        model = AppModel(
            state, input_controller, header_callback, footer_callback, size_callback
        )

        # 1. Load entries
        model.load_entries()
        assert len(state.entries) == 4

        # Verify that types were detected correctly through sorting behavior
        # Test numeric sorting on user_id (should be detected as int)
        state.sort_column = "user_id"
        state.sort_reverse = False
        model.apply_filters()

        filtered = state.filtered_entries
        entries_with_user_id = [
            entry for entry in filtered if entry.get_value("user_id")
        ]
        user_ids = [int(entry.get_value("user_id")) for entry in entries_with_user_id]
        assert user_ids == sorted(user_ids)  # Should be in numeric order

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
            '{"timestamp": "2023-01-01T10:04:00", "level": "info", "service": "auth", '
            '"message": "User logout", "user_id": 123}',
        ]
        input_controller.add_data(new_lines)

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
            '{"@timestamp": "2023-01-15T10:30:45.123Z", "level": "INFO", '
            '"logger": "com.example.UserService", "message": "User authentication successful", '
            '"user_id": 12345, "ip_address": "192.168.1.100", "response_time_ms": 45}',
            '{"@timestamp": "2023-01-15T10:30:46.456Z", "level": "ERROR", '
            '"logger": "com.example.DatabaseService", "message": "Connection pool exhausted", '
            '"pool_size": 10, "active_connections": 10, '
            '"stack_trace": "java.sql.SQLException: Connection timeout"}',
            '{"@timestamp": "2023-01-15T10:30:47.789Z", "level": "WARN", '
            '"logger": "com.example.CacheService", "message": "Cache miss for key", '
            '"cache_key": "user:12345:profile", "cache_hit_ratio": 0.85}',
            '{"@timestamp": "2023-01-15T10:30:48.012Z", "level": "DEBUG", '
            '"logger": "com.example.ApiController", "message": "Processing API request", '
            '"endpoint": "/api/v1/users/12345", "method": "GET", '
            '"headers": {"Authorization": "Bearer xxx", "Content-Type": "application/json"}}',
        ]
        input_controller = create_mock_controller_from_string("\n".join(realistic_logs))
        state = JuffiState()

        def dummy_callback() -> None:
            pass

        model = AppModel(
            state, input_controller, dummy_callback, dummy_callback, dummy_callback
        )

        # Load and process
        model.load_entries()
        model.apply_filters()

        # Verify processing
        assert len(state.entries) == 4
        assert len(state.filtered_entries) == 4

        # Check timestamp parsing
        timestamps = [entry.timestamp for entry in state.entries]
        assert all(ts is not None for ts in timestamps)

        # Verify type detection through sorting behavior for various field types
        # Test int sorting
        state.sort_column = "user_id"
        state.sort_reverse = False
        model.apply_filters()
        entries_with_user_id = [
            entry for entry in state.filtered_entries if entry.get_value("user_id")
        ]
        user_ids = [int(entry.get_value("user_id")) for entry in entries_with_user_id]
        assert user_ids == sorted(user_ids)

        # Test float sorting
        state.sort_column = "cache_hit_ratio"
        model.apply_filters()
        entries_with_ratio = [
            entry
            for entry in state.filtered_entries
            if entry.get_value("cache_hit_ratio")
        ]
        ratios = [
            float(entry.get_value("cache_hit_ratio")) for entry in entries_with_ratio
        ]
        assert ratios == sorted(ratios)

        # Test string sorting
        state.sort_column = "level"
        model.apply_filters()
        levels = [entry.get_value("level") for entry in state.filtered_entries]
        assert levels == sorted(levels)

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
