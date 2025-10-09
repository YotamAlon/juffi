"""Tests for the main JuffiState class."""

from unittest.mock import Mock

import pytest

from juffi.models.column import Column
from juffi.models.juffi_model import JuffiState, ViewMode
from juffi.models.log_entry import LogEntry


@pytest.fixture(name="state")
def state_fixture() -> JuffiState:
    """Create a fresh JuffiState instance for testing."""
    return JuffiState()


def test_default_initialization(state: JuffiState) -> None:
    """Test that JuffiState initializes with correct default values."""
    # Assert
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
    assert state.filters_count == 0
    assert state.filters == {}
    assert state.entries == []
    assert state.num_entries == 0
    assert state.filtered_entries == []
    assert len(state.columns) == 0
    assert state.all_discovered_columns == set()


def test_state_inheritance(state: JuffiState) -> None:
    """Test that JuffiState properly inherits from State."""
    # Assert
    assert hasattr(state, "changes")
    assert hasattr(state, "clear_changes")
    assert hasattr(state, "register_watcher")
    assert state.changes == set()


def test_update_filters(state: JuffiState) -> None:
    """Test updating filters."""
    # Arrange
    filters = {"level": "error", "service": "api"}

    # Act
    state.update_filters(filters)

    # Assert
    assert state.filters == filters
    assert state.filters_count == 2


def test_update_filters_multiple_times(state: JuffiState) -> None:
    """Test adding more filters."""
    # Arrange
    initial_filters = {"level": "error", "service": "api"}
    state.update_filters(initial_filters)
    more_filters = {"host": "server1"}

    # Act
    state.update_filters(more_filters)

    # Assert
    expected = {"level": "error", "service": "api", "host": "server1"}
    assert state.filters == expected
    assert state.filters_count == 3


def test_update_filters_with_search_term(state: JuffiState) -> None:
    """Test that filters_count includes search term."""
    # Arrange
    state.search_term = "test"
    filters = {"level": "error"}

    # Act
    state.update_filters(filters)

    # Assert
    assert state.filters == filters
    assert state.filters_count == 2


def test_clear_filters(state: JuffiState) -> None:
    """Test clearing filters."""
    # Arrange
    filters = {"level": "error", "service": "api"}
    state.update_filters(filters)

    # Act
    state.clear_filters()

    # Assert
    assert state.filters == {}
    assert state.filters_count == 0


def test_clear_filters_with_search_term(state: JuffiState) -> None:
    """Test clearing filters when search term exists."""
    # Arrange
    state.search_term = "test"
    filters = {"level": "error"}
    state.update_filters(filters)

    # Act
    state.clear_filters()

    # Assert
    assert state.filters == {}
    assert state.filters_count == 1


def test_filters_property_returns_copy(state: JuffiState) -> None:
    """Test that filters property returns a copy."""
    # Arrange
    filters = {"level": "error"}
    state.update_filters(filters)

    # Act
    returned_filters = state.filters
    returned_filters["new_key"] = "new_value"

    # Assert
    assert state.filters == {"level": "error"}


def test_extend_entries(state: JuffiState) -> None:
    """Test extending entries list."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "message": "test1"}', 1)
    entry2 = LogEntry('{"level": "error", "message": "test2"}', 2)
    entries = [entry1, entry2]

    # Act
    state.extend_entries(entries)

    # Assert
    assert len(state.entries) == 2
    assert state.num_entries == 2
    assert state.entries[0].line_number == 1
    assert state.entries[1].line_number == 2


def test_extend_entries_empty_list(state: JuffiState) -> None:
    """Test extending with empty list does nothing."""
    # Arrange
    initial_count = state.num_entries

    # Act
    state.extend_entries([])

    # Assert
    assert state.num_entries == initial_count
    assert len(state.entries) == 0


def test_extend_entries_multiple_times(state: JuffiState) -> None:
    """Test extending entries multiple times."""
    # Arrange
    entry1 = LogEntry('{"message": "test1"}', 1)
    entry2 = LogEntry('{"message": "test2"}', 2)
    entry3 = LogEntry('{"message": "test3"}', 3)

    # Act
    state.extend_entries([entry1])
    state.extend_entries([entry2, entry3])

    # Assert
    assert state.num_entries == 3


def test_set_entries(state: JuffiState) -> None:
    """Test setting entries directly."""
    # Arrange
    entry1 = LogEntry('{"message": "test1"}', 1)
    state.extend_entries([entry1])
    entry2 = LogEntry('{"message": "test2"}', 2)
    entry3 = LogEntry('{"message": "test3"}', 3)
    new_entries = [entry2, entry3]

    # Act
    state.set_entries(new_entries)

    # Assert
    assert state.num_entries == 2
    assert len(state.entries) == 2
    assert state.entries[0].line_number == 2
    assert state.entries[1].line_number == 3


def test_entries_property_returns_copy(state: JuffiState) -> None:
    """Test that entries property returns a copy."""
    # Arrange
    entry = LogEntry('{"message": "test"}', 1)
    state.extend_entries([entry])

    # Act
    returned_entries = state.entries
    returned_entries.append(LogEntry('{"message": "fake"}', 999))

    # Assert
    assert len(state.entries) == 1
    assert state.entries[0].line_number == 1


def test_set_filtered_entries(state: JuffiState) -> None:
    """Test setting filtered entries."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "message": "test1"}', 1)
    entry2 = LogEntry('{"level": "error", "message": "test2"}', 2)
    filtered_entries = [entry1, entry2]

    # Act
    state.set_filtered_entries(filtered_entries)

    # Assert
    assert len(state.filtered_entries) == 2
    assert state.filtered_entries[0].line_number == 1
    assert state.filtered_entries[1].line_number == 2


def test_set_filtered_entries_triggers_column_detection(state: JuffiState) -> None:
    """Test that setting filtered entries triggers column detection."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "message": "test1", "service": "api"}', 1)
    entry2 = LogEntry('{"level": "error", "message": "test2", "host": "server1"}', 2)
    filtered_entries = [entry1, entry2]

    # Act
    state.set_filtered_entries(filtered_entries)

    # Assert
    columns = state.columns
    assert len(columns) > 0
    discovered = state.all_discovered_columns
    assert "level" in discovered
    assert "message" in discovered
    assert "service" in discovered
    assert "host" in discovered
    assert "#" in discovered


def test_filtered_entries_property_returns_copy(state: JuffiState) -> None:
    """Test that filtered_entries property returns a copy."""
    # Arrange
    entry = LogEntry('{"message": "test"}', 1)
    state.set_filtered_entries([entry])

    # Act
    returned_entries = state.filtered_entries
    returned_entries.append(LogEntry('{"message": "fake"}', 999))

    # Assert
    assert len(state.filtered_entries) == 1
    assert state.filtered_entries[0].line_number == 1


def test_move_column(state: JuffiState) -> None:
    """Test moving columns."""
    # Arrange
    column_names = ["#", "level", "message", "service"]
    state.set_columns_from_names(column_names)

    # Act
    state.move_column(1, 3)

    # Assert
    column_list = list(state.columns.keys())
    expected = ["#", "message", "service", "level"]
    assert column_list == expected


def test_set_column_width(state: JuffiState) -> None:
    """Test setting column width."""
    # Arrange
    column_names = ["#", "level", "message"]
    state.set_columns_from_names(column_names)

    # Act
    state.set_column_width("level", 15)

    # Assert
    assert state.columns["level"].width == 15


def test_set_columns_from_names_new_columns(state: JuffiState) -> None:
    """Test setting columns from names with new columns."""
    # Arrange
    column_names = ["#", "level", "message", "service"]

    # Act
    state.set_columns_from_names(column_names)

    # Assert
    columns = state.columns
    assert len(columns) == 4
    assert "#" in columns
    assert "level" in columns
    assert "message" in columns
    assert "service" in columns


def test_set_columns_from_names_preserves_existing(state: JuffiState) -> None:
    """Test that setting columns preserves existing column objects but recalculates widths."""
    # Arrange
    state.terminal_size = (24, 80)
    initial_names = ["#", "level", "message"]
    state.set_columns_from_names(initial_names)
    original_level_column = state.columns["level"]
    state.set_column_width("level", 20)
    new_names = ["#", "level", "service", "host"]

    # Act
    state.set_columns_from_names(new_names)

    # Assert
    assert state.columns["level"] is original_level_column
    assert isinstance(state.columns["level"].width, int)
    assert "service" in state.columns
    assert "host" in state.columns
    assert "message" not in state.columns


def test_column_width_calculation_with_terminal_size(state: JuffiState) -> None:
    """Test that column width calculation respects terminal size."""
    # Arrange
    column_names = ["#", "level", "message"]

    # Act
    state.terminal_size = (0, 0)
    state.set_columns_from_names(column_names)

    # Assert
    for col in state.columns.values():
        assert isinstance(col.width, int)


def test_column_width_calculation_with_reasonable_terminal_size(
    state: JuffiState,
) -> None:
    """Test that column width calculation with reasonable terminal size."""
    # Arrange
    column_names = ["#", "level", "message"]

    # Act
    state.terminal_size = (24, 100)
    state.set_columns_from_names(column_names)

    # Assert
    for col in state.columns.values():
        assert col.width > 0


def test_columns_property_returns_copy(state: JuffiState) -> None:
    """Test that columns property returns a copy."""
    # Arrange
    column_names = ["#", "level"]
    state.set_columns_from_names(column_names)

    # Act
    returned_columns = state.columns
    returned_columns["fake"] = Column("fake")

    # Assert
    assert "fake" not in state.columns
    assert len(state.columns) == 2


def test_get_default_sorted_columns(state: JuffiState) -> None:
    """Test getting default sorted columns."""
    # Arrange
    entry1 = LogEntry(
        '{"level": "info", "message": "test1", "timestamp": "2023-01-01"}', 1
    )
    entry2 = LogEntry('{"service": "api", "host": "server1"}', 2)
    state.set_filtered_entries([entry1, entry2])

    # Act
    sorted_columns = state.get_default_sorted_columns()

    # Assert
    assert "#" in sorted_columns
    assert "timestamp" in sorted_columns
    assert "level" in sorted_columns
    assert "message" in sorted_columns
    assert sorted_columns[0] == "#"


def test_public_attribute_changes_tracked(state: JuffiState) -> None:
    """Test that changes to public attributes are tracked."""
    # Act
    state.current_row = 5

    # Assert
    assert "current_row" in state.changes


def test_only_public_attribute_changes_tracked(state: JuffiState) -> None:
    """Test that only public attribute changes are tracked."""
    # Arrange
    state.clear_changes()

    # Act
    state.current_row = 5

    # Assert
    assert "current_row" in state.changes
    assert len(state.changes) == 1


def test_clear_changes(state: JuffiState) -> None:
    """Test clearing changes."""
    # Arrange
    state.current_row = 5
    state.follow_mode = False

    # Act
    state.clear_changes()

    # Assert
    assert len(state.changes) == 0


def test_watcher_registration_and_notification(state: JuffiState) -> None:
    """Test watcher registration and notification."""
    # Arrange
    callback = Mock()
    state.register_watcher("current_row", callback)

    # Act
    state.current_row = 10

    # Assert
    callback.assert_called_once()


def test_column_detection_with_json_entries(state: JuffiState) -> None:
    """Test column detection with valid JSON entries."""
    # Arrange
    entry1 = LogEntry(
        '{"level": "info", "message": "test1", "timestamp": "2023-01-01"}', 1
    )
    entry2 = LogEntry('{"level": "error", "service": "api", "host": "server1"}', 2)
    entry3 = LogEntry('{"message": "test3", "user": "john"}', 3)

    # Act
    state.set_filtered_entries([entry1, entry2, entry3])

    # Assert
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
    columns = state.columns
    assert len(columns) > 0
    for col_name in expected_columns:
        assert col_name in columns


def test_column_detection_with_non_json_entries(state: JuffiState) -> None:
    """Test column detection with non-JSON entries."""
    # Arrange
    entry1 = LogEntry("This is a plain text log entry", 1)
    entry2 = LogEntry("Another plain text entry", 2)

    # Act
    state.set_filtered_entries([entry1, entry2])

    # Assert
    discovered = state.all_discovered_columns
    expected_columns = {"#", "message"}
    assert discovered == expected_columns


def test_column_detection_mixed_entries(state: JuffiState) -> None:
    """Test column detection with mixed JSON and non-JSON entries."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "message": "json entry"}', 1)
    entry2 = LogEntry("Plain text entry", 2)
    entry3 = LogEntry('{"service": "api", "timestamp": "2023-01-01"}', 3)

    # Act
    state.set_filtered_entries([entry1, entry2, entry3])

    # Assert
    discovered = state.all_discovered_columns
    expected_columns = {"#", "level", "message", "service", "timestamp"}
    assert discovered == expected_columns


def test_column_detection_ignores_empty_values(state: JuffiState) -> None:
    """Test that column detection ignores empty/null values."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "message": "", "service": null}', 1)
    entry2 = LogEntry('{"level": "error", "message": "test", "host": "server1"}', 2)

    # Act
    state.set_filtered_entries([entry1, entry2])

    # Assert
    discovered = state.all_discovered_columns
    assert "#" in discovered
    assert "level" in discovered
    assert "host" in discovered


def test_column_priority_ordering(state: JuffiState) -> None:
    """Test that columns are ordered by priority: # > timestamp > level > message > custom."""
    # Arrange
    entry = LogEntry(
        '{"#": 1, "timestamp": "2023-01-01", "level": "info", '
        '"message": "test", "custom_field": "value"}',
        1,
    )

    # Act
    state.set_filtered_entries([entry])

    # Assert
    column_names = list(state.columns.keys())
    hash_idx = column_names.index("#")
    timestamp_idx = column_names.index("timestamp")
    level_idx = column_names.index("level")
    message_idx = column_names.index("message")
    custom_idx = column_names.index("custom_field")

    assert hash_idx < timestamp_idx
    assert timestamp_idx < level_idx
    assert level_idx < message_idx
    assert message_idx < custom_idx


def test_column_priority_uses_count_as_secondary_sort(state: JuffiState) -> None:
    """Test that count is used as secondary sort for column priority."""
    # Arrange
    entry1 = LogEntry('{"field_a": "value", "field_b": "value"}', 1)
    entry2 = LogEntry('{"field_a": "value"}', 2)
    entry3 = LogEntry('{"field_a": "value"}', 3)

    # Act
    state.set_filtered_entries([entry1, entry2, entry3])

    # Assert
    column_names = list(state.columns.keys())
    field_a_idx = column_names.index("field_a")
    field_b_idx = column_names.index("field_b")
    assert field_a_idx < field_b_idx


def test_column_ordering_by_priority(state: JuffiState) -> None:
    """Test that columns are ordered by priority."""
    # Arrange
    entry1 = LogEntry('{"message": "test", "custom": "value", "level": "info"}', 1)
    entry2 = LogEntry('{"timestamp": "2023-01-01", "service": "api"}', 2)

    # Act
    state.set_filtered_entries([entry1, entry2])

    # Assert
    column_names = list(state.columns.keys())
    assert column_names[0] == "#"
    timestamp_idx = column_names.index("timestamp")
    level_idx = column_names.index("level")
    assert timestamp_idx < level_idx
    message_idx = column_names.index("message")
    assert level_idx < message_idx


def test_column_detection_accumulates_over_time(state: JuffiState) -> None:
    """Test that column detection accumulates columns over multiple calls."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "message": "test1"}', 1)
    entry2 = LogEntry('{"service": "api", "host": "server1"}', 2)

    # Act
    state.set_filtered_entries([entry1])
    first_discovered = state.all_discovered_columns.copy()
    state.set_filtered_entries([entry1, entry2])
    second_discovered = state.all_discovered_columns

    # Assert
    assert "level" in first_discovered
    assert "message" in first_discovered
    assert "level" in second_discovered
    assert "message" in second_discovered
    assert "service" in second_discovered
    assert "host" in second_discovered


def test_move_column_invalid_indices(state: JuffiState) -> None:
    """Test moving columns with invalid indices."""
    # Arrange
    column_names = ["#", "level", "message"]
    state.set_columns_from_names(column_names)

    # Act & Assert
    try:
        state.move_column(10, 0)
        state.move_column(0, 10)
    except IndexError:
        pass


def test_set_column_width_nonexistent_column(state: JuffiState) -> None:
    """Test setting width for non-existent column."""
    # Arrange
    column_names = ["#", "level"]
    state.set_columns_from_names(column_names)

    # Act & Assert
    with pytest.raises(KeyError):
        state.set_column_width("nonexistent", 10)


def test_empty_filtered_entries(state: JuffiState) -> None:
    """Test behavior with empty filtered entries."""
    # Act
    state.set_filtered_entries([])

    # Assert
    discovered = state.all_discovered_columns
    assert "#" in discovered
    columns = state.columns
    assert "#" in columns


def test_extend_entries_triggers_changes(state: JuffiState) -> None:
    """Test that extend_entries triggers changes."""
    # Arrange
    entry = LogEntry('{"message": "test"}', 1)

    # Act
    state.extend_entries([entry])

    # Assert
    assert "entries" in state.changes or "num_entries" in state.changes


def test_set_filtered_entries_triggers_changes(state: JuffiState) -> None:
    """Test that set_filtered_entries triggers changes."""
    # Arrange
    entry = LogEntry('{"message": "test"}', 1)

    # Act
    state.set_filtered_entries([entry])

    # Assert
    assert "filtered_entries" in state.changes


def test_column_operations_trigger_changes(state: JuffiState) -> None:
    """Test that column operations trigger changes."""
    # Act
    state.set_columns_from_names(["#", "level"])

    # Assert
    assert "columns" in state.changes
