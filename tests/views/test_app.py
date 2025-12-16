"""Test the app view"""

from tests.views.utils import LOG_FILE, JuffiTestApp


def test_app_title_included_file_name(test_app: JuffiTestApp):
    """Test the app"""
    # Act
    text = test_app.read_text_until(LOG_FILE.name)

    # Assert
    assert text.startswith(f" Juffi - JSON Log Viewer - {LOG_FILE.name}")


def test_app_loads_log_entries(test_app: JuffiTestApp):
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
