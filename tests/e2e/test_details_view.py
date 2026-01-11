"""Test the details view functionality"""

from datetime import datetime

from tests.e2e.file_test_app import FileTestApp


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
