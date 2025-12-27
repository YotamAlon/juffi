"""Test the browse view functionality"""

import itertools
import json
from datetime import datetime, timedelta

from tests.views.utils import DOWN_ARROW, LEFT_ARROW, RIGHT_ARROW, JuffiTestApp


def create_json_log_line(data: dict[str, str | int | datetime]) -> str:
    """Create a JSON log line from a dictionary

    Converts datetime objects to ISO format strings with 'Z' suffix.
    """
    converted_data: dict[str, str | int] = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            converted_data[key] = value.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            converted_data[key] = value
    return json.dumps(converted_data)


def _generate_json_log_lines(num_new_entries: int) -> tuple[dict, list[str]]:
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
    new_lines = [create_json_log_line(log) for log in logs]
    return logs[-1], new_lines


def test_browse_view_shows_entries_after_reset(test_app: JuffiTestApp):
    """Test that the browse view shows entries after reset"""
    # Act
    text = test_app.read_text_until("Row 1/5", timeout=3)

    # Assert
    assert "Row 1/5" in text
    assert "Application started" in text or "Request processed successfully" in text


def test_filter_column_shows_only_matching_rows(test_app: JuffiTestApp):
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


def test_filter_and_scroll_down(test_app: JuffiTestApp):
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
    test_app: JuffiTestApp,
):
    """Test that reverse sort keeps first row selected when new lines are added"""
    # Arrange
    last_log, new_lines = _generate_json_log_lines(test_app.entries_height + 10)

    # Act
    test_app.append_to_log(new_lines)

    # Assert
    text = test_app.read_text_until(last_log["message"], timeout=3)
    assert last_log["message"] in text


def test_normal_sort_moves_to_last_row_when_lines_added(test_app: JuffiTestApp):
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
    test_app: JuffiTestApp,
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
    test_app: JuffiTestApp,
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
