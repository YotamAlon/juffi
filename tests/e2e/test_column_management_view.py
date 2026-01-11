"""Test the column management view"""

from tests.e2e.file_test_app import FileTestApp
from tests.infra.utils import DOWN_ARROW, LEFT_ARROW, RIGHT_ARROW


def test_column_management_can_be_opened_with_m(test_app: FileTestApp):
    """Test that column management can be opened with 'm' key"""
    # Act
    test_app.send_keys("m")

    # Assert
    text = test_app.read_text_until("Selected Columns")
    assert "Column Management" in text
    assert "Available Columns" in text
    assert "Selected Columns" in text


def test_column_management_move_column_to_available(test_app: FileTestApp):
    """Test moving a column from selected to available"""
    # Arrange
    test_app.read_text_until("Application started")
    test_app.send_keys("m")
    test_app.read_text_until("Selected Columns")
    test_app.send_keys(RIGHT_ARROW)
    test_app.send_keys(DOWN_ARROW * 4)
    test_app.send_keys("\n")

    # Act
    test_app.send_keys(LEFT_ARROW)
    test_app.send_keys("\t\n")

    # Assert
    test_app.send_keys("m")
    text = test_app.read_text_until("Reset")
    assert "service" in text
    assert "Available Columns" in text
    assert "Selected Columns" in text
