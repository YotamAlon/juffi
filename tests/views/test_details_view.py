"""Tests for the DetailsMode view"""

import curses

import pytest

from juffi.helpers.curses_utils import Size
from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
from juffi.views.details import DetailsMode
from tests.infra.mock_output_controller import MockOutputController


@pytest.fixture(name="state")
def state_fixture() -> JuffiState:
    """Create a JuffiState instance for testing"""
    return JuffiState()


@pytest.fixture(name="output_controller")
def output_controller_fixture() -> MockOutputController:
    """Create a MockOutputController instance for testing"""
    return MockOutputController(Size(24, 80))


@pytest.fixture(name="details_mode")
def details_mode_fixture(
    state: JuffiState, output_controller: MockOutputController
) -> DetailsMode:
    """Create a DetailsMode instance for testing"""
    return DetailsMode(state, output_controller.create_main_window())


@pytest.fixture(name="sample_entries")
def sample_entries_fixture() -> list[LogEntry]:
    """Create sample log entries for testing"""
    return [
        LogEntry(raw_line='{"level": "info", "message": "First entry"}', line_number=1),
        LogEntry(
            raw_line='{"level": "error", "message": "Second entry"}', line_number=2
        ),
    ]


def test_details_mode_draws_entry_title(
    details_mode: DetailsMode,
    state: JuffiState,
    sample_entries: list[LogEntry],
    output_controller: MockOutputController,
) -> None:
    """Test that details mode draws the entry title"""
    # Arrange
    state.filtered_entries = sample_entries
    state.current_row = 0

    # Act
    details_mode.draw(sample_entries)

    # Assert
    screen = output_controller.get_screen()
    assert "Details - Line 1" in screen


def test_details_mode_draws_entry_fields(
    details_mode: DetailsMode,
    state: JuffiState,
    sample_entries: list[LogEntry],
    output_controller: MockOutputController,
) -> None:
    """Test that details mode draws entry fields"""
    # Arrange
    state.filtered_entries = sample_entries
    state.current_row = 0

    # Act
    details_mode.draw(sample_entries)

    # Assert
    line_3 = output_controller.get_screen_line(3)
    assert "level:" in line_3
    assert "info" in line_3

    line_4 = output_controller.get_screen_line(4)
    assert "message:" in line_4
    assert "First entry" in line_4


def test_details_mode_does_not_draw_when_no_entries(
    details_mode: DetailsMode,
    output_controller: MockOutputController,
) -> None:
    """Test that details mode does not draw when there are no entries"""
    # Act
    details_mode.draw([])

    # Assert
    screen = output_controller.get_screen()
    assert screen.strip() == ""


def test_details_mode_navigate_fields_down(
    details_mode: DetailsMode,
    state: JuffiState,
    sample_entries: list[LogEntry],
    output_controller: MockOutputController,
) -> None:
    """Test navigating down through fields in details view"""
    # Arrange
    state.filtered_entries = sample_entries
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.draw(sample_entries)

    # Act
    details_mode.handle_input(curses.KEY_DOWN)
    details_mode.draw(sample_entries)

    # Assert
    screen = output_controller.get_screen()
    assert "Field 2/" in screen


def test_details_mode_navigate_to_next_entry(
    details_mode: DetailsMode,
    state: JuffiState,
    sample_entries: list[LogEntry],
    output_controller: MockOutputController,
) -> None:
    """Test navigating to next entry in details view"""
    # Arrange
    state.filtered_entries = sample_entries
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.draw(sample_entries)

    # Act
    details_mode.handle_input(curses.KEY_RIGHT)
    details_mode.draw(sample_entries)

    # Assert
    screen = output_controller.get_screen()
    assert "Details - Line 2" in screen
    assert "Second entry" in screen


def test_details_mode_navigate_to_previous_entry(
    details_mode: DetailsMode,
    state: JuffiState,
    sample_entries: list[LogEntry],
    output_controller: MockOutputController,
) -> None:
    """Test navigating to previous entry in details view"""
    # Arrange
    state.filtered_entries = sample_entries
    state.current_row = 1
    details_mode.enter_mode()
    details_mode.draw(sample_entries)

    # Act
    details_mode.handle_input(curses.KEY_LEFT)
    details_mode.draw(sample_entries)

    # Assert
    screen = output_controller.get_screen()
    assert "Details - Line 1" in screen
    assert "First entry" in screen


def test_details_mode_shows_field_count(
    details_mode: DetailsMode,
    state: JuffiState,
    sample_entries: list[LogEntry],
    output_controller: MockOutputController,
) -> None:
    """Test that details mode shows field count"""
    # Arrange
    state.filtered_entries = sample_entries
    state.current_row = 0
    details_mode.enter_mode()

    # Act
    details_mode.draw(sample_entries)

    # Assert
    screen = output_controller.get_screen()
    assert "Field 1/" in screen


def test_navigate_to_next_entry_preserves_field_position_when_field_exists(
    details_mode: DetailsMode,
    state: JuffiState,
    output_controller: MockOutputController,
) -> None:
    """Test that navigating to next entry preserves field position when field exists"""
    # Arrange
    entries = [
        LogEntry(
            raw_line='{"level": "info", "message": "First", "timestamp": "2024-01-01"}',
            line_number=1,
        ),
        LogEntry(
            raw_line='{"level": "error", "message": "Second", "timestamp": "2024-01-02"}',
            line_number=2,
        ),
    ]
    state.filtered_entries = entries
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.draw(entries)

    details_mode.handle_input(curses.KEY_DOWN)
    details_mode.draw(entries)

    # Act
    details_mode.handle_input(curses.KEY_RIGHT)
    details_mode.draw(entries)

    # Assert
    screen = output_controller.get_screen()
    assert "Details - Line 2" in screen
    assert "Field 2/" in screen


def test_details_mode_toggles_fullscreen_with_enter(
    details_mode: DetailsMode,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test that details mode toggles fullscreen mode with Enter key"""
    # Arrange
    state.filtered_entries = sample_entries
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.draw(sample_entries)
    assert details_mode.viewmodel.in_fullscreen_mode is False

    # Act
    details_mode.handle_input(ord("\n"))

    # Assert
    assert details_mode.viewmodel.in_fullscreen_mode is True


def test_details_mode_exits_fullscreen_with_enter(
    details_mode: DetailsMode,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test that details mode exits fullscreen mode with Enter key"""
    # Arrange
    state.filtered_entries = sample_entries
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.draw(sample_entries)
    details_mode.handle_input(ord("\n"))
    assert details_mode.viewmodel.in_fullscreen_mode is True

    # Act
    details_mode.handle_input(ord("\n"))

    # Assert
    assert details_mode.viewmodel.in_fullscreen_mode is False


def test_details_mode_exits_fullscreen_with_escape(
    details_mode: DetailsMode,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test that details mode exits fullscreen mode with Escape key"""
    # Arrange
    state.filtered_entries = sample_entries
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.draw(sample_entries)
    details_mode.handle_input(ord("\n"))
    assert details_mode.viewmodel.in_fullscreen_mode is True

    # Act
    details_mode.handle_input(27)

    # Assert
    assert details_mode.viewmodel.in_fullscreen_mode is False


def test_details_mode_draws_fullscreen_view(
    details_mode: DetailsMode,
    state: JuffiState,
    output_controller: MockOutputController,
) -> None:
    """Test that details mode draws fullscreen view correctly"""
    # Arrange
    entry = LogEntry(
        raw_line='{"level": "info", "message": "Test message"}', line_number=1
    )
    state.filtered_entries = [entry]
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.handle_input(ord("\n"))

    # Act
    details_mode.draw([entry])

    # Assert
    screen = output_controller.get_screen()
    assert "Field: level" in screen
    assert "Enter/Esc to exit" in screen


def test_details_mode_fullscreen_shows_scroll_info(
    details_mode: DetailsMode,
    state: JuffiState,
    output_controller: MockOutputController,
) -> None:
    """Test that fullscreen mode shows scroll information"""
    # Arrange
    long_message = "Line\n" * 100
    entry = LogEntry(
        raw_line=f'{{"level": "info", "message": "{long_message}"}}', line_number=1
    )
    state.filtered_entries = [entry]
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.handle_input(curses.KEY_DOWN)
    details_mode.handle_input(ord("\n"))

    # Act
    details_mode.draw([entry])

    # Assert
    screen = output_controller.get_screen()
    assert "Lines" in screen
    assert "of" in screen


def test_details_mode_fullscreen_arrow_down_scrolls(
    details_mode: DetailsMode,
    state: JuffiState,
) -> None:
    """Test that down arrow scrolls in fullscreen mode"""
    # Arrange
    long_message = "Line\n" * 100
    entry = LogEntry(
        raw_line=f'{{"level": "info", "message": "{long_message}"}}', line_number=1
    )
    state.filtered_entries = [entry]
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.handle_input(curses.KEY_DOWN)
    details_mode.handle_input(ord("\n"))
    initial_offset = details_mode.viewmodel.field_content_scroll_offset

    # Act
    details_mode.handle_input(curses.KEY_DOWN)

    # Assert
    assert details_mode.viewmodel.field_content_scroll_offset == initial_offset + 1


def test_details_mode_fullscreen_arrow_up_scrolls(
    details_mode: DetailsMode,
    state: JuffiState,
) -> None:
    """Test that up arrow scrolls in fullscreen mode"""
    # Arrange
    long_message = "Line\n" * 100
    entry = LogEntry(
        raw_line=f'{{"level": "info", "message": "{long_message}"}}', line_number=1
    )
    state.filtered_entries = [entry]
    state.current_row = 0
    details_mode.enter_mode()
    details_mode.handle_input(curses.KEY_DOWN)
    details_mode.handle_input(ord("\n"))
    details_mode.handle_input(curses.KEY_DOWN)
    details_mode.handle_input(curses.KEY_DOWN)
    initial_offset = details_mode.viewmodel.field_content_scroll_offset

    # Act
    details_mode.handle_input(curses.KEY_UP)

    # Assert
    assert details_mode.viewmodel.field_content_scroll_offset == initial_offset - 1
