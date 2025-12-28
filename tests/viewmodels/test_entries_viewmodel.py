"""Tests for the EntriesModel viewmodel"""

import curses
from unittest.mock import Mock

import pytest

from juffi.models.juffi_model import JuffiState
from juffi.models.log_entry import LogEntry
from juffi.viewmodels.entries import EntriesModel


@pytest.fixture(name="test_state")
def juffi_state_fixture():
    """Create a JuffiState instance for testing"""
    return JuffiState()


@pytest.fixture(name="redraw_callback")
def mock_redraw_fixture():
    """Create a mock needs_redraw callback"""
    return Mock()


@pytest.fixture(name="test_model")
def entries_model_fixture(test_state, redraw_callback):
    """Create an EntriesModel instance for testing"""
    return EntriesModel(test_state, redraw_callback)


@pytest.fixture(name="navigation_setup")
def navigation_test_setup_fixture(test_state, redraw_callback):
    """Set up test data for navigation tests"""
    model = EntriesModel(test_state, redraw_callback)

    entries = [
        LogEntry("test1", 1),
        LogEntry("test2", 2),
        LogEntry("test3", 3),
        LogEntry("test4", 4),
        LogEntry("test5", 5),
    ]
    test_state.set_filtered_entries(entries)
    test_state.set_columns_from_names(["col1", "col2", "col3"])

    return {"state": test_state, "model": model}


@pytest.fixture(name="column_setup")
def column_test_setup_fixture(test_state, redraw_callback):
    """Set up test data for column operations tests"""
    model = EntriesModel(test_state, redraw_callback)

    test_state.set_columns_from_names(["col1", "col2", "col3"])
    test_state.set_column_width("col1", 10)
    test_state.set_column_width("col2", 15)
    test_state.set_column_width("col3", 20)

    return {"state": test_state, "model": model}


@pytest.fixture(name="goto_line_setup")
def goto_line_test_setup_fixture(test_state, redraw_callback):
    """Set up test data for goto line tests"""
    model = EntriesModel(test_state, redraw_callback)

    entries = [
        LogEntry("test1", 0),
        LogEntry("test2", 1),
        LogEntry("test3", 2),
        LogEntry("test4", 3),
        LogEntry("test5", 4),
    ]
    test_state.set_filtered_entries(entries)

    return {"state": test_state, "model": model}


def test_initialization_with_callbacks(test_state, redraw_callback):
    """Test that EntriesModel initializes correctly with callbacks"""
    # Act
    model = EntriesModel(test_state, redraw_callback)

    # Assert
    assert model.scroll_row == 0


def test_watcher_registration_fields(test_state, redraw_callback):
    """Test that all required fields are registered for watching"""
    # Act
    EntriesModel(test_state, redraw_callback)

    # Assert
    original_call_count = redraw_callback.call_count
    test_state.current_row = 1
    assert redraw_callback.call_count > original_call_count


def test_set_data_normal_case(test_state, redraw_callback):
    """Test set_data with normal data"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)
    entries = [
        LogEntry("test1", 1),
        LogEntry("test2", 2),
        LogEntry("test3", 3),
    ]
    test_state.set_filtered_entries(entries)
    test_state.current_row = 1

    # Act
    model.set_data()

    # Assert
    assert test_state.current_row >= 0


def test_set_data_sort_reverse_at_beginning(test_state, redraw_callback):
    """Test set_data when sort_reverse is True and current_row is 0"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)
    entries = [LogEntry("test1", 1), LogEntry("test2", 2)]
    test_state.set_filtered_entries(entries)
    test_state.sort_reverse = True
    test_state.current_row = 0

    # Act
    model.set_data()

    # Assert
    assert test_state.current_row == 0


def test_set_data_sort_reverse_new_lines_at_top(test_state, redraw_callback):
    """Test set_data when new lines are added and selected line is the top one"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)
    initial_entries = [LogEntry("test1", 1), LogEntry("test2", 2)]
    test_state.set_filtered_entries(initial_entries)
    test_state.sort_reverse = True
    test_state.current_row = 0
    model.set_data()
    new_entries = [
        LogEntry("test3", 3),
        LogEntry("test4", 4),
        LogEntry("test1", 1),
        LogEntry("test2", 2),
    ]
    test_state.set_filtered_entries(new_entries)

    # Act
    model.set_data()

    # Assert
    assert test_state.current_row == 0
    assert model.scroll_row == 0


def test_set_data_not_reversed_new_lines_at_bottom(test_state, redraw_callback):
    """Test set_data when new lines are added and selected line is the bottom one"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)
    initial_entries = [LogEntry("test1", 1), LogEntry("test2", 2)]
    test_state.set_filtered_entries(initial_entries)
    test_state.sort_reverse = False
    test_state.current_row = 1
    model.set_data()
    new_entries = [
        LogEntry("test1", 1),
        LogEntry("test2", 2),
        LogEntry("test3", 3),
        LogEntry("test4", 4),
    ]
    test_state.set_filtered_entries(new_entries)

    # Act
    model.set_data()

    # Assert
    assert test_state.current_row == 3
    assert model.scroll_row == 3


def test_set_data_not_reversed_scroll_follows_when_many_new_lines_added(
    test_state, redraw_callback
):
    """Test that scroll_row is adjusted when many new lines are added in normal sort"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)
    initial_entries = [LogEntry(f"test{i}", i) for i in range(1, 6)]
    test_state.set_filtered_entries(initial_entries)
    test_state.sort_reverse = False
    test_state.current_row = 4
    test_state.terminal_size = (100, 10)
    model.set_data()

    visible_rows = 8
    model.set_visible_rows(visible_rows)
    new_entries = [LogEntry(f"test{i}", i) for i in range(1, 21)]
    test_state.set_filtered_entries(new_entries)

    # Act
    model.set_data()

    # Assert
    assert test_state.current_row == 19
    assert model.scroll_row >= test_state.current_row - visible_rows + 1


def test_set_data_current_row_exceeds_entries(test_state, redraw_callback):
    """Test set_data when current_row exceeds available entries"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)
    entries = [LogEntry("test1", 1)]
    test_state.set_filtered_entries(entries)
    test_state.current_row = 5

    # Act
    model.set_data()

    # Assert
    assert test_state.current_row == 0


def test_set_data_empty_entries(test_state, redraw_callback):
    """Test set_data with empty entries"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)
    test_state.set_filtered_entries([])
    test_state.current_row = 1

    # Act
    model.set_data()

    # Assert
    assert test_state.current_row == 0


def test_handle_navigation_up_arrow(navigation_setup):
    """Test navigation with up arrow key"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 2
    nav_model.set_visible_rows(3)

    # Act
    result = nav_model.handle_navigation(curses.KEY_UP)

    # Assert
    assert result is True
    assert nav_state.current_row == 1


def test_handle_navigation_up_arrow_at_beginning(navigation_setup):
    """Test navigation with up arrow at beginning"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 0
    nav_model.set_visible_rows(3)

    # Act
    result = nav_model.handle_navigation(curses.KEY_UP)

    # Assert
    assert result is True
    assert nav_state.current_row == 0


def test_handle_navigation_down_arrow(navigation_setup):
    """Test navigation with down arrow key"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 1
    nav_model.set_visible_rows(3)

    # Act
    result = nav_model.handle_navigation(curses.KEY_DOWN)

    # Assert
    assert result is True
    assert nav_state.current_row == 2


def test_handle_navigation_down_arrow_at_end(navigation_setup):
    """Test navigation with down arrow at end"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 4
    nav_model.set_visible_rows(3)

    # Act
    result = nav_model.handle_navigation(curses.KEY_DOWN)

    # Assert
    assert result is True
    assert nav_state.current_row == 4


def test_handle_navigation_page_up(navigation_setup):
    """Test navigation with page up key"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 4
    nav_model.set_visible_rows(3)

    # Act
    result = nav_model.handle_navigation(curses.KEY_PPAGE)

    # Assert
    assert result is True
    assert nav_state.current_row == 1
    assert nav_model.scroll_row == 0


def test_handle_navigation_page_down(navigation_setup):
    """Test navigation with page down key"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 0
    nav_model.set_visible_rows(3)

    # Act
    result = nav_model.handle_navigation(curses.KEY_NPAGE)

    # Assert
    assert result is True
    assert nav_state.current_row == 3
    assert nav_model.scroll_row == 2


def test_handle_navigation_home(navigation_setup):
    """Test navigation with home key"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 3
    nav_model.set_visible_rows(3)

    # Act
    result = nav_model.handle_navigation(curses.KEY_HOME)

    # Assert
    assert result is True
    assert nav_state.current_row == 0


def test_handle_navigation_end(navigation_setup):
    """Test navigation with end key"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 1
    nav_model.set_visible_rows(3)

    # Act
    result = nav_model.handle_navigation(curses.KEY_END)

    # Assert
    assert result is True
    assert nav_state.current_row == 4


def test_handle_navigation_left_arrow(navigation_setup):
    """Test navigation with left arrow key"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_column = "col2"
    nav_model.set_visible_rows(3)
    nav_state.current_row = 0

    # Act
    result = nav_model.handle_navigation(curses.KEY_LEFT)

    # Assert
    assert result is True
    assert nav_state.current_column == "col1"


def test_handle_navigation_left_arrow_at_beginning(navigation_setup):
    """Test navigation with left arrow at first column"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_column = "col1"
    nav_model.set_visible_rows(3)
    nav_state.current_row = 0

    # Act
    result = nav_model.handle_navigation(curses.KEY_LEFT)

    # Assert
    assert result is True
    assert nav_state.current_column == "col1"


def test_handle_navigation_right_arrow(navigation_setup):
    """Test navigation with right arrow key"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_column = "col1"
    nav_model.set_visible_rows(3)
    nav_state.current_row = 0

    # Act
    result = nav_model.handle_navigation(curses.KEY_RIGHT)

    # Assert
    assert result is True
    assert nav_state.current_column == "col2"


def test_handle_navigation_right_arrow_at_end(navigation_setup):
    """Test navigation with right arrow at last column"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_column = "col3"
    nav_model.set_visible_rows(3)
    nav_state.current_row = len(nav_state.filtered_entries) - 1

    # Act
    result = nav_model.handle_navigation(curses.KEY_RIGHT)

    # Assert
    assert result is True
    assert nav_state.current_column == "col3"


def test_handle_navigation_unknown_key(navigation_setup):
    """Test navigation with unknown key"""
    # Arrange
    nav_model = navigation_setup["model"]
    nav_model.set_visible_rows(3)

    # Act
    result = nav_model.handle_navigation(ord("x"))

    # Assert
    assert result is False


def test_handle_navigation_empty_entries(test_state, redraw_callback):
    """Test navigation with empty entries"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)
    test_state.set_filtered_entries([])
    model.set_visible_rows(3)

    # Act
    result = model.handle_navigation(curses.KEY_UP)

    # Assert
    assert result is False


def test_handle_navigation_scroll_adjustment_up(navigation_setup):
    """Test that scroll adjusts when current row goes above visible area"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 3
    nav_model.set_visible_rows(3)

    # Act
    nav_model.handle_navigation(curses.KEY_UP)

    # Assert
    assert nav_state.current_row == 2
    assert nav_model.scroll_row >= 0


def test_handle_navigation_scroll_adjustment_down(navigation_setup):
    """Test that scroll adjusts when current row goes below visible area"""
    # Arrange
    nav_state = navigation_setup["state"]
    nav_model = navigation_setup["model"]
    nav_state.current_row = 1
    nav_model.set_visible_rows(2)

    # Act
    nav_model.handle_navigation(curses.KEY_DOWN)
    nav_model.handle_navigation(curses.KEY_DOWN)

    # Assert
    assert nav_state.current_row == 3
    assert nav_model.scroll_row >= 0


def test_move_column_right(column_setup):
    """Test moving column to the right"""
    # Arrange
    col_state = column_setup["state"]
    col_model = column_setup["model"]
    visible_cols = ["col1", "col2"]
    col_state.current_column = "col1"
    original_columns = list(col_state.columns.keys())

    # Act
    col_model.move_column(True, visible_cols)

    # Assert
    assert col_state.current_column == "col1"
    new_columns = list(col_state.columns.keys())
    assert new_columns != original_columns
    assert "col1" in new_columns
    assert original_columns.index("col1") != new_columns.index("col1")


def test_move_column_left(column_setup):
    """Test moving column to the left"""
    # Arrange
    col_state = column_setup["state"]
    col_model = column_setup["model"]
    visible_cols = ["col2", "col3"]
    col_state.current_column = "col2"
    original_columns = list(col_state.columns.keys())

    # Act
    col_model.move_column(False, visible_cols)

    # Assert
    assert col_state.current_column == "col2"
    new_columns = list(col_state.columns.keys())
    assert new_columns != original_columns
    assert "col2" in new_columns
    assert original_columns.index("col2") != new_columns.index("col2")


def test_move_column_right_at_end(column_setup):
    """Test moving column right when at the end"""
    # Arrange
    col_state = column_setup["state"]
    col_model = column_setup["model"]
    visible_cols = ["col3"]
    col_state.current_column = "col3"

    # Act
    col_model.move_column(True, visible_cols)

    # Assert
    assert col_state.current_column == "col3"


def test_move_column_left_at_beginning(column_setup):
    """Test moving column left when at the beginning"""
    # Arrange
    col_state = column_setup["state"]
    col_model = column_setup["model"]
    visible_cols = ["col1"]
    col_state.current_column = "col1"

    # Act
    col_model.move_column(False, visible_cols)

    # Assert
    assert col_state.current_column == "col1"


def test_move_column_empty_columns(test_state, redraw_callback):
    """Test moving column with empty columns"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)
    visible_cols = []

    # Act & Assert
    model.move_column(True, visible_cols)


def test_move_column_empty_visible_cols(column_setup):
    """Test moving column with empty visible columns"""
    # Arrange
    col_model = column_setup["model"]
    visible_cols = []

    # Act & Assert
    col_model.move_column(True, visible_cols)


def test_adjust_column_width_increase(column_setup):
    """Test increasing column width"""
    # Arrange
    col_state = column_setup["state"]
    col_model = column_setup["model"]
    visible_cols = ["col1"]
    original_width = col_state.columns["col1"].width

    # Act
    col_model.adjust_column_width(5, visible_cols)

    # Assert
    assert col_state.columns["col1"].width == original_width + 5


def test_adjust_column_width_decrease(column_setup):
    """Test decreasing column width"""
    # Arrange
    col_state = column_setup["state"]
    col_model = column_setup["model"]
    visible_cols = ["col1"]
    original_width = col_state.columns["col1"].width

    # Act
    col_model.adjust_column_width(-3, visible_cols)

    # Assert
    assert col_state.columns["col1"].width == original_width - 3


def test_adjust_column_width_minimum_limit(column_setup):
    """Test column width minimum limit"""
    # Arrange
    col_state = column_setup["state"]
    col_model = column_setup["model"]
    visible_cols = ["col1"]

    # Act
    col_model.adjust_column_width(-20, visible_cols)

    # Assert
    assert col_state.columns["col1"].width == 5


def test_adjust_column_width_maximum_limit(column_setup):
    """Test column width maximum limit"""
    # Arrange
    col_state = column_setup["state"]
    col_model = column_setup["model"]
    visible_cols = ["col1"]

    # Act
    col_model.adjust_column_width(200, visible_cols)

    # Assert
    assert col_state.columns["col1"].width == 100


def test_adjust_column_width_empty_visible_cols(column_setup):
    """Test adjusting column width with empty visible columns"""
    # Arrange
    col_model = column_setup["model"]
    visible_cols = []

    # Act & Assert
    col_model.adjust_column_width(5, visible_cols)


def test_goto_line_valid_row_number(goto_line_setup):
    """Test going to a valid row number"""
    # Arrange
    goto_state = goto_line_setup["state"]
    goto_model = goto_line_setup["model"]
    goto_model.set_visible_rows(3)
    goto_state.current_row = 4

    # Act
    goto_model.goto_line(1)

    # Assert
    assert goto_state.current_row == 1
    assert goto_model.scroll_row == 0


def test_goto_line_first_row(goto_line_setup):
    """Test going to the first row"""
    goto_state = goto_line_setup["state"]
    goto_model = goto_line_setup["model"]
    goto_model.set_visible_rows(3)

    goto_model.goto_line(0)

    assert goto_state.current_row == 0


def test_goto_line_last_row(goto_line_setup):
    """Test going to the last row"""
    # Arrange
    goto_state = goto_line_setup["state"]
    goto_model = goto_line_setup["model"]
    goto_model.set_visible_rows(3)

    # Act
    goto_model.goto_line(4)

    # Assert
    assert goto_state.current_row == 4
    assert goto_model.scroll_row == 3


def test_goto_line_beyond_available_entries(goto_line_setup):
    """Test going to a row number beyond available entries (should clamp to last)"""
    # Arrange
    goto_state = goto_line_setup["state"]
    goto_model = goto_line_setup["model"]
    goto_model.set_visible_rows(3)

    # Act
    goto_model.goto_line(100)

    # Assert
    assert goto_state.current_row == 4
    assert goto_model.scroll_row == 3


def test_goto_line_negative_row_number(goto_line_setup):
    """Test going to a negative row number"""
    goto_state = goto_line_setup["state"]
    goto_model = goto_line_setup["model"]
    goto_model.set_visible_rows(3)

    goto_model.goto_line(-5)

    assert goto_state.current_row == 0


def test_goto_line_scroll_centering(goto_line_setup):
    """Test that goto_line centers the target row"""
    # Arrange
    goto_state = goto_line_setup["state"]
    goto_model = goto_line_setup["model"]
    goto_model.set_visible_rows(4)

    # Act
    goto_model.goto_line(5)

    # Assert
    assert goto_state.current_row == 4
    assert goto_model.scroll_row == 2


def test_reset(test_state, redraw_callback):
    """Test reset method"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)

    test_state.current_row = 5
    test_state.current_column = "some_column"

    # Act
    model.reset()

    # Assert
    assert test_state.current_row == 0
    assert test_state.current_column == "#"
    assert model.scroll_row == 0


def test_scroll_row_property(test_state, redraw_callback):
    """Test that scroll_row property returns correct value"""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)

    # Act & Assert
    assert model.scroll_row == 0


def test_goto_line_with_filtered_entries(test_state, redraw_callback):
    """Test goto_line uses row numbers with filtered entries."""
    # Arrange
    model = EntriesModel(test_state, redraw_callback)

    entries = [
        LogEntry("line 10", 10),
        LogEntry("line 30", 30),
        LogEntry("line 50", 50),
    ]
    test_state.set_filtered_entries(entries)
    model.set_visible_rows(10)

    # Act
    model.goto_line(1)

    # Assert
    assert test_state.current_row == 1
