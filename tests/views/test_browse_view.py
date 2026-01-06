"""Test the browse view functionality"""

import itertools
import re
from datetime import datetime, timedelta

from tests.infra.screen_data import ScreenData
from tests.infra.utils import DOWN_ARROW, LEFT_ARROW, RIGHT_ARROW
from tests.views.file_test_app import FileTestApp


def _generate_json_log_lines(num_new_entries: int) -> tuple[dict, list[dict]]:
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    levels = itertools.cycle(["info", "error", "debug"])
    logs: list[dict[str, str | int | datetime]] = [
        {
            "timestamp": base_time + timedelta(seconds=i),
            "level": (level := next(levels)),
            "message": f"New {level} entry {i}",
        }
        for i in range(num_new_entries)
    ]
    return logs[-1], logs


def test_browse_view_shows_entries_after_reset(test_app: FileTestApp):
    """Test that the browse view shows entries after reset"""
    # Act
    text = test_app.read_text_until("Row 1/5", timeout=3)

    # Assert
    assert "Row 1/5" in text
    assert "Application started" in text or "Request processed successfully" in text


def test_filter_column_shows_only_matching_rows(test_app: FileTestApp):
    """Test that applying a filter to a column updates the filter count"""
    # Arrange
    # Navigate to level column
    test_app.send_keys(RIGHT_ARROW * 2)

    # Act
    test_app.send_keys("f")
    test_app.send_keys("info\n")

    # Assert
    text = test_app.read_text_until("Filters: 1", timeout=3)
    assert "Filters: 1" in text

    # Verify we see only info entries (2 out of 5 total)
    assert "Row 1/2" in text or "Row 2/2" in text

    # Verify info entries are visible
    assert "Application started" in text or "Request processed successfully" in text

    # Verify non-info entries are not visible
    assert "Database connection established" not in text
    assert "High memory usage" not in text
    assert "Failed to process request" not in text


def test_filter_and_scroll_down(test_app: FileTestApp):
    """Test that filtering and then scrolling down shows the second filtered row"""
    # Arrange
    test_app.send_keys(RIGHT_ARROW)
    test_app.send_keys(RIGHT_ARROW)
    test_app.send_keys("f")
    test_app.send_keys("info\n")

    # Act
    test_app.send_keys(DOWN_ARROW)

    # Assert
    text = test_app.read_text_until("Row 2/2", timeout=3)
    assert "Row 2/2" in text
    assert "Request processed successfully" in text


def test_reverse_sort_keeps_first_row_selected_when_lines_added(
    test_app: FileTestApp,
):
    """Test that reverse sort keeps first row selected when new lines are added"""
    # Arrange
    last_log, new_lines = _generate_json_log_lines(test_app.entries_height + 10)

    # Act
    test_app.append_to_log(new_lines)

    # Assert
    text = test_app.read_text_until(last_log["message"], timeout=3)
    assert last_log["message"] in text


def test_normal_sort_moves_to_last_row_when_lines_added(test_app: FileTestApp):
    """Test that normal sort moves to last row when new lines are added at bottom"""
    # Arrange
    test_app.send_keys("s")
    test_app.send_keys(DOWN_ARROW * 4)
    test_app.read_text_until("Row 5/5", timeout=3)

    last_log, new_lines = _generate_json_log_lines(test_app.entries_height + 10)

    # Act
    test_app.append_to_log(new_lines)

    # Assert
    text = test_app.read_text_until(last_log["message"], timeout=3)
    assert last_log["message"] in text


def test_follow_with_filter_reverse_sort_shows_matching_entries(
    test_app: FileTestApp,
):
    """Test that follow mode with filter in reverse sort shows only matching new entries"""
    # Arrange
    last_log, new_lines = _generate_json_log_lines((test_app.entries_height + 10) * 3)

    test_app.send_keys(RIGHT_ARROW * 2)
    test_app.send_keys("f")
    test_app.send_keys(f"{last_log['level']}\n")
    test_app.send_keys(LEFT_ARROW * 2)
    test_app.read_text_until("Filters: 1", timeout=3)

    # Act
    test_app.append_to_log(new_lines)

    # Assert
    text = test_app.read_text_until(last_log["message"], timeout=3)
    assert last_log["message"] in text


def test_follow_with_filter_normal_sort_shows_matching_entries(
    test_app: FileTestApp,
):
    """Test that follow mode with filter in normal sort shows only matching new entries"""
    # Arrange
    last_log, new_lines = _generate_json_log_lines((test_app.entries_height + 10) * 3)

    test_app.send_keys("s")
    test_app.send_keys(RIGHT_ARROW * 2)
    test_app.send_keys("f")
    test_app.send_keys(f"{last_log['level']}\n")
    test_app.read_text_until("High memory usage", timeout=3)
    test_app.send_keys(DOWN_ARROW * 4)

    # Act
    test_app.append_to_log(new_lines)

    # Assert
    text = test_app.read_text_until(last_log["message"], timeout=3)
    assert last_log["message"] in text


def test_goto_navigates_to_row(test_app: FileTestApp):
    """Test that goto command navigates to the specified row"""
    test_app.read_text_until("Row 1/5", timeout=3)

    test_app.send_keys("g")
    test_app.send_keys("3\n")

    text = test_app.read_text_until("Row 3/5", timeout=3)
    assert "Row 3/5" in text


def _get_selected_level(screen: ScreenData) -> str:
    level_matches = list(re.finditer(r"\b(info|error|debug)\b", screen.text))
    assert len(level_matches) > 0, f"Could not find any level values in: {screen.text}"

    for match in level_matches:
        if screen.is_selected(match.group(1)):
            return match.group(1)

    raise AssertionError("Could not find a selected level")


def _apply_level_filter(test_app: FileTestApp, level: str) -> None:
    test_app.send_keys(RIGHT_ARROW * 2)
    test_app.send_keys("f")
    test_app.send_keys(f"{level}\n")
    test_app.send_keys(LEFT_ARROW * 2)


def _setup_test_with_selected_row(test_app: FileTestApp, row_number: int) -> str:
    _, new_lines = _generate_json_log_lines(test_app.entries_height + 10)
    test_app.append_to_log(new_lines)
    test_app.read_text_until(f"Row 1/{5 + test_app.entries_height + 10}")

    test_app.send_keys("g")
    test_app.send_keys(f"{row_number}\n")
    screen = test_app.read_text_until(f"Row {row_number}/")

    return _get_selected_level(screen)


def test_filter_preserves_line_number_when_applying_filter(test_app: FileTestApp):
    """Test that applying a filter preserves the current line number"""
    # Arrange
    selected_level = _setup_test_with_selected_row(test_app, 10)

    # Act
    _apply_level_filter(test_app, selected_level)
    screen = test_app.read_text_until("Filters: 1")

    # Assert
    assert screen.is_selected(selected_level)


def test_filter_preserves_line_number_when_clearing_filter(test_app: FileTestApp):
    """Test that clearing a filter preserves the current line number"""
    # Arrange
    selected_level = _setup_test_with_selected_row(test_app, 10)
    _apply_level_filter(test_app, selected_level)
    test_app.read_text_until("Filters: 1")

    # Act
    test_app.send_keys("c")
    screen = test_app.read_text_until("/93")

    # Assert
    assert screen.is_selected(selected_level)


def _get_different_level(level: str) -> str:
    if level == "info":
        return "error"
    if level == "error":
        return "debug"
    return "info"


def test_filter_moves_to_closest_line_when_current_filtered_out(test_app: FileTestApp):
    """Test that applying a filter moves to the closest line when the current one is filtered out"""
    # Arrange
    selected_level = _setup_test_with_selected_row(test_app, 10)
    filter_level = _get_different_level(selected_level)

    # Act
    _apply_level_filter(test_app, filter_level)
    screen = test_app.read_text_until("Filters: 1")

    # Assert
    assert not screen.is_selected(selected_level)
    assert screen.is_selected(filter_level)


def test_filter_restores_original_line_when_clearing_after_current_filtered_out(
    test_app: FileTestApp,
):
    """
    Test that clearing a filter restores the original
    line number when the current one was filtered out
    """
    # Arrange
    selected_level = _setup_test_with_selected_row(test_app, 10)
    filter_level = _get_different_level(selected_level)
    _apply_level_filter(test_app, filter_level)
    test_app.read_text_until("Filters: 1")

    # Act
    test_app.send_keys("c")
    screen = test_app.read_text_until("/93")

    # Assert
    assert screen.is_selected(selected_level)
