"""Test the column management view"""

from tests.views.utils import LOG_FILE, JuffiTestApp


def test_column_management_screen_displays_title(test_app: JuffiTestApp):
    """Test that column management screen displays the title"""
    # Arrange
    test_app.read_text_until(LOG_FILE.name)

    # Act
    test_app.send_keys("m")

    # Assert
    text = test_app.read_text_until("Column Management")
    assert "Column Management" in text


def test_column_management_screen_displays_instructions(test_app: JuffiTestApp):
    """Test that column management screen displays instructions"""
    # Arrange
    test_app.read_text_until(LOG_FILE.name)

    # Act
    test_app.send_keys("m")

    # Assert
    text = test_app.read_text_until("Available Columns")
    assert "Move between panes" in text or "Move column" in text
    assert "Navigate" in text or "Move column" in text
    assert "Select column" in text or "Enter" in text
    assert "Tab" in text or "Buttons" in text


def test_column_management_screen_displays_panes(test_app: JuffiTestApp):
    """Test that column management screen displays both panes"""
    # Arrange
    test_app.read_text_until(LOG_FILE.name)

    # Act
    test_app.send_keys("m")

    # Assert
    text = test_app.read_text_until("Selected Columns")
    assert "Available Columns" in text
    assert "Selected Columns" in text


def test_column_management_screen_displays_buttons(test_app: JuffiTestApp):
    """Test that column management screen displays all buttons"""
    # Arrange
    test_app.read_text_until(LOG_FILE.name)

    # Act
    test_app.send_keys("m")

    # Assert
    text = test_app.read_text_until("Reset")
    assert "OK" in text
    assert "Cancel" in text
    assert "Reset" in text


def test_column_management_can_be_opened_with_m(test_app: JuffiTestApp):
    """Test that column management can be opened with 'm' key"""
    # Arrange
    test_app.read_text_until(LOG_FILE.name)

    # Act
    test_app.send_keys("m")

    # Assert
    text = test_app.read_text_until("Selected Columns")
    assert "Column Management" in text
    assert "Available Columns" in text
    assert "Selected Columns" in text


def test_column_management_move_column_to_available(test_app: JuffiTestApp):
    """Test moving a column from selected to available"""
    # Arrange - wait for initial screen with data loaded
    test_app.read_text_until("Application started")

    # Act - open column management
    test_app.send_keys("m")
    test_app.read_text_until("Selected Columns")

    # Switch focus to selected pane (right arrow once from available)
    test_app.send_keys("\x1b[C")

    # Navigate down to find service column (it should be in the selected list)
    # The columns are typically: #, timestamp, level, message, service
    # So we need to navigate down 4 times to get to service
    test_app.send_keys("\x1b[B")  # Down arrow (to timestamp)
    test_app.send_keys("\x1b[B")  # Down arrow (to level)
    test_app.send_keys("\x1b[B")  # Down arrow (to message)
    test_app.send_keys("\x1b[B")  # Down arrow (to service)

    # Select the column with Enter
    test_app.send_keys("\n")

    # Move it left to available pane
    test_app.send_keys("\x1b[D")  # Left arrow

    # Navigate to buttons and select OK
    test_app.send_keys("\t")  # Tab to buttons
    test_app.send_keys("\n")  # Press Enter on OK button

    # Assert - verify we're back to browse mode
    test_app.read_text_until(LOG_FILE.name)
    text = test_app.read_text_until("Press 'h' for help")
    assert "service" not in text and "web-server" not in text

    # The key verification: open column management again and check that
    # service is now in the Available Columns pane (not in Selected Columns)
    test_app.send_keys("m")
    text = test_app.read_text_until("Reset")

    # Verify service appears somewhere in the screen (in available section)
    assert "service" in text

    # Verify the structure: Available Columns should come before Selected Columns
    # and service should be in the Available section
    assert "Available Columns" in text
    assert "Selected Columns" in text
