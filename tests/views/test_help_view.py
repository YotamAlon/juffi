"""Test the help view"""

from tests.views.file_test_app import FileTestApp


def test_help_screen_displays_title(test_app: FileTestApp):
    """Test that help screen displays the title"""
    # Act
    test_app.send_keys("h")

    # Assert
    text = test_app.read_text_until("Press any key to continue")
    assert "JSON LOG VIEWER - HELP" in text


def test_help_screen_displays_all_sections(test_app: FileTestApp):
    """Test that help screen displays all sections"""
    # Act
    test_app.send_keys("h")

    # Assert
    text = test_app.read_text_until("Press any key to continue")
    assert "JSON LOG VIEWER - HELP" in text
    assert "Navigation:" in text
    assert "Move up" in text
    assert "Move down" in text
    assert "Column Operations:" in text
    assert "Sort by current column" in text
    assert "Filtering & Search:" in text
    assert "Search all fields" in text
    assert "View Options:" in text
    assert "Toggle details view" in text
    assert "File Operations:" in text
    assert "Toggle follow mode" in text
    assert "Other:" in text
    assert "Toggle this help" in text
    assert "Press any key to continue" in text


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
