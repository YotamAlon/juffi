"""Test the app view"""

from tests.views.utils import LOG_FILE, JuffiTestApp


def test_app_title_included_file_name(test_app: JuffiTestApp):
    """Test the app"""
    # Act
    text = test_app.read_text_until(LOG_FILE.name)

    # Assert
    assert text.startswith(f" Juffi - JSON Log Viewer - {LOG_FILE.name}")
