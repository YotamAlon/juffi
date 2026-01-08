"""Test the app view"""

from tests.e2e.file_test_app import FileTestApp


def test_app_title_included_file_name(test_app: FileTestApp):
    """Test the app"""
    # Act
    text = test_app.read_text_until(test_app.log_file.name)

    # Assert
    assert text.startswith(f" Juffi - JSON Log Viewer - {test_app.log_file.name}")


def test_app_loads_log_entries(test_app: FileTestApp):
    """Test that the app loads and displays log entries"""
    # Act - wait for entries to be loaded and filtered (Row 1/5 indicates 5 entries)
    text = test_app.read_text_until("Row 1/5", timeout=3)

    # Assert - verify we can see log entries
    assert "Application started" in text
    assert "info" in text
    assert "timestamp" in text
    assert "Row 1/5" in text

    # Verify we see multiple entries (the test.log has 5 entries)
    # Check for content from different log lines
    assert "Database connection established" in text or "High memory usage" in text
