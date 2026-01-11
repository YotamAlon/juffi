"""Test the help view"""

from tests.e2e.file_test_app import FileTestApp


def test_help_screen_can_be_opened_with_h(test_app: FileTestApp):
    """Test that help screen can be opened with 'h' key"""
    # Act
    test_app.send_keys("h")

    # Assert
    text = test_app.read_text_until("Press any key to continue")
    assert "JSON LOG VIEWER - HELP" in text
    assert "Press any key to continue" in text


def test_help_screen_can_be_opened_with_question_mark(test_app: FileTestApp):
    """Test that help screen can be opened with '?' key"""
    # Act
    test_app.send_keys("?")

    # Assert
    text = test_app.read_text_until("Press any key to continue")
    assert "JSON LOG VIEWER - HELP" in text
    assert "Press any key to continue" in text
