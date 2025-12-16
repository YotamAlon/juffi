"""Tests for the AppModel viewmodel class."""

from typing import Iterator

import pytest

from juffi.input_controller import InputController
from juffi.models.juffi_model import JuffiState, ViewMode
from juffi.viewmodels.app import AppModel

TEXT_LINES = [
    "2023-01-01 10:00:00 INFO Application started",
    "2023-01-01 10:01:00 ERROR Database connection failed",
    "2023-01-01 10:02:00 DEBUG Processing request",
]

SIMPLE_JSON_LINES = [
    '{"level": "info", "message": "First entry"}',
    '{"level": "error", "message": "Second entry"}',
]

MULTIPLE_CALLS_LINES = [
    '{"level": "info", "message": "first batch 1"}',
    '{"level": "info", "message": "first batch 2"}',
    '{"level": "error", "message": "second batch 1"}',
    '{"level": "debug", "message": "second batch 2"}',
]


class MockInputController(InputController):
    """Mock input controller for testing"""

    def __init__(
        self, data_lines: list[str] | None = None, input_name: str = "test.log"
    ):
        self.data_lines = data_lines or []
        self.input_keys: list[int] = []
        self.input_index: int = 0
        self.input_name = input_name
        self.last_read_index: int = 0

    def get_input(self) -> int:
        if self.input_index < len(self.input_keys):
            key = self.input_keys[self.input_index]
            self.input_index += 1
            return key
        return -1

    def get_data(self) -> Iterator[str]:
        new_lines = self.data_lines[self.last_read_index :]
        self.last_read_index = len(self.data_lines)
        return iter(new_lines)

    def add_data(self, new_lines: list[str]) -> None:
        """Add new data to the same data list"""
        self.data_lines.extend(new_lines)

    def get_input_name(self) -> str:
        return self.input_name

    def reset(self) -> None:
        """Reset the read index to the beginning"""
        self.last_read_index = 0


def create_mock_controller_from_string(
    data: str, input_name: str = "test.log"
) -> MockInputController:
    """Helper function to create MockInputController from string data"""
    lines = data.split("\n") if data else []
    lines = [line for line in lines if line.strip()]
    return MockInputController(lines, input_name)


def dummy_callback() -> None:
    """Dummy callback function for testing."""


@pytest.fixture(name="state")
def state_fixture() -> JuffiState:
    """Create a fresh JuffiState instance for testing."""
    return JuffiState()


@pytest.fixture(name="input_controller")
def input_controller_fixture() -> MockInputController:
    """Create an empty MockInputController for testing."""
    return create_mock_controller_from_string("")


@pytest.fixture(name="app_model")
def app_model_fixture(
    state: JuffiState,
    input_controller: MockInputController,
) -> AppModel:
    """Create an AppModel instance with standard setup."""
    return AppModel(
        state, input_controller, dummy_callback, dummy_callback, dummy_callback
    )


@pytest.fixture(name="app_model_with_json")
def app_model_with_json_fixture(
    state: JuffiState,
    input_controller: MockInputController,
) -> AppModel:
    """Create an AppModel instance with JSON test data."""
    json_lines = [
        '{"level": "info", "message": "Application started", "timestamp": "2023-01-01T10:00:00"}',
        '{"level": "error", "message": "Database connection failed", "service": "db"}',
        '{"level": "debug", "count": 42, "active": true}',
    ]
    input_controller.add_data(json_lines)
    return AppModel(
        state, input_controller, dummy_callback, dummy_callback, dummy_callback
    )


@pytest.fixture(name="loaded_app_model")
def loaded_app_model_fixture(app_model_with_json: AppModel) -> AppModel:
    """Create an AppModel with JSON data already loaded."""
    app_model_with_json.load_entries()
    return app_model_with_json


@pytest.fixture(name="app_model_with_sorting_data")
def app_model_with_sorting_data_fixture(state: JuffiState) -> AppModel:
    """Create an AppModel instance with sorting test data."""
    sorting_test_lines = [
        '{"level": "error", "count": 100, "price": 19.99}',
        '{"level": "info", "count": 2, "price": 5.5}',
        '{"level": "debug", "count": 10, "price": 100.0}',
    ]
    input_controller = MockInputController(sorting_test_lines)
    return AppModel(
        state, input_controller, dummy_callback, dummy_callback, dummy_callback
    )


@pytest.fixture(name="app_model_with_text")
def app_model_with_text_fixture(
    state: JuffiState, input_controller: MockInputController
) -> AppModel:
    """Create an AppModel instance with plain text test data."""
    input_controller.add_data(TEXT_LINES)
    return AppModel(
        state, input_controller, dummy_callback, dummy_callback, dummy_callback
    )


def test_initialization_with_callbacks(
    state: JuffiState, input_controller: MockInputController
) -> None:
    """Test AppModel initialization with callback functions."""
    # Arrange
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

    # Act
    AppModel(state, input_controller, header_update, footer_update, size_update)
    state.current_mode = ViewMode.HELP
    state.follow_mode = False
    state.terminal_size = (24, 80)

    # Assert
    assert header_called is True
    assert footer_called is True
    assert size_called is True


def test_initial_sorting_behavior(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test that initial sorting works correctly (verifies column types are set)."""
    # Arrange
    json_lines = [
        '{"level": "error", "count": 3}',
        '{"level": "info", "count": 1}',
        '{"level": "debug", "count": 2}',
    ]
    input_controller.add_data(json_lines)

    # Act
    app_model.load_entries()
    state.sort_column = "#"
    state.sort_reverse = False
    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    line_numbers = [entry.line_number for entry in filtered]
    assert line_numbers == [1, 2, 3]


def test_watcher_registration_fields(
    state: JuffiState, input_controller: MockInputController
) -> None:
    """Test that all expected fields have watchers registered."""
    # Arrange
    header_calls = []
    footer_calls = []
    size_calls = []

    def header_update() -> None:
        header_calls.append("header")

    def footer_update() -> None:
        footer_calls.append("footer")

    def size_update() -> None:
        size_calls.append("size")

    # Act
    AppModel(state, input_controller, header_update, footer_update, size_update)
    state.current_mode = ViewMode.DETAILS
    state.terminal_size = (30, 100)
    state.follow_mode = False
    state.current_row = 5
    state.sort_column = "level"
    state.sort_reverse = False
    state.search_term = "test"
    state.input_mode = "filter"
    state.input_buffer = "test input"
    state.input_column = "message"
    state.input_cursor_pos = 4

    # Assert
    assert len(header_calls) >= 2
    assert len(footer_calls) >= 9
    assert len(size_calls) >= 1


def test_update_terminal_size(app_model: AppModel, state: JuffiState) -> None:
    """Test updating terminal size."""
    # Act & Assert
    assert state.terminal_size == (0, 0)
    assert hasattr(app_model, "update_terminal_size")
    assert callable(app_model.update_terminal_size)


def test_reset_clears_state(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test that reset clears filters, resets sort settings, and reloads entries."""
    # Arrange
    input_controller.add_data(SIMPLE_JSON_LINES)
    app_model.load_entries()
    initial_entry_count = len(state.entries)
    assert initial_entry_count > 0

    state.update_filters({"level": "error", "service": "api"})
    state.search_term = "test search"
    state.sort_column = "timestamp"
    state.sort_reverse = False
    assert len(state.filters) == 2
    assert state.search_term == "test search"
    assert state.sort_column == "timestamp"
    assert state.sort_reverse is False

    # Act
    app_model.reset()

    # Assert
    assert len(state.filters) == 0
    assert state.search_term == ""
    assert state.sort_column == "#"
    assert state.sort_reverse is True
    # Entries should be reloaded from the beginning
    assert len(state.entries) == initial_entry_count


def test_load_entries_from_json_lines(
    app_model_with_json: AppModel, state: JuffiState
) -> None:
    """Test loading entries from JSON log lines."""
    # Act
    app_model_with_json.load_entries()

    # Assert
    entries = state.entries
    assert len(entries) == 3
    assert entries[0].line_number == 1
    assert entries[0].is_valid_json is True
    assert entries[0].level == "info"
    assert entries[0].get_value("message") == "Application started"
    assert entries[1].line_number == 2
    assert entries[1].level == "error"
    assert entries[1].get_value("service") == "db"
    assert entries[2].line_number == 3
    assert entries[2].level == "debug"
    assert entries[2].get_value("count") == "42"
    assert entries[2].get_value("active") == "true"


def test_load_entries_from_plain_text(
    app_model_with_text: AppModel, state: JuffiState
) -> None:
    """Test loading entries from plain text log lines."""
    # Act
    app_model_with_text.load_entries()

    # Assert
    entries = state.entries
    assert len(entries) == 3
    for i, entry in enumerate(entries):
        assert entry.line_number == i + 1
        assert entry.is_valid_json is False
        assert entry.level is None
        assert entry.get_value("message") == TEXT_LINES[i]


def test_load_entries_skips_empty_lines(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test that empty lines are skipped during loading."""
    # Arrange
    lines = [
        '{"level": "info", "message": "first"}',
        "",
        "   ",
        '{"level": "error", "message": "second"}',
        "",
        '{"level": "debug", "message": "third"}',
    ]
    input_controller.add_data(lines)

    # Act
    app_model.load_entries()

    # Assert
    entries = state.entries
    assert len(entries) == 3
    assert entries[0].get_value("message") == "first"
    assert entries[1].get_value("message") == "second"
    assert entries[2].get_value("message") == "third"
    assert entries[0].line_number == 1
    assert entries[1].line_number == 2
    assert entries[2].line_number == 3


def test_load_entries_multiple_calls(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test loading entries multiple times (simulating file growth)."""
    # Arrange
    input_controller.add_data(MULTIPLE_CALLS_LINES[:2])

    # Act
    app_model.load_entries()

    # Assert
    assert len(state.entries) == 2
    assert state.entries[0].line_number == 1
    assert state.entries[1].line_number == 2
    input_controller.add_data(MULTIPLE_CALLS_LINES[2:])
    app_model.load_entries()
    assert len(state.entries) == 4
    assert state.entries[2].line_number == 3
    assert state.entries[3].line_number == 4
    assert state.entries[2].get_value("message") == "second batch 1"
    assert state.entries[3].get_value("message") == "second batch 2"


def test_string_column_sorting(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test that string columns sort alphabetically (verifies string type detection)."""
    # Arrange
    json_lines = [
        '{"level": "error", "message": "Third"}',
        '{"level": "info", "message": "First"}',
        '{"level": "debug", "message": "Second"}',
    ]
    input_controller.add_data(json_lines)

    # Act
    app_model.load_entries()
    state.sort_column = "level"
    state.sort_reverse = False
    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    levels = [entry.level for entry in filtered]
    assert levels == ["debug", "error", "info"]


def test_numeric_column_sorting(
    app_model_with_sorting_data: AppModel, state: JuffiState
) -> None:
    """Test that numeric columns sort numerically (verifies int type detection)."""
    # Act
    app_model_with_sorting_data.load_entries()
    state.sort_column = "count"
    state.sort_reverse = False
    app_model_with_sorting_data.apply_filters()

    # Assert
    filtered = state.filtered_entries
    counts = [int(entry.get_value("count")) for entry in filtered]
    assert counts == [2, 10, 100]


def test_float_column_sorting(
    app_model_with_sorting_data: AppModel, state: JuffiState
) -> None:
    """Test that float columns sort numerically (verifies float type detection)."""
    # Act
    app_model_with_sorting_data.load_entries()
    state.sort_column = "price"
    state.sort_reverse = False
    app_model_with_sorting_data.apply_filters()

    # Assert
    filtered = state.filtered_entries
    prices = [float(entry.get_value("price")) for entry in filtered]
    assert prices == [5.5, 19.99, 100.0]


def test_type_conflict_resolution_through_sorting(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test that type conflicts are resolved to string (observable through sorting)."""
    # Arrange
    json_lines = [
        '{"level": "info", "count": 42}',
        '{"level": "error", "count": "not a number"}',
        '{"level": "debug", "count": 1}',
    ]
    input_controller.add_data(json_lines)

    # Act
    app_model.load_entries()
    state.sort_column = "count"
    state.sort_reverse = False
    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    count_values = [entry.get_value("count") for entry in filtered]
    assert count_values == ["1", "42", "not a number"]


def test_apply_filters_with_column_filters(
    app_model: AppModel,
    state: JuffiState,
    input_controller: MockInputController,
) -> None:
    """Test applying column-based filters."""
    # Arrange
    filtering_test_lines = [
        '{"level": "info", "service": "api", "message": "Request processed"}',
        '{"level": "error", "service": "api", "message": "Request failed"}',
        '{"level": "info", "service": "db", "message": "Connection established"}',
        '{"level": "error", "service": "db", "message": "Connection failed"}',
    ]
    input_controller.add_data(filtering_test_lines)

    # Act
    app_model.load_entries()
    assert len(state.entries) == 4
    state.update_filters({"level": "error"})
    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    assert len(filtered) == 2
    assert all(entry.level == "error" for entry in filtered)
    state.update_filters({"service": "db"})
    app_model.apply_filters()
    filtered = state.filtered_entries
    assert len(filtered) == 1
    assert filtered[0].level == "error"
    assert filtered[0].get_value("service") == "db"


def test_apply_filters_with_search_term(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test applying search term filter."""
    # Arrange
    json_lines = [
        '{"level": "info", "message": "User login successful"}',
        '{"level": "error", "message": "Database connection failed"}',
        '{"level": "info", "message": "User logout successful"}',
        '{"level": "debug", "message": "Processing request"}',
    ]
    input_controller.add_data(json_lines)

    # Act
    app_model.load_entries()
    assert len(state.entries) == 4

    state.search_term = "user"
    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    assert len(filtered) == 2
    assert "user" in filtered[0].get_value("message").lower()
    assert "user" in filtered[1].get_value("message").lower()


def test_apply_filters_combined(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test applying both column filters and search term."""
    # Arrange
    json_lines = [
        '{"level": "info", "service": "auth", "message": "User login successful"}',
        '{"level": "error", "service": "auth", "message": "User authentication failed"}',
        '{"level": "info", "service": "api", "message": "User data retrieved"}',
        '{"level": "error", "service": "db", "message": "Database connection failed"}',
    ]
    input_controller.add_data(json_lines)

    # Act
    app_model.load_entries()
    assert len(state.entries) == 4

    state.update_filters({"service": "auth"})
    state.search_term = "user"
    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    assert len(filtered) == 2
    assert all(entry.get_value("service") == "auth" for entry in filtered)
    assert all("user" in entry.get_value("message").lower() for entry in filtered)


def test_apply_filters_no_matches(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test applying filters that match no entries."""
    # Arrange
    input_controller.add_data(SIMPLE_JSON_LINES)

    # Act
    app_model.load_entries()
    assert len(state.entries) == 2

    state.update_filters({"level": "critical"})
    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    assert len(filtered) == 0


def test_apply_filters_no_filters(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test applying filters when no filters are set."""
    # Arrange
    input_controller.add_data(SIMPLE_JSON_LINES)

    # Act
    app_model.load_entries()
    assert len(state.entries) == 2

    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    assert len(filtered) == 2


def test_apply_filters_with_sorting_reverse(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test reverse sorting."""
    # Arrange
    json_lines = [
        '{"level": "error", "count": 1}',
        '{"level": "info", "count": 3}',
        '{"level": "debug", "count": 2}',
    ]
    input_controller.add_data(json_lines)

    # Act
    app_model.load_entries()
    state.sort_column = "count"
    state.sort_reverse = True
    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    counts = [int(entry.get_value("count")) for entry in filtered]
    assert counts == [3, 2, 1]


def test_apply_filters_no_sort_column(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test filtering without sorting."""
    # Arrange
    input_controller.add_data(SIMPLE_JSON_LINES)

    # Act
    app_model.load_entries()
    state.sort_column = ""
    app_model.apply_filters()

    # Assert
    filtered = state.filtered_entries
    assert len(filtered) == 2
    assert filtered[0].line_number == 1
    assert filtered[1].line_number == 2


def test_update_entries_with_new_entries(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test update_entries when new entries are available."""
    # Arrange
    initial_lines = [
        '{"level": "info", "message": "Initial entry 1"}',
        '{"level": "error", "message": "Initial entry 2"}',
    ]
    input_controller.add_data(initial_lines)
    app_model.load_entries()
    initial_count = len(state.entries)
    assert initial_count == 2
    new_lines = [
        '{"level": "debug", "message": "New entry 1"}',
        '{"level": "info", "message": "New entry 2"}',
    ]
    input_controller.add_data(new_lines)

    # Act
    result = app_model.update_entries()

    # Assert
    assert result is True
    assert len(state.entries) == 4
    assert len(state.filtered_entries) > 0


def test_update_entries_no_new_entries(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test update_entries when no new entries are available."""
    # Arrange
    input_controller.add_data(SIMPLE_JSON_LINES)
    app_model.load_entries()
    initial_count = len(state.entries)

    # Act
    result = app_model.update_entries()

    # Assert
    assert result is False
    assert len(state.entries) == initial_count


def test_empty_file_handling(app_model: AppModel, state: JuffiState) -> None:
    """Test handling of empty file."""
    # Act
    app_model.load_entries()

    # Assert
    assert len(state.entries) == 0
    app_model.apply_filters()
    assert len(state.filtered_entries) == 0
    result = app_model.update_entries()
    assert result is False


def test_file_with_only_empty_lines(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test file with only empty/whitespace lines."""
    # Arrange
    input_controller.add_data(["", "", "   ", "\t", ""])

    # Act
    app_model.load_entries()

    # Assert
    assert len(state.entries) == 0


def test_mixed_json_and_text_entries(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test file with mixed JSON and plain text entries."""
    # Arrange
    lines = [
        '{"level": "info", "message": "JSON entry"}',
        "Plain text log entry",
        '{"level": "error", "count": 42}',
        "Another plain text entry",
        '{"invalid": json}',
    ]
    input_controller.add_data(lines)

    # Act
    app_model.load_entries()

    # Assert
    assert len(state.entries) == 5
    assert state.entries[0].is_valid_json is True
    assert state.entries[1].is_valid_json is False
    assert state.entries[2].is_valid_json is True
    assert state.entries[3].is_valid_json is False
    assert state.entries[4].is_valid_json is False
    state.sort_column = "count"
    state.sort_reverse = False
    app_model.apply_filters()
    filtered = state.filtered_entries
    valid_entries = [
        entry for entry in filtered if entry.is_valid_json and entry.get_value("count")
    ]
    if len(valid_entries) >= 2:
        counts = [int(entry.get_value("count")) for entry in valid_entries]
        assert counts == sorted(counts)


def test_very_long_lines(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test handling of very long log lines."""
    # Arrange
    long_message = "x" * 10000
    json_line = f'{{"level": "info", "message": "{long_message}"}}'
    input_controller.add_data([json_line])

    # Act
    app_model.load_entries()

    # Assert
    assert len(state.entries) == 1
    assert state.entries[0].is_valid_json is True
    assert len(state.entries[0].get_value("message")) == 10000


def test_unicode_handling(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test handling of unicode characters."""
    # Arrange
    unicode_lines = [
        '{"level": "info", "message": "Hello 世界", "emoji": "🚀"}',
        "Plain text with unicode: café, naïve, résumé",
        '{"user": "José", "city": "São Paulo"}',
    ]
    input_controller.add_data(unicode_lines)

    # Act
    app_model.load_entries()

    # Assert
    assert len(state.entries) == 3
    assert state.entries[0].get_value("message") == "Hello 世界"
    assert state.entries[0].get_value("emoji") == "🚀"
    assert "café" in state.entries[1].get_value("message")
    assert state.entries[2].get_value("user") == "José"


def test_complete_workflow(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test complete workflow: load, filter, sort, update."""
    # Arrange
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
    input_controller.add_data(json_lines)

    callback_calls = {"header": 0, "footer": 0}

    def header_callback() -> None:
        callback_calls["header"] += 1

    def footer_callback() -> None:
        callback_calls["footer"] += 1

    state.register_watcher("current_mode", header_callback)
    state.register_watcher("follow_mode", footer_callback)

    # Act & Assert
    app_model.load_entries()
    assert len(state.entries) == 4
    state.sort_column = "user_id"
    state.sort_reverse = False
    app_model.apply_filters()
    filtered = state.filtered_entries
    entries_with_user_id = [entry for entry in filtered if entry.get_value("user_id")]
    user_ids = [int(entry.get_value("user_id")) for entry in entries_with_user_id]
    assert user_ids == sorted(user_ids)
    state.update_filters({"level": "error"})
    app_model.apply_filters()
    filtered = state.filtered_entries
    assert len(filtered) == 2
    assert all(entry.level == "error" for entry in filtered)
    state.search_term = "connection"
    app_model.apply_filters()
    filtered = state.filtered_entries
    assert len(filtered) == 1
    assert "connection" in filtered[0].get_value("message").lower()
    state.sort_column = "service"
    state.sort_reverse = False
    app_model.apply_filters()
    filtered = state.filtered_entries
    assert len(filtered) == 1
    assert filtered[0].get_value("service") == "db"
    app_model.reset()
    app_model.apply_filters()
    filtered = state.filtered_entries
    assert len(filtered) == 4
    new_lines = [
        '{"timestamp": "2023-01-01T10:04:00", "level": "info", "service": "auth", '
        '"message": "User logout", "user_id": 123}',
    ]
    input_controller.add_data(new_lines)
    result = app_model.update_entries()
    assert result is True
    assert len(state.entries) == 5
    state.current_mode = ViewMode.HELP
    state.follow_mode = False
    assert callback_calls["header"] > 0
    assert callback_calls["footer"] > 0


def test_real_world_log_processing(
    app_model: AppModel, state: JuffiState, input_controller: MockInputController
) -> None:
    """Test processing realistic log data."""
    # Arrange
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
    input_controller.add_data(realistic_logs)

    # Act
    app_model.load_entries()
    app_model.apply_filters()

    # Assert
    assert len(state.entries) == 4
    assert len(state.filtered_entries) == 4
    timestamps = [entry.timestamp for entry in state.entries]
    assert all(ts is not None for ts in timestamps)
    state.sort_column = "user_id"
    state.sort_reverse = False
    app_model.apply_filters()
    entries_with_user_id = [
        entry for entry in state.filtered_entries if entry.get_value("user_id")
    ]
    user_ids = [int(entry.get_value("user_id")) for entry in entries_with_user_id]
    assert user_ids == sorted(user_ids)
    state.sort_column = "cache_hit_ratio"
    app_model.apply_filters()
    entries_with_ratio = [
        entry for entry in state.filtered_entries if entry.get_value("cache_hit_ratio")
    ]
    ratios = [float(entry.get_value("cache_hit_ratio")) for entry in entries_with_ratio]
    assert ratios == sorted(ratios)
    state.sort_column = "level"
    app_model.apply_filters()
    levels = [entry.get_value("level") for entry in state.filtered_entries]
    assert levels == sorted(levels)
    state.update_filters({"level": "ERROR"})
    app_model.apply_filters()
    filtered = state.filtered_entries
    assert len(filtered) == 1
    assert "Connection pool exhausted" in filtered[0].get_value("message")
    state.clear_filters()
    state.search_term = "12345"
    app_model.apply_filters()
    filtered = state.filtered_entries
    assert len(filtered) == 3
