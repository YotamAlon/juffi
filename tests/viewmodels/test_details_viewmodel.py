"""Tests for the DetailsViewModel class"""

import json

import pytest

from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
from juffi.viewmodels.details import DetailsViewModel


@pytest.fixture(name="state")
def state_fixture():
    """Create a JuffiState instance for testing"""
    return JuffiState()


@pytest.fixture(name="viewmodel")
def viewmodel_fixture(state):
    """Create a DetailsViewModel instance for testing"""
    return DetailsViewModel(state)


@pytest.fixture(name="viewmodel_with_fields")
def viewmodel_with_fields_fixture(state):
    """Create a DetailsViewModel with sample entries for navigation testing"""
    viewmodel = DetailsViewModel(state)

    # Set up entries with fields to test navigation
    entry_data = {
        "level": "info",
        "message": "test",
        "timestamp": "2023-01-01",
        "field4": "value4",
        "field5": "value5",
    }
    entry = LogEntry(json.dumps(entry_data), 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel.enter_mode()  # This will set field_count to 5

    return viewmodel


def test_initialization(viewmodel):
    """Test that DetailsViewModel initializes correctly"""
    # Assert
    assert viewmodel.field_count == 0
    assert viewmodel.current_field == 0
    assert viewmodel.scroll_offset == 0
    assert viewmodel.in_fullscreen_mode is False


def test_navigate_field_up(viewmodel_with_fields):
    """Test navigating to previous field"""
    # Arrange
    viewmodel_with_fields.navigate_field_down()
    viewmodel_with_fields.navigate_field_down()
    initial_field = viewmodel_with_fields.current_field

    # Act
    viewmodel_with_fields.navigate_field_up()

    # Assert
    assert viewmodel_with_fields.current_field == initial_field - 1


def test_navigate_field_up_at_beginning(viewmodel_with_fields):
    """Test navigating up when already at first field"""
    # Arrange - viewmodel starts at field 0
    assert viewmodel_with_fields.current_field == 0

    # Act
    viewmodel_with_fields.navigate_field_up()

    # Assert
    assert viewmodel_with_fields.current_field == 0


def test_navigate_field_down(viewmodel_with_fields):
    """Test navigating to next field"""
    # Arrange
    initial_field = viewmodel_with_fields.current_field

    # Act
    viewmodel_with_fields.navigate_field_down()

    # Assert
    assert viewmodel_with_fields.current_field == initial_field + 1


def test_navigate_field_down_at_end(viewmodel_with_fields):
    """Test navigating down when already at last field"""
    # Arrange
    while viewmodel_with_fields.current_field < viewmodel_with_fields.field_count - 1:
        viewmodel_with_fields.navigate_field_down()
    last_field = viewmodel_with_fields.current_field

    # Act
    viewmodel_with_fields.navigate_field_down()

    # Assert
    assert viewmodel_with_fields.current_field == last_field


def test_navigate_entry_previous(state):
    """Test navigating to previous entry"""
    # Arrange
    entry1 = LogEntry(json.dumps({"message": "entry1"}), 1)
    entry2 = LogEntry(json.dumps({"message": "entry2"}), 2)
    state.set_filtered_entries([entry1, entry2])
    state.current_row = 1
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    viewmodel.navigate_field_down()
    viewmodel.navigate_field_down()

    # Act
    viewmodel.navigate_entry_previous()

    # Assert
    assert state.current_row == 0
    assert viewmodel.current_field == 0
    assert viewmodel.scroll_offset == 0


def test_navigate_entry_next(state):
    """Test navigating to next entry"""
    # Arrange
    entry1 = LogEntry(json.dumps({"message": "entry1"}), 1)
    entry2 = LogEntry(json.dumps({"message": "entry2"}), 2)
    state.set_filtered_entries([entry1, entry2])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    viewmodel.navigate_field_down()
    viewmodel.navigate_field_down()

    # Act
    viewmodel.navigate_entry_next()

    # Assert
    assert state.current_row == 1
    assert viewmodel.current_field == 0
    assert viewmodel.scroll_offset == 0


def test_get_current_entry_no_entries(state):
    """Test getting current entry when no entries exist"""
    # Arrange
    state.set_filtered_entries([])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)

    # Act
    result = viewmodel.get_current_entry()

    # Assert
    assert result is None


def test_get_current_entry_valid(state):
    """Test getting current entry when entries exist"""
    # Arrange
    entry_data = {"level": "info", "message": "test"}
    entry = LogEntry(json.dumps(entry_data), 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)

    # Act
    result = viewmodel.get_current_entry()

    # Assert
    assert result is entry


def test_get_entry_fields_json_entry(viewmodel):
    """Test getting fields from a JSON entry"""
    # Arrange
    entry_data = {"level": "info", "message": "test", "timestamp": "2023-01-01"}
    entry = LogEntry(json.dumps(entry_data), 1)

    # Act
    fields = viewmodel.get_entry_fields(entry)

    # Assert
    expected_fields = [
        ("level", "info"),
        ("message", "test"),
        ("timestamp", "2023-01-01"),
    ]
    assert fields == expected_fields


def test_get_entry_fields_plain_text_entry(viewmodel):
    """Test getting fields from a plain text entry"""
    # Arrange
    entry = LogEntry("This is plain text", 1)

    # Act
    fields = viewmodel.get_entry_fields(entry)

    # Assert
    expected_fields = [("message", "This is plain text")]
    assert fields == expected_fields


def test_enter_mode_no_entries(state):
    """Test entering mode when no entries exist"""
    # Arrange
    state.set_filtered_entries([])
    state.current_row = None
    viewmodel = DetailsViewModel(state)

    # Act
    viewmodel.enter_mode()

    # Assert
    assert viewmodel.field_count == 0
    assert viewmodel.current_field == 0
    assert viewmodel.scroll_offset == 0


def test_enter_mode_with_json_entry(state):
    """Test entering mode with a JSON entry"""
    # Arrange
    entry_data = {"level": "info", "message": "test", "timestamp": "2023-01-01"}
    entry = LogEntry(json.dumps(entry_data), 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)

    # Act
    viewmodel.enter_mode()

    # Assert
    assert viewmodel.field_count == 3  # level, message, timestamp
    assert viewmodel.current_field == 0
    assert viewmodel.scroll_offset == 0


def test_enter_mode_with_plain_text_entry(state):
    """Test entering mode with a plain text entry"""
    # Arrange
    entry = LogEntry("This is plain text", 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)

    # Act
    viewmodel.enter_mode()

    # Assert
    assert viewmodel.field_count == 1  # Just message field
    assert viewmodel.current_field == 0
    assert viewmodel.scroll_offset == 0


def test_update_scroll_for_display_field_above_view(state):
    """Test scroll update when current field is above visible area"""
    # Arrange
    entry_data = {f"field{i}": str(i) for i in range(1, 11)}
    entry = LogEntry(json.dumps(entry_data), 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    for _ in range(8):
        viewmodel.navigate_field_down()

    # Act
    viewmodel.update_scroll_for_display(available_height=3, fields_count=10)

    # Assert
    assert viewmodel.scroll_offset >= 0


def test_update_scroll_for_display_field_below_view(state):
    """Test scroll update when current field is below visible area"""
    # Arrange
    entry_data = {f"field{i}": str(i) for i in range(1, 11)}
    entry = LogEntry(json.dumps(entry_data), 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    for _ in range(8):
        viewmodel.navigate_field_down()
    current_field = viewmodel.current_field

    # Act
    viewmodel.update_scroll_for_display(available_height=3, fields_count=10)

    # Assert
    assert viewmodel.scroll_offset <= current_field


def test_update_scroll_for_display_field_in_view(state):
    """Test scroll update when current field is already visible"""
    # Arrange
    entry_data = {f"field{i}": str(i) for i in range(1, 6)}
    entry = LogEntry(json.dumps(entry_data), 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    viewmodel.navigate_field_down()
    viewmodel.navigate_field_down()
    initial_scroll = viewmodel.scroll_offset

    # Act
    viewmodel.update_scroll_for_display(available_height=5, fields_count=5)

    # Assert
    assert viewmodel.scroll_offset == initial_scroll


def test_update_scroll_for_display_max_scroll_limit(state):
    """Test that scroll offset doesn't exceed maximum"""
    # Arrange
    entry_data = {f"field{i}": str(i) for i in range(1, 6)}
    entry = LogEntry(json.dumps(entry_data), 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    while viewmodel.current_field < viewmodel.field_count - 1:
        viewmodel.navigate_field_down()

    # Act
    viewmodel.update_scroll_for_display(available_height=3, fields_count=5)

    # Assert
    max_scroll = max(0, 5 - 3)
    assert viewmodel.scroll_offset <= max_scroll


def test_update_scroll_for_display_negative_scroll_prevention(state):
    """Test that scroll offset doesn't go negative"""
    # Arrange
    entry_data = {f"field{i}": str(i) for i in range(1, 4)}
    entry = LogEntry(json.dumps(entry_data), 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    assert viewmodel.current_field == 0

    # Act
    viewmodel.update_scroll_for_display(available_height=5, fields_count=3)

    # Assert
    assert viewmodel.scroll_offset >= 0


def test_navigate_to_next_entry_preserves_field_position_when_field_exists(state):
    """Test that field position is preserved when navigating to next entry"""
    # Arrange
    entry1 = LogEntry(
        json.dumps({"level": "info", "message": "First", "timestamp": "2024-01-01"}), 1
    )
    entry2 = LogEntry(
        json.dumps({"level": "error", "message": "Second", "timestamp": "2024-01-02"}),
        2,
    )
    state.set_filtered_entries([entry1, entry2])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    viewmodel.navigate_field_down()

    # Act
    viewmodel.navigate_entry_next()

    # Assert
    assert state.current_row == 1
    assert viewmodel.current_field == 1


def test_navigate_to_previous_entry_preserves_field_position_when_field_exists(state):
    """Test that field position is preserved when navigating to previous entry"""
    # Arrange
    entry1 = LogEntry(
        json.dumps({"level": "info", "message": "First", "timestamp": "2024-01-01"}), 1
    )
    entry2 = LogEntry(
        json.dumps({"level": "error", "message": "Second", "timestamp": "2024-01-02"}),
        2,
    )
    state.set_filtered_entries([entry1, entry2])
    state.current_row = 1
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    viewmodel.navigate_field_down()

    # Act
    viewmodel.navigate_entry_previous()

    # Assert
    assert state.current_row == 0
    assert viewmodel.current_field == 1


def test_navigate_to_entry_with_fewer_fields_stays_at_same_height(state):
    """Test that navigating to entry with fewer fields stays at same height"""
    # Arrange
    entry1 = LogEntry(json.dumps({"a": "1", "b": "2", "c": "3", "d": "4", "e": "5"}), 1)
    entry2 = LogEntry(json.dumps({"a": "1", "b": "2", "c": "3"}), 2)
    state.set_filtered_entries([entry1, entry2])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    viewmodel.navigate_field_down()
    viewmodel.navigate_field_down()

    # Act
    viewmodel.navigate_entry_next()

    # Assert
    assert state.current_row == 1
    assert viewmodel.current_field == 2


def test_navigate_to_entry_with_fewer_fields_clamps_to_last_field(state):
    """Test that navigating to entry with fewer fields clamps to last field"""
    # Arrange
    entry1 = LogEntry(json.dumps({"a": "1", "b": "2", "c": "3", "d": "4", "e": "5"}), 1)
    entry2 = LogEntry(json.dumps({"a": "1", "b": "2"}), 2)
    state.set_filtered_entries([entry1, entry2])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()
    for _ in range(4):
        viewmodel.navigate_field_down()

    # Act
    viewmodel.navigate_entry_next()

    # Assert
    assert state.current_row == 1
    assert viewmodel.current_field == 1


def test_preserves_intended_field_position_across_entries_with_varying_fields(state):
    """Test that intended field position is preserved across varying field counts"""
    # Arrange
    entry1 = LogEntry(json.dumps({"a": "1", "b": "2", "c": "3", "d": "4", "e": "5"}), 1)
    entry2 = LogEntry(json.dumps({"a": "1", "b": "2"}), 2)
    entry3 = LogEntry(
        json.dumps({"a": "1", "b": "2", "c": "3", "d": "4", "e": "5", "f": "6"}), 3
    )
    state.set_filtered_entries([entry1, entry2, entry3])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.enter_mode()

    for _ in range(3):
        viewmodel.navigate_field_down()

    # Act
    viewmodel.navigate_entry_next()
    viewmodel.navigate_entry_next()

    # Assert
    assert state.current_row == 2
    assert viewmodel.current_field == 3


def test_toggle_fullscreen_mode(viewmodel_with_fields):
    """Test toggling fullscreen mode"""
    # Arrange
    assert viewmodel_with_fields.in_fullscreen_mode is False

    # Act
    viewmodel_with_fields.toggle_fullscreen_mode()

    # Assert
    assert viewmodel_with_fields.in_fullscreen_mode is True

    # Act
    viewmodel_with_fields.toggle_fullscreen_mode()

    # Assert
    assert viewmodel_with_fields.in_fullscreen_mode is False


def test_exit_fullscreen_mode(viewmodel_with_fields):
    """Test exiting fullscreen mode"""
    # Arrange
    viewmodel_with_fields.toggle_fullscreen_mode()
    assert viewmodel_with_fields.in_fullscreen_mode is True

    # Act
    viewmodel_with_fields.exit_fullscreen_mode()

    # Assert
    assert viewmodel_with_fields.in_fullscreen_mode is False
    assert viewmodel_with_fields.field_content_scroll_offset == 0


def test_toggle_fullscreen_resets_scroll_offset(viewmodel_with_fields):
    """Test that toggling fullscreen off resets scroll offset"""
    # Arrange
    viewmodel_with_fields.toggle_fullscreen_mode()

    # Act
    viewmodel_with_fields.toggle_fullscreen_mode()

    # Assert
    assert viewmodel_with_fields.field_content_scroll_offset == 0


def test_enter_mode_resets_fullscreen_and_scroll(state):
    """Test that entering mode resets fullscreen and scroll offset"""
    # Arrange
    entry = LogEntry(json.dumps({"message": "test"}), 1)
    state.set_filtered_entries([entry])
    state.current_row = 0
    viewmodel = DetailsViewModel(state)
    viewmodel.toggle_fullscreen_mode()

    # Act
    viewmodel.enter_mode()

    # Assert
    assert viewmodel.in_fullscreen_mode is False
    assert viewmodel.field_content_scroll_offset == 0
