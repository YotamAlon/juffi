"""Test the details view redraw optimization."""

import curses
from unittest.mock import Mock

import pytest

from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
from juffi.views.details import DetailsMode
from juffi.views.entries import EntriesWindow


@pytest.fixture(name="state")
def state_fixture():
    """Create a JuffiState instance for testing."""
    return JuffiState()


@pytest.fixture(name="entries_window")
def entries_window_fixture():
    """Create a mock entries window for testing."""
    return Mock(spec=EntriesWindow)


@pytest.fixture(name="colors")
def colors_fixture():
    """Create colors dictionary for testing."""
    return {"DEFAULT": 1, "HEADER": 2, "INFO": 3, "SELECTED": 4}


@pytest.fixture(name="entries_win")
def entries_win_fixture():
    """Create a mock curses window for testing."""
    mock_win = Mock()
    mock_win.getmaxyx.return_value = (20, 80)
    mock_win.clear = Mock()
    mock_win.noutrefresh = Mock()
    mock_win.addstr = Mock()
    mock_win.refresh = Mock()
    return mock_win


@pytest.fixture(name="filtered_entries")
def filtered_entries_fixture():
    """Create test entries for testing."""
    entry1 = LogEntry('{"level": "info", "message": "test1"}', 1)
    entry2 = LogEntry('{"level": "error", "message": "test2"}', 2)
    return [entry1, entry2]


@pytest.fixture(name="details_mode")
def details_mode_fixture(state, entries_window, colors, entries_win, filtered_entries):
    """Create a DetailsMode instance for testing."""
    state.set_filtered_entries(filtered_entries)
    entries_window.get_current_row.return_value = 0
    return DetailsMode(state, entries_window, colors, entries_win)


def test_initial_draw_happens(details_mode, filtered_entries, entries_win):
    """Test that the initial draw happens."""
    # Act
    details_mode.draw(filtered_entries)

    # Assert
    assert entries_win.clear.call_count > 0
    assert entries_win.refresh.call_count > 0


def test_redundant_draw_skipped(details_mode, filtered_entries, entries_win):
    """Test that redundant draws are skipped."""
    # Arrange
    details_mode.draw(filtered_entries)
    initial_clear_calls = entries_win.clear.call_count
    initial_refresh_calls = entries_win.refresh.call_count

    # Act
    details_mode.draw(filtered_entries)

    # Assert
    assert entries_win.clear.call_count == initial_clear_calls
    assert entries_win.refresh.call_count == initial_refresh_calls


def test_entry_change_triggers_redraw(
    details_mode, filtered_entries, entries_win, entries_window
):
    """Test that changing the current entry triggers a redraw."""
    # Arrange
    details_mode.draw(filtered_entries)
    initial_clear_calls = entries_win.clear.call_count
    initial_refresh_calls = entries_win.refresh.call_count

    # Act
    entries_window.get_current_row.return_value = 1
    details_mode.draw(filtered_entries)

    # Assert
    assert entries_win.clear.call_count > initial_clear_calls
    assert entries_win.refresh.call_count > initial_refresh_calls


def test_window_resize_triggers_redraw(details_mode, filtered_entries, entries_win):
    """Test that window resize triggers a redraw."""
    # Arrange
    details_mode.draw(filtered_entries)
    initial_clear_calls = entries_win.clear.call_count
    initial_refresh_calls = entries_win.refresh.call_count

    # Act
    entries_win.getmaxyx.return_value = (25, 90)
    details_mode.draw(filtered_entries)

    # Assert
    assert entries_win.clear.call_count > initial_clear_calls
    assert entries_win.refresh.call_count > initial_refresh_calls


def test_force_redraw_triggers_redraw(details_mode, filtered_entries, entries_win):
    """Test that force_redraw triggers a redraw."""
    # Arrange
    details_mode.draw(filtered_entries)
    initial_clear_calls = entries_win.clear.call_count
    initial_refresh_calls = entries_win.refresh.call_count

    # Act
    details_mode.force_redraw()
    details_mode.draw(filtered_entries)

    # Assert
    assert entries_win.clear.call_count > initial_clear_calls
    assert entries_win.refresh.call_count > initial_refresh_calls


def test_resize_method_triggers_redraw(details_mode, filtered_entries, entries_win):
    """Test that the resize method triggers a redraw."""
    # Arrange
    details_mode.draw(filtered_entries)
    initial_clear_calls = entries_win.clear.call_count
    initial_refresh_calls = entries_win.refresh.call_count

    # Act
    details_mode.resize()
    details_mode.draw(filtered_entries)

    # Assert
    assert entries_win.clear.call_count > initial_clear_calls
    assert entries_win.refresh.call_count > initial_refresh_calls


def test_input_handling_triggers_redraw(details_mode, filtered_entries, entries_win):
    """Test that input handling triggers a redraw."""
    # Arrange
    details_mode.draw(filtered_entries)
    initial_clear_calls = entries_win.clear.call_count
    initial_refresh_calls = entries_win.refresh.call_count

    # Act
    details_mode.handle_input(curses.KEY_UP)
    details_mode.draw(filtered_entries)

    # Assert
    assert entries_win.clear.call_count > initial_clear_calls
    assert entries_win.refresh.call_count > initial_refresh_calls


def test_enter_mode_triggers_redraw(details_mode, filtered_entries, entries_win):
    """Test that entering mode triggers a redraw."""
    # Arrange
    details_mode.draw(filtered_entries)
    entries_win.clear.reset_mock()
    entries_win.refresh.reset_mock()

    # Act
    details_mode.enter_mode()
    details_mode.draw(filtered_entries)

    # Assert
    assert entries_win.clear.call_count > 0
    assert entries_win.refresh.call_count > 0
