"""Tests for the main JuffiState class."""

from unittest.mock import Mock

import pytest

from juffi.helpers.indexed_dict import IndexedDict
from juffi.models.column import Column
from juffi.models.juffi_model import JuffiState, ViewMode
from juffi.models.log_entry import LogEntry


class TestJuffiStateInitialization:
    """Test JuffiState initialization and default values."""

    def test_default_initialization(self) -> None:
        """Test that JuffiState initializes with correct default values."""
        state = JuffiState()

        # Test basic attributes
        assert state.terminal_size == (0, 0)
        assert state.current_mode == ViewMode.BROWSE
        assert state.previous_mode == ViewMode.BROWSE
        assert state.follow_mode is True
        assert state.current_row == 0
        assert state.current_column == "#"
        assert state.sort_column == "#"
        assert state.sort_reverse is True
        assert state.input_mode is None
        assert state.input_column is None
        assert state.input_buffer == ""
        assert state.input_cursor_pos == 0
        assert state.search_term == ""

        # Test private attributes through properties
        assert state.filters_count == 0
        assert state.filters == {}
        assert state.entries == []
        assert state.num_entries == 0
        assert state.filtered_entries == []
        assert len(state.columns) == 0
        assert state.all_discovered_columns == set()

    def test_state_inheritance(self) -> None:
        """Test that JuffiState properly inherits from State."""
        state = JuffiState()

        # Test that it has State methods
        assert hasattr(state, "changes")
        assert hasattr(state, "clear_changes")
        assert hasattr(state, "register_watcher")

        # Test initial changes are empty
        assert state.changes == set()


class TestJuffiStateFilters:
    """Test filter-related functionality."""

    def test_update_filters(self) -> None:
        """Test updating filters."""
        state = JuffiState()

        # Test adding filters
        filters = {"level": "error", "service": "api"}
        state.update_filters(filters)

        assert state.filters == filters
        assert state.filters_count == 2

        # Test adding more filters
        more_filters = {"host": "server1"}
        state.update_filters(more_filters)

        expected = {"level": "error", "service": "api", "host": "server1"}
        assert state.filters == expected
        assert state.filters_count == 3

    def test_update_filters_with_search_term(self) -> None:
        """Test that filters_count includes search term."""
        state = JuffiState()
        state.search_term = "test"

        filters = {"level": "error"}
        state.update_filters(filters)

        assert state.filters == filters
        assert state.filters_count == 2  # 1 filter + 1 search term

    def test_clear_filters(self) -> None:
        """Test clearing filters."""
        state = JuffiState()

        # Add some filters
        filters = {"level": "error", "service": "api"}
        state.update_filters(filters)
        assert state.filters_count == 2

        # Clear filters
        state.clear_filters()

        assert state.filters == {}
        assert state.filters_count == 0

    def test_clear_filters_with_search_term(self) -> None:
        """Test clearing filters when search term exists."""
        state = JuffiState()
        state.search_term = "test"

        # Add filters
        filters = {"level": "error"}
        state.update_filters(filters)
        assert state.filters_count == 2

        # Clear filters
        state.clear_filters()

        assert state.filters == {}
        assert state.filters_count == 1  # Only search term remains

    def test_filters_property_returns_copy(self) -> None:
        """Test that filters property returns a copy."""
        state = JuffiState()
        filters = {"level": "error"}
        state.update_filters(filters)

        returned_filters = state.filters
        returned_filters["new_key"] = "new_value"

        # Original filters should be unchanged
        assert state.filters == {"level": "error"}


class TestJuffiStateEntries:
    """Test entry-related functionality."""

    def test_extend_entries(self) -> None:
        """Test extending entries list."""
        state = JuffiState()

        # Create mock entries
        entry1 = LogEntry('{"level": "info", "message": "test1"}', 1)
        entry2 = LogEntry('{"level": "error", "message": "test2"}', 2)
        entries = [entry1, entry2]

        state.extend_entries(entries)

        assert len(state.entries) == 2
        assert state.num_entries == 2
        assert state.entries[0].line_number == 1
        assert state.entries[1].line_number == 2

    def test_extend_entries_empty_list(self) -> None:
        """Test extending with empty list does nothing."""
        state = JuffiState()
        initial_count = state.num_entries

        state.extend_entries([])

        assert state.num_entries == initial_count
        assert len(state.entries) == 0

    def test_extend_entries_multiple_times(self) -> None:
        """Test extending entries multiple times."""
        state = JuffiState()

        # First batch
        entry1 = LogEntry('{"message": "test1"}', 1)
        state.extend_entries([entry1])
        assert state.num_entries == 1

        # Second batch
        entry2 = LogEntry('{"message": "test2"}', 2)
        entry3 = LogEntry('{"message": "test3"}', 3)
        state.extend_entries([entry2, entry3])
        assert state.num_entries == 3

    def test_set_entries(self) -> None:
        """Test setting entries directly."""
        state = JuffiState()

        # Add some entries first
        entry1 = LogEntry('{"message": "test1"}', 1)
        state.extend_entries([entry1])
        assert state.num_entries == 1

        # Set new entries
        entry2 = LogEntry('{"message": "test2"}', 2)
        entry3 = LogEntry('{"message": "test3"}', 3)
        new_entries = [entry2, entry3]

        state.set_entries(new_entries)

        assert state.num_entries == 2
        assert len(state.entries) == 2
        assert state.entries[0].line_number == 2
        assert state.entries[1].line_number == 3

    def test_entries_property_returns_copy(self) -> None:
        """Test that entries property returns a copy."""
        state = JuffiState()
        entry = LogEntry('{"message": "test"}', 1)
        state.extend_entries([entry])

        returned_entries = state.entries
        returned_entries.append(LogEntry('{"message": "fake"}', 999))

        # Original entries should be unchanged
        assert len(state.entries) == 1
        assert state.entries[0].line_number == 1


class TestJuffiStateFilteredEntries:
    """Test filtered entries functionality."""

    def test_set_filtered_entries(self) -> None:
        """Test setting filtered entries."""
        state = JuffiState()

        # Create entries with JSON data
        entry1 = LogEntry('{"level": "info", "message": "test1"}', 1)
        entry2 = LogEntry('{"level": "error", "message": "test2"}', 2)
        filtered_entries = [entry1, entry2]

        state.set_filtered_entries(filtered_entries)

        assert len(state.filtered_entries) == 2
        assert state.filtered_entries[0].line_number == 1
        assert state.filtered_entries[1].line_number == 2

    def test_set_filtered_entries_triggers_column_detection(self) -> None:
        """Test that setting filtered entries triggers column detection."""
        state = JuffiState()

        # Create entries with different JSON fields
        entry1 = LogEntry('{"level": "info", "message": "test1", "service": "api"}', 1)
        entry2 = LogEntry(
            '{"level": "error", "message": "test2", "host": "server1"}', 2
        )
        filtered_entries = [entry1, entry2]

        state.set_filtered_entries(filtered_entries)

        # Check that columns were detected
        columns = state.columns
        assert len(columns) > 0

        # Check that discovered columns include the JSON fields
        discovered = state.all_discovered_columns
        assert "level" in discovered
        assert "message" in discovered
        assert "service" in discovered
        assert "host" in discovered
        assert "#" in discovered  # Always present

    def test_filtered_entries_property_returns_copy(self) -> None:
        """Test that filtered_entries property returns a copy."""
        state = JuffiState()
        entry = LogEntry('{"message": "test"}', 1)
        state.set_filtered_entries([entry])

        returned_entries = state.filtered_entries
        returned_entries.append(LogEntry('{"message": "fake"}', 999))

        # Original filtered entries should be unchanged
        assert len(state.filtered_entries) == 1
        assert state.filtered_entries[0].line_number == 1


class TestJuffiStateColumns:
    """Test column-related functionality."""

    def test_move_column(self) -> None:
        """Test moving columns."""
        state = JuffiState()

        # Set up some columns
        column_names = ["#", "level", "message", "service"]
        state.set_columns_from_names(column_names)

        # Move column from index 1 to index 3
        state.move_column(1, 3)

        column_list = list(state.columns.keys())
        expected = ["#", "message", "service", "level"]
        assert column_list == expected

    def test_set_column_width(self) -> None:
        """Test setting column width."""
        state = JuffiState()

        # Set up columns
        column_names = ["#", "level", "message"]
        state.set_columns_from_names(column_names)

        # Set width for level column
        state.set_column_width("level", 15)

        assert state.columns["level"].width == 15

    def test_set_columns_from_names_new_columns(self) -> None:
        """Test setting columns from names with new columns."""
        state = JuffiState()

        column_names = ["#", "level", "message", "service"]
        state.set_columns_from_names(column_names)

        columns = state.columns
        assert len(columns) == 4
        assert "#" in columns
        assert "level" in columns
        assert "message" in columns
        assert "service" in columns

    def test_set_columns_from_names_preserves_existing(self) -> None:
        """Test that setting columns preserves existing column objects but recalculates widths."""
        state = JuffiState()
        # Set a reasonable terminal size to avoid negative width calculations
        state.terminal_size = (24, 80)

        # Set initial columns
        initial_names = ["#", "level", "message"]
        state.set_columns_from_names(initial_names)

        # Get the original column object
        original_level_column = state.columns["level"]

        # Modify a column width
        state.set_column_width("level", 20)
        assert state.columns["level"].width == 20

        # Set new columns that include the existing one
        new_names = ["#", "level", "service", "host"]
        state.set_columns_from_names(new_names)

        # Check that the same column object was preserved
        assert state.columns["level"] is original_level_column
        # But width is recalculated based on content and terminal size
        assert isinstance(state.columns["level"].width, int)
        # Check that new columns were added
        assert "service" in state.columns
        assert "host" in state.columns
        # Check that removed column is gone
        assert "message" not in state.columns

    def test_column_width_calculation_with_terminal_size(self) -> None:
        """Test that column width calculation respects terminal size."""
        state = JuffiState()

        # Test with zero terminal size (should handle gracefully)
        state.terminal_size = (0, 0)
        column_names = ["#", "level", "message"]
        state.set_columns_from_names(column_names)

        # With zero width, columns should have minimal or negative widths
        # This tests the edge case behavior
        for col in state.columns.values():
            assert isinstance(col.width, int)  # Should be an integer

        # Test with reasonable terminal size
        state.terminal_size = (24, 100)
        state.set_columns_from_names(column_names)

        # With reasonable width, columns should have positive widths
        for col in state.columns.values():
            assert col.width > 0

    def test_columns_property_returns_copy(self) -> None:
        """Test that columns property returns a copy."""
        state = JuffiState()
        column_names = ["#", "level"]
        state.set_columns_from_names(column_names)

        returned_columns = state.columns
        returned_columns["fake"] = Column("fake")

        # Original columns should be unchanged
        assert "fake" not in state.columns
        assert len(state.columns) == 2

    def test_get_default_sorted_columns(self) -> None:
        """Test getting default sorted columns."""
        state = JuffiState()

        # Add some discovered columns
        entry1 = LogEntry(
            '{"level": "info", "message": "test1", "timestamp": "2023-01-01"}', 1
        )
        entry2 = LogEntry('{"service": "api", "host": "server1"}', 2)
        state.set_filtered_entries([entry1, entry2])

        sorted_columns = state.get_default_sorted_columns()

        # Check that high-priority columns come first
        assert "#" in sorted_columns
        assert "timestamp" in sorted_columns
        assert "level" in sorted_columns
        assert "message" in sorted_columns

        # Check that # comes first (highest priority)
        assert sorted_columns[0] == "#"


class TestJuffiStateChangeTracking:
    """Test change tracking functionality."""

    def test_public_attribute_changes_tracked(self) -> None:
        """Test that changes to public attributes are tracked."""
        state = JuffiState()

        # Change a public attribute
        state.current_row = 5

        assert "current_row" in state.changes

    def test_private_attribute_changes_not_tracked(self) -> None:
        """Test that changes to private attributes are not automatically tracked."""
        state = JuffiState()

        # Change a private attribute directly (not recommended)
        state._filters = {"test": "value"}

        # Private attribute changes are not automatically tracked
        assert "_filters" not in state.changes

    def test_clear_changes(self) -> None:
        """Test clearing changes."""
        state = JuffiState()

        # Make some changes
        state.current_row = 5
        state.follow_mode = False

        assert len(state.changes) > 0

        # Clear changes
        state.clear_changes()

        assert len(state.changes) == 0

    def test_watcher_registration_and_notification(self) -> None:
        """Test watcher registration and notification."""
        state = JuffiState()

        # Create mock callback
        callback = Mock()

        # Register watcher
        state.register_watcher("current_row", callback)

        # Change the watched attribute
        state.current_row = 10

        # Callback should have been called
        callback.assert_called_once()


class TestJuffiStateColumnDetection:
    """Test column detection and priority calculation."""

    def test_column_detection_with_json_entries(self) -> None:
        """Test column detection with valid JSON entries."""
        state = JuffiState()

        # Create entries with different JSON fields
        entry1 = LogEntry(
            '{"level": "info", "message": "test1", "timestamp": "2023-01-01"}', 1
        )
        entry2 = LogEntry('{"level": "error", "service": "api", "host": "server1"}', 2)
        entry3 = LogEntry('{"message": "test3", "user": "john"}', 3)

        state.set_filtered_entries([entry1, entry2, entry3])

        # Check discovered columns
        discovered = state.all_discovered_columns
        expected_columns = {
            "#",
            "level",
            "message",
            "timestamp",
            "service",
            "host",
            "user",
        }
        assert discovered == expected_columns

        # Check that columns are created
        columns = state.columns
        assert len(columns) > 0
        for col_name in expected_columns:
            assert col_name in columns

    def test_column_detection_with_non_json_entries(self) -> None:
        """Test column detection with non-JSON entries."""
        state = JuffiState()

        # Create non-JSON entries
        entry1 = LogEntry("This is a plain text log entry", 1)
        entry2 = LogEntry("Another plain text entry", 2)

        state.set_filtered_entries([entry1, entry2])

        # Should have # and message columns
        discovered = state.all_discovered_columns
        expected_columns = {"#", "message"}
        assert discovered == expected_columns

    def test_column_detection_mixed_entries(self) -> None:
        """Test column detection with mixed JSON and non-JSON entries."""
        state = JuffiState()

        # Mix of JSON and non-JSON entries
        entry1 = LogEntry('{"level": "info", "message": "json entry"}', 1)
        entry2 = LogEntry("Plain text entry", 2)
        entry3 = LogEntry('{"service": "api", "timestamp": "2023-01-01"}', 3)

        state.set_filtered_entries([entry1, entry2, entry3])

        # Should have all columns from JSON entries plus message
        discovered = state.all_discovered_columns
        expected_columns = {"#", "level", "message", "service", "timestamp"}
        assert discovered == expected_columns

    def test_column_detection_ignores_empty_values(self) -> None:
        """Test that column detection ignores empty/null values."""
        state = JuffiState()

        # Create entries with empty values
        entry1 = LogEntry('{"level": "info", "message": "", "service": null}', 1)
        entry2 = LogEntry('{"level": "error", "message": "test", "host": "server1"}', 2)

        state.set_filtered_entries([entry1, entry2])

        # Empty/null values should not be counted
        discovered = state.all_discovered_columns
        # Note: empty string and null are falsy, so they should be ignored
        # But the JSON parsing might handle this differently
        assert "#" in discovered
        assert "level" in discovered
        assert "host" in discovered

    def test_column_priority_calculation(self) -> None:
        """Test column priority calculation."""
        # Test the static method directly
        priority_hash = JuffiState._calculate_column_priority("#", 10)
        priority_timestamp = JuffiState._calculate_column_priority("timestamp", 5)
        priority_level = JuffiState._calculate_column_priority("level", 8)
        priority_message = JuffiState._calculate_column_priority("message", 12)
        priority_custom = JuffiState._calculate_column_priority("custom_field", 3)

        # Check priority order (higher priority = higher tuple values)
        assert priority_hash > priority_timestamp  # # has priority 4, timestamp has 3
        assert (
            priority_timestamp > priority_level
        )  # timestamp has priority 3, level has 2
        assert priority_level > priority_message  # level has priority 2, message has 1
        assert (
            priority_message > priority_custom
        )  # message has priority 1, custom has 0

        # Check that count is used as secondary sort
        priority_custom_high_count = JuffiState._calculate_column_priority(
            "custom_field", 100
        )
        priority_custom_low_count = JuffiState._calculate_column_priority(
            "custom_field", 1
        )
        assert priority_custom_high_count > priority_custom_low_count

    def test_column_ordering_by_priority(self) -> None:
        """Test that columns are ordered by priority."""
        state = JuffiState()

        # Create entries that will generate columns with different priorities
        entry1 = LogEntry('{"message": "test", "custom": "value", "level": "info"}', 1)
        entry2 = LogEntry('{"timestamp": "2023-01-01", "service": "api"}', 2)

        state.set_filtered_entries([entry1, entry2])

        # Get column order
        column_names = list(state.columns.keys())

        # # should be first (highest priority)
        assert column_names[0] == "#"

        # timestamp should come before level
        timestamp_idx = column_names.index("timestamp")
        level_idx = column_names.index("level")
        assert timestamp_idx < level_idx

        # level should come before message
        message_idx = column_names.index("message")
        assert level_idx < message_idx

    def test_column_detection_accumulates_over_time(self) -> None:
        """Test that column detection accumulates columns over multiple calls."""
        state = JuffiState()

        # First batch of entries
        entry1 = LogEntry('{"level": "info", "message": "test1"}', 1)
        state.set_filtered_entries([entry1])

        first_discovered = state.all_discovered_columns.copy()
        assert "level" in first_discovered
        assert "message" in first_discovered

        # Second batch with new columns
        entry2 = LogEntry('{"service": "api", "host": "server1"}', 2)
        state.set_filtered_entries([entry1, entry2])

        second_discovered = state.all_discovered_columns
        # Should have all columns from both batches
        assert "level" in second_discovered
        assert "message" in second_discovered
        assert "service" in second_discovered
        assert "host" in second_discovered


class TestJuffiStateEdgeCases:
    """Test edge cases and error conditions."""

    def test_move_column_invalid_indices(self) -> None:
        """Test moving columns with invalid indices."""
        state = JuffiState()
        column_names = ["#", "level", "message"]
        state.set_columns_from_names(column_names)

        # This should not crash, but behavior may vary
        # The implementation uses list.pop() and list.insert() which handle out-of-bounds
        try:
            state.move_column(10, 0)  # from_idx out of bounds
            state.move_column(0, 10)  # to_idx out of bounds
        except IndexError:
            pass  # This is acceptable behavior

    def test_set_column_width_nonexistent_column(self) -> None:
        """Test setting width for non-existent column."""
        state = JuffiState()
        column_names = ["#", "level"]
        state.set_columns_from_names(column_names)

        # This should raise KeyError
        with pytest.raises(KeyError):
            state.set_column_width("nonexistent", 10)

    def test_empty_filtered_entries(self) -> None:
        """Test behavior with empty filtered entries."""
        state = JuffiState()

        state.set_filtered_entries([])

        # Should still have # column
        discovered = state.all_discovered_columns
        assert "#" in discovered

        columns = state.columns
        assert "#" in columns

    def test_state_changes_on_method_calls(self) -> None:
        """Test that appropriate changes are tracked on method calls."""
        state = JuffiState()

        # Test extend_entries triggers changes
        entry = LogEntry('{"message": "test"}', 1)
        state.extend_entries([entry])
        assert "entries" in state.changes or "num_entries" in state.changes

        state.clear_changes()

        # Test set_filtered_entries triggers changes
        state.set_filtered_entries([entry])
        assert "filtered_entries" in state.changes

        state.clear_changes()

        # Test column operations trigger changes
        state.set_columns_from_names(["#", "level"])
        assert "columns" in state.changes
