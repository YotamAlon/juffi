"""Tests for the EntriesWindow view"""

import curses

import pytest

from juffi.helpers.curses_utils import Color, Size
from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
from juffi.views.entries import EntriesWindow
from tests.infra.mock_output_controller import MockOutputController


@pytest.fixture(name="state")
def state_fixture() -> JuffiState:
    """Create a JuffiState instance for testing"""
    state = JuffiState()
    state.terminal_size = Size(10, 80)
    return state


@pytest.fixture(name="output_controller")
def output_controller_fixture() -> MockOutputController:
    """Create a MockOutputController instance for testing"""
    return MockOutputController(Size(10, 80))


@pytest.fixture(name="entries_window")
def entries_window_fixture(
    state: JuffiState, output_controller: MockOutputController
) -> EntriesWindow:
    """Create an EntriesWindow instance for testing"""
    return EntriesWindow(state, output_controller.create_main_window())


@pytest.fixture(name="sample_entries")
def sample_entries_fixture() -> list[LogEntry]:
    """Create sample log entries for testing"""
    return [
        LogEntry(raw_line='{"level": "info", "message": "Entry 1"}', line_number=1),
        LogEntry(raw_line='{"level": "warn", "message": "Entry 2"}', line_number=2),
        LogEntry(raw_line='{"level": "error", "message": "Entry 3"}', line_number=3),
        LogEntry(raw_line='{"level": "info", "message": "Entry 4"}', line_number=4),
        LogEntry(raw_line='{"level": "debug", "message": "Entry 5"}', line_number=5),
        LogEntry(raw_line='{"level": "info", "message": "Entry 6"}', line_number=6),
        LogEntry(raw_line='{"level": "info", "message": "Entry 7"}', line_number=7),
        LogEntry(raw_line='{"level": "info", "message": "Entry 8"}', line_number=8),
        LogEntry(raw_line='{"level": "info", "message": "Entry 9"}', line_number=9),
        LogEntry(raw_line='{"level": "info", "message": "Entry 10"}', line_number=10),
    ]


def has_selected_color_at_line(
    output_controller: MockOutputController, line: int
) -> bool:
    """Check if a line has the SELECTED color"""
    content = output_controller.get_screen_content()

    for pos, cell in content.items():
        if pos.y == line and cell.color == Color.SELECTED:
            return True
    return False


def test_draw_does_not_raise(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test that draw completes without errors"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 0
    entries_window.set_data()

    entries_window.draw()


def test_handle_navigation_down(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test navigation down"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 0

    result = entries_window.handle_navigation(curses.KEY_DOWN)

    assert result is True
    assert state.current_row == 1


def test_handle_navigation_up(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test navigation up"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 2

    result = entries_window.handle_navigation(curses.KEY_UP)

    assert result is True
    assert state.current_row == 1


def test_goto_line(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test goto_line moves to specified line"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 0

    entries_window.goto_line(5)

    assert state.current_row == 5


def test_reset(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test reset returns to initial state"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 5
    state.current_column = "message"

    entries_window.reset()

    assert state.current_row == 0
    assert state.current_column == "#"


def test_draw_after_scroll_down(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
    output_controller: MockOutputController,
) -> None:
    """Test that scrolling down updates selection colors correctly"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 0
    entries_window.set_data()

    entries_window.draw()

    for _ in range(7):
        entries_window.handle_navigation(curses.KEY_DOWN)
        entries_window.draw()

    assert state.current_row == 7
    assert has_selected_color_at_line(output_controller, 9)
    assert not has_selected_color_at_line(output_controller, 8)

    entries_window.handle_navigation(curses.KEY_DOWN)
    entries_window.draw()

    assert state.current_row == 8
    assert has_selected_color_at_line(output_controller, 9)
    assert not has_selected_color_at_line(output_controller, 8)


def test_draw_after_scroll_up(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
    output_controller: MockOutputController,
) -> None:
    """Test that scrolling up updates selection colors correctly"""
    state.set_filtered_entries(sample_entries)
    entries_window.set_data()
    state.current_row = 5

    entries_window.draw()
    assert has_selected_color_at_line(output_controller, 7)
    assert not has_selected_color_at_line(output_controller, 6)

    entries_window.handle_navigation(curses.KEY_UP)
    entries_window.draw()

    assert state.current_row == 4
    assert not has_selected_color_at_line(output_controller, 7)
    assert has_selected_color_at_line(output_controller, 6)


def test_draw_after_multiple_scrolls(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test that multiple scrolls work correctly"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 0
    entries_window.set_data()

    entries_window.draw()

    for _ in range(5):
        entries_window.handle_navigation(curses.KEY_DOWN)
        entries_window.draw()

    assert state.current_row == 5


def test_set_data_preserves_line(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test that set_data can preserve line number"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 5

    entries_window.prepare_for_data_update()
    entries_window.set_data(preserve_line=True)

    assert state.filtered_entries[state.current_row].line_number == 6


def test_resize_updates_window(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test that resize updates the window dimensions"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 0

    entries_window.resize()
    entries_window.draw()


def test_move_column_right(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test moving column to the right"""
    state.set_filtered_entries(sample_entries)
    state.current_row = 0
    entries_window.set_data()

    initial_columns = list(state.columns.keys())
    state.current_column = initial_columns[0]

    entries_window.move_column(to_the_right=True)

    new_columns = list(state.columns.keys())
    assert new_columns[0] == initial_columns[1]
    assert new_columns[1] == initial_columns[0]


def test_adjust_column_width(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test adjusting column width"""
    state.set_filtered_entries(sample_entries)
    entries_window.set_data()

    first_col = list(state.columns.keys())[0]
    initial_width = state.columns[first_col].width

    entries_window.adjust_column_width(delta=10)

    assert state.columns[first_col].width == max(5, min(100, initial_width + 10))


def test_get_current_column(
    entries_window: EntriesWindow,
    state: JuffiState,
    sample_entries: list[LogEntry],
) -> None:
    """Test getting current column"""
    state.set_filtered_entries(sample_entries)
    entries_window.set_data()

    columns = list(state.columns.keys())
    if len(columns) > 1:
        state.current_column = columns[1]
        current_col = entries_window.get_current_column()
        assert current_col == columns[1]
