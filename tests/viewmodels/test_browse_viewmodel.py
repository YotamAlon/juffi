"""Tests for the browse viewmodel"""

from unittest.mock import Mock

import pytest

from juffi.models.juffi_model import JuffiState
from juffi.viewmodels.browse import BrowseViewModel


@pytest.fixture(name="state")
def state_fixture():
    """Create a JuffiState instance for testing"""
    return JuffiState()


@pytest.fixture(name="callbacks")
def callbacks_fixture():
    """Create mock callbacks for testing"""
    return {
        "on_apply_filters": Mock(),
        "on_load_entries": Mock(),
        "on_reset": Mock(),
    }


@pytest.fixture(name="viewmodel")
def viewmodel_fixture(state, callbacks):
    """Create a BrowseViewModel instance for testing"""
    return BrowseViewModel(
        state=state,
        no_follow=False,
        on_apply_filters=callbacks["on_apply_filters"],
        on_load_entries=callbacks["on_load_entries"],
        on_reset=callbacks["on_reset"],
    )


def test_init_sets_follow_mode():
    """Test that initialization sets follow mode correctly"""
    # Test with no_follow=False (follow mode should be True)
    state1 = JuffiState()
    BrowseViewModel(
        state=state1,
        no_follow=False,
        on_apply_filters=Mock(),
        on_load_entries=Mock(),
        on_reset=Mock(),
    )
    assert state1.follow_mode is True

    # Test with no_follow=True (follow mode should be False)
    state2 = JuffiState()
    BrowseViewModel(
        state=state2,
        no_follow=True,
        on_apply_filters=Mock(),
        on_load_entries=Mock(),
        on_reset=Mock(),
    )
    assert state2.follow_mode is False


def test_handle_search_command(state, viewmodel):
    """Test search command handling"""
    state.search_term = "test search"

    viewmodel.handle_search_command()

    assert state.input_mode == "search"
    assert state.input_buffer == "test search"


def test_handle_filter_command_with_column(state, viewmodel):
    """Test filter command handling with valid column"""
    state.update_filters({"level": "error"})

    viewmodel.handle_filter_command("level")

    assert state.input_mode == "filter"
    assert state.input_column == "level"
    assert state.input_buffer == "error"


def test_handle_filter_command_without_column(state, viewmodel):
    """Test filter command handling without column"""
    viewmodel.handle_filter_command(None)

    assert state.input_mode is None
    assert state.input_column is None


def test_handle_goto_command(state, viewmodel):
    """Test goto command handling"""
    viewmodel.handle_goto_command()

    assert state.input_mode == "goto"
    assert state.input_buffer == ""


def test_handle_clear_filters_command(state, viewmodel, callbacks):
    """Test clear filters command handling"""
    state.update_filters({"level": "error"})
    state.search_term = "test"

    viewmodel.handle_clear_filters_command()

    assert len(state.filters) == 0
    assert state.search_term == ""
    callbacks["on_apply_filters"].assert_called_once()


def test_handle_sort_command_new_column(state, viewmodel, callbacks):
    """Test sort command with new column"""
    viewmodel.handle_sort_command("timestamp", reverse=False)

    assert state.sort_column == "timestamp"
    assert state.sort_reverse is False
    callbacks["on_apply_filters"].assert_called_once()


def test_handle_sort_command_same_column_toggle(state, viewmodel, callbacks):
    """Test sort command with same column toggles reverse"""
    state.sort_column = "timestamp"
    state.sort_reverse = False

    viewmodel.handle_sort_command("timestamp", reverse=False)

    assert state.sort_column == "timestamp"
    assert state.sort_reverse is True
    callbacks["on_apply_filters"].assert_called_once()


def test_handle_sort_command_reverse(state, viewmodel, callbacks):
    """Test sort command with reverse=True"""
    viewmodel.handle_sort_command("level", reverse=True)

    assert state.sort_column == "level"
    assert state.sort_reverse is True
    callbacks["on_apply_filters"].assert_called_once()


def test_handle_sort_command_without_column(viewmodel, callbacks):
    """Test sort command without column"""
    viewmodel.handle_sort_command(None, reverse=False)

    callbacks["on_apply_filters"].assert_not_called()


def test_handle_toggle_follow_command(state, viewmodel):
    """Test toggle follow mode command"""
    initial_follow_mode = state.follow_mode

    viewmodel.handle_toggle_follow_command()

    assert state.follow_mode == (not initial_follow_mode)


def test_handle_reload_command(viewmodel, callbacks):
    """Test reload command"""
    viewmodel.handle_reload_command()

    callbacks["on_load_entries"].assert_called_once()
    callbacks["on_apply_filters"].assert_called_once()


def test_handle_reset_command(viewmodel, callbacks):
    """Test reset command"""
    viewmodel.handle_reset_command()

    callbacks["on_reset"].assert_called_once()
    callbacks["on_apply_filters"].assert_called_once()


def test_handle_input_submission_search(state, viewmodel, callbacks):
    """Test input submission for search mode"""
    state.input_mode = "search"
    state.input_buffer = "new search term"
    goto_callback = Mock()

    viewmodel.handle_input_submission(goto_callback)

    assert state.search_term == "new search term"
    callbacks["on_apply_filters"].assert_called_once()
    assert state.input_mode is None
    assert state.input_buffer == ""


def test_handle_input_submission_filter(state, viewmodel, callbacks):
    """Test input submission for filter mode"""
    state.input_mode = "filter"
    state.input_column = "level"
    state.input_buffer = "warning"
    goto_callback = Mock()

    viewmodel.handle_input_submission(goto_callback)

    assert state.filters.get("level") == "warning"
    callbacks["on_apply_filters"].assert_called_once()
    assert state.input_mode is None


def test_handle_input_submission_goto_valid(state, viewmodel, callbacks):
    """Test input submission for goto mode with valid line number"""
    state.input_mode = "goto"
    state.input_buffer = "42"
    goto_callback = Mock()

    viewmodel.handle_input_submission(goto_callback)

    goto_callback.assert_called_once_with(42)
    callbacks["on_apply_filters"].assert_called_once()
    assert state.input_mode is None


def test_handle_input_submission_goto_invalid(state, viewmodel, callbacks):
    """Test input submission for goto mode with invalid line number"""
    state.input_mode = "goto"
    state.input_buffer = "not_a_number"
    goto_callback = Mock()

    viewmodel.handle_input_submission(goto_callback)

    goto_callback.assert_not_called()
    callbacks["on_apply_filters"].assert_called_once()
    assert state.input_mode is None


def test_handle_input_cancellation(state, viewmodel):
    """Test input cancellation"""
    state.input_mode = "search"
    state.input_buffer = "some text"
    state.input_column = "level"
    state.input_cursor_pos = 5

    viewmodel.handle_input_cancellation()

    assert state.input_mode is None
    assert state.input_buffer == ""
    assert state.input_column is None
    assert state.input_cursor_pos == 0


def test_handle_input_backspace(state, viewmodel):
    """Test input backspace handling"""
    state.input_buffer = "hello"
    state.input_cursor_pos = 3

    viewmodel.handle_input_backspace()

    assert state.input_buffer == "helo"
    assert state.input_cursor_pos == 2


def test_handle_input_backspace_at_beginning(state, viewmodel):
    """Test input backspace at beginning of buffer"""
    state.input_buffer = "hello"
    state.input_cursor_pos = 0

    viewmodel.handle_input_backspace()

    assert state.input_buffer == "hello"  # No change
    assert state.input_cursor_pos == 0


def test_handle_input_delete(state, viewmodel):
    """Test input delete handling"""
    state.input_buffer = "hello"
    state.input_cursor_pos = 2

    viewmodel.handle_input_delete()

    assert state.input_buffer == "helo"
    assert state.input_cursor_pos == 2


def test_handle_input_cursor_left(state, viewmodel):
    """Test input cursor left movement"""
    state.input_cursor_pos = 3

    viewmodel.handle_input_cursor_left()

    assert state.input_cursor_pos == 2


def test_handle_input_cursor_left_at_beginning(state, viewmodel):
    """Test input cursor left at beginning"""
    state.input_cursor_pos = 0

    viewmodel.handle_input_cursor_left()

    assert state.input_cursor_pos == 0


def test_handle_input_cursor_right(state, viewmodel):
    """Test input cursor right movement"""
    state.input_buffer = "hello"
    state.input_cursor_pos = 2

    viewmodel.handle_input_cursor_right()

    assert state.input_cursor_pos == 3


def test_handle_input_cursor_right_at_end(state, viewmodel):
    """Test input cursor right at end"""
    state.input_buffer = "hello"
    state.input_cursor_pos = 5

    viewmodel.handle_input_cursor_right()

    assert state.input_cursor_pos == 5


def test_handle_input_character(state, viewmodel):
    """Test input character handling"""
    state.input_buffer = "helo"
    state.input_cursor_pos = 2

    viewmodel.handle_input_character("l")

    assert state.input_buffer == "hello"
    assert state.input_cursor_pos == 3
