"""Tests for JuffiState business logic."""

import pytest

from juffi.helpers.curses_utils import Size
from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry


@pytest.fixture(name="state")
def state_fixture() -> JuffiState:
    """Create a fresh JuffiState instance for testing."""
    return JuffiState()


def test_filters_count_includes_search_term(state: JuffiState) -> None:
    """Test that filters_count includes search term in the count."""
    # Arrange
    state.search_term = "test"
    state.update_filters({"level": "error"})

    # Act & Assert
    assert state.filters_count == 2


def test_filters_count_without_search_term(state: JuffiState) -> None:
    """Test that filters_count counts only filters when no search term."""
    # Arrange & Act
    state.update_filters({"level": "error", "service": "api"})

    # Assert
    assert state.filters_count == 2


def test_update_filters_accumulates(state: JuffiState) -> None:
    """Test that update_filters accumulates filters across calls."""
    # Arrange
    state.update_filters({"level": "error"})

    # Act
    state.update_filters({"service": "api"})

    # Assert
    assert state.filters == {"level": "error", "service": "api"}


def test_clear_filters(state: JuffiState) -> None:
    """Test that clear_filters removes all filters."""
    # Arrange
    state.update_filters({"level": "error", "service": "api"})

    # Act
    state.clear_filters()

    # Assert
    assert state.filters == {}
    assert state.filters_count == 0


def test_extend_entries(state: JuffiState) -> None:
    """Test that extend_entries adds entries to the state."""
    # Arrange
    entry1 = LogEntry('{"message": "test1"}', 1)
    entry2 = LogEntry('{"message": "test2"}', 2)

    # Act
    state.extend_entries([entry1, entry2])

    # Assert
    assert state.num_entries == 2
    assert state.entries[0].line_number == 1


def test_set_entries_replaces_existing(state: JuffiState) -> None:
    """Test that set_entries replaces existing entries."""
    # Arrange
    entry1 = LogEntry('{"message": "test1"}', 1)
    entry2 = LogEntry('{"message": "test2"}', 2)
    state.extend_entries([entry1, entry2])

    # Act
    state.set_entries([entry1])

    # Assert
    assert state.num_entries == 1
    assert state.entries[0].line_number == 1


def test_set_filtered_entries_triggers_column_detection(state: JuffiState) -> None:
    """Test that set_filtered_entries triggers column detection."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "service": "api"}', 1)
    entry2 = LogEntry('{"level": "error", "host": "server1"}', 2)

    # Act
    state.set_filtered_entries([entry1, entry2])

    # Assert
    discovered = state.all_discovered_columns
    assert "level" in discovered
    assert "service" in discovered
    assert "host" in discovered
    assert "#" in discovered


def test_move_column(state: JuffiState) -> None:
    """Test that move_column reorders columns correctly."""
    # Arrange
    state.set_columns_from_names(["#", "level", "message", "service"])

    # Act
    state.move_column(1, 3)

    # Assert
    assert list(state.columns.keys()) == ["#", "message", "service", "level"]


def test_set_column_width(state: JuffiState) -> None:
    """Test that set_column_width updates column width."""
    # Arrange
    state.set_columns_from_names(["#", "level", "message"])

    # Act
    state.set_column_width("level", 15)

    # Assert
    assert state.columns["level"].width == 15


def test_set_column_width_nonexistent_column_raises(state: JuffiState) -> None:
    """Test that set_column_width raises KeyError for nonexistent column."""
    # Arrange
    state.set_columns_from_names(["#", "level"])

    # Act & Assert
    with pytest.raises(KeyError):
        state.set_column_width("nonexistent", 10)


def test_set_columns_from_names_creates_columns(state: JuffiState) -> None:
    """Test that set_columns_from_names creates columns from names."""
    # Act
    state.set_columns_from_names(["#", "level", "message"])

    # Assert
    assert len(state.columns) == 3
    assert "#" in state.columns
    assert "level" in state.columns


def test_set_columns_from_names_preserves_existing_columns(state: JuffiState) -> None:
    """Test that set_columns_from_names preserves existing column objects."""
    # Arrange
    state.terminal_size = Size(24, 80)
    state.set_columns_from_names(["#", "level", "message"])
    original_level = state.columns["level"]

    # Act
    state.set_columns_from_names(["#", "level", "service"])

    # Assert
    assert state.columns["level"] is original_level
    assert "service" in state.columns
    assert "message" not in state.columns


def test_get_default_sorted_columns(state: JuffiState) -> None:
    """Test that get_default_sorted_columns returns columns in priority order."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "timestamp": "2023-01-01"}', 1)
    entry2 = LogEntry('{"service": "api", "host": "server1"}', 2)
    state.set_filtered_entries([entry1, entry2])

    # Act
    sorted_columns = state.get_default_sorted_columns()

    # Assert
    assert sorted_columns[0] == "#"
    assert "timestamp" in sorted_columns
    assert "level" in sorted_columns


def test_column_detection_with_json_entries(state: JuffiState) -> None:
    """Test that column detection works with JSON entries."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "timestamp": "2023-01-01"}', 1)
    entry2 = LogEntry('{"service": "api", "host": "server1"}', 2)

    # Act
    state.set_filtered_entries([entry1, entry2])

    # Assert
    discovered = state.all_discovered_columns
    assert discovered == {"#", "level", "timestamp", "service", "host"}


def test_column_detection_with_plain_text_entries(state: JuffiState) -> None:
    """Test that column detection works with plain text entries."""
    # Arrange
    entry1 = LogEntry("Plain text log entry", 1)
    entry2 = LogEntry("Another plain text entry", 2)

    # Act
    state.set_filtered_entries([entry1, entry2])

    # Assert
    assert state.all_discovered_columns == {"#", "message"}


def test_column_detection_ignores_empty_values(state: JuffiState) -> None:
    """Test that column detection ignores empty and null values."""
    # Arrange
    entry1 = LogEntry('{"level": "info", "empty_field": "", "null_field": null}', 1)
    entry2 = LogEntry('{"level": "error", "message": "test"}', 2)

    # Act
    state.set_filtered_entries([entry1, entry2])

    # Assert
    discovered = state.all_discovered_columns
    assert "level" in discovered
    assert "message" in discovered
    assert "empty_field" not in discovered
    assert "null_field" not in discovered


def test_column_priority_ordering(state: JuffiState) -> None:
    """Test that columns are ordered by priority."""
    # Arrange
    entry = LogEntry(
        '{"timestamp": "2023-01-01", "level": "info", "message": "test", "custom": "value"}',
        1,
    )

    # Act
    state.set_filtered_entries([entry])

    # Assert
    column_names = list(state.columns.keys())
    assert column_names[0] == "#"
    assert column_names.index("timestamp") < column_names.index("level")
    assert column_names.index("level") < column_names.index("message")
    assert column_names.index("message") < column_names.index("custom")


def test_column_priority_uses_count_as_secondary_sort(state: JuffiState) -> None:
    """Test that column priority uses count as secondary sort."""
    # Arrange
    entry1 = LogEntry('{"field_a": "value", "field_b": "value"}', 1)
    entry2 = LogEntry('{"field_a": "value"}', 2)
    entry3 = LogEntry('{"field_a": "value"}', 3)

    # Act
    state.set_filtered_entries([entry1, entry2, entry3])

    # Assert
    column_names = list(state.columns.keys())
    assert column_names.index("field_a") < column_names.index("field_b")


def test_column_detection_accumulates_over_time(state: JuffiState) -> None:
    """Test that column detection accumulates columns over time."""
    # Arrange
    entry1 = LogEntry('{"level": "info"}', 1)
    entry2 = LogEntry('{"service": "api"}', 2)

    # Act
    state.set_filtered_entries([entry1])
    first_discovered = state.all_discovered_columns.copy()
    state.set_filtered_entries([entry1, entry2])
    second_discovered = state.all_discovered_columns

    # Assert
    assert "level" in first_discovered
    assert "level" in second_discovered
    assert "service" in second_discovered


def test_empty_filtered_entries_includes_line_number_column(state: JuffiState) -> None:
    """Test that empty filtered entries still includes line number column."""
    # Act
    state.set_filtered_entries([])

    # Assert
    assert "#" in state.all_discovered_columns
    assert "#" in state.columns
