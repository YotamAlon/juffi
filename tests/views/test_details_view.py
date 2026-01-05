"""Test the details view functionality"""

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
