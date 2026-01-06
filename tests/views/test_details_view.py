"""Test the details view functionality"""

from datetime import datetime

from tests.infra.utils import DOWN_ARROW, LEFT_ARROW, RIGHT_ARROW
from tests.views.file_test_app import FileTestApp


def test_details_view_shows_entry_fields(test_app: FileTestApp):
    """Test that details view shows all fields of an entry"""
    # Act
    test_app.send_keys("d")

    # Assert
    screen = test_app.read_text_until("DETAILS")
    assert "Field 1/" in screen.text
    assert screen.is_selected("level:")
    assert "level:" in screen.text
    assert "message:" in screen.text
    assert "timestamp:" in screen.text


def test_details_view_navigate_fields_down(test_app: FileTestApp):
    """Test navigating down through fields in details view"""
    # Arrange
    test_app.send_keys("d")
    test_app.read_text_until("Details - Line")

    # Act
    test_app.send_keys(DOWN_ARROW)

    # Assert
    screen = test_app.read_text_until("Field 2/")
    assert screen.is_selected("message:")


def test_details_view_navigate_to_next_entry(test_app: FileTestApp):
    """Test navigating to next entry in details view"""
    # Arrange
    test_app.send_keys("d")
    initial_screen = test_app.read_text_until("Details - Line 5")
    assert "Details - Line 5" in initial_screen.text

    # Act
    test_app.send_keys(RIGHT_ARROW)

    # Assert
    screen = test_app.read_text_until("Details - Line 4")
    assert "Details - Line 4" in screen.text


def test_details_view_navigate_to_previous_entry(test_app: FileTestApp):
    """Test navigating to previous entry in details view"""
    # Arrange
    test_app.send_keys("d")
    test_app.read_text_until("Details - Line 5")
    test_app.send_keys(RIGHT_ARROW)
    test_app.read_text_until("Details - Line 4")

    # Act
    test_app.send_keys(LEFT_ARROW)

    # Assert
    screen = test_app.read_text_until("Details - Line 5")
    assert "Details - Line 5" in screen.text


def test_details_view_preserves_line_when_new_entries_arrive(test_app: FileTestApp):
    """Test that details view stays on the same line when new entries are added"""
    # Arrange
    test_app.send_keys("d")
    test_app.read_text_until("Row 1/")
    new_lines = [
        {
            "timestamp": datetime(2024, 1, 1, 10, 0, 5),
            "level": "info",
            "message": "New entry 1",
            "service": "web-server",
        },
        {
            "timestamp": datetime(2024, 1, 1, 10, 0, 6),
            "level": "info",
            "message": "New entry 2",
            "service": "web-server",
        },
    ]

    # Act
    test_app.append_to_log(new_lines)

    # Assert
    assert test_app.read_text_until("Row 3/")
