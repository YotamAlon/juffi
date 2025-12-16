"""Test the browse view functionality"""

from tests.views.utils import DOWN_ARROW, RIGHT_ARROW, JuffiTestApp


def test_browse_view_shows_entries_after_reset(test_app: JuffiTestApp):
    """Test that the browse view shows entries after reset"""
    # After reset, entries should be loaded and displayed
    # Wait for entries to appear
    text = test_app.read_text_until("Row 1/5", timeout=3)

    # Verify we can see all 5 entries
    assert "Row 1/5" in text
    assert "Application started" in text or "Request processed successfully" in text


def test_filter_column_shows_only_matching_rows(test_app: JuffiTestApp):
    """Test that applying a filter to a column updates the filter count"""
    # Arrange - wait for entries to appear after reset
    text = test_app.read_text_until("Application started", timeout=3)

    # Verify initial state has no filters
    assert "Filters:" not in text or "Filters: 0" in text

    # Navigate to level column
    # Default columns are ordered: # -> timestamp -> level -> message
    # Send ">" twice to move viewport to show level as the leftmost column
    test_app.send_keys(RIGHT_ARROW)
    test_app.send_keys(RIGHT_ARROW)

    # Act - apply filter on level column
    test_app.send_keys("f")

    # Wait for filter input mode to appear
    text = test_app.read_text_until("Filter", timeout=3)
    assert "Filter" in text

    # Type filter value and submit
    test_app.send_keys("info\n")

    # Assert - verify filter was applied by checking filter count
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
    # Arrange - wait for entries to appear after reset
    text = test_app.read_text_until("Application started", timeout=3)

    # Navigate to level column and apply filter for "info"
    test_app.send_keys(RIGHT_ARROW)
    test_app.send_keys(RIGHT_ARROW)
    test_app.send_keys("f")
    test_app.send_keys("info\n")

    # Act - scroll down to the second row
    test_app.send_keys(DOWN_ARROW)

    # Assert - verify we're now on row 2
    text = test_app.read_text_until("Row 2/2", timeout=3)
    assert "Row 2/2" in text

    # Verify we see the second info entry
    assert "Request processed successfully" in text
