"""Test piped input functionality"""

from tests.piped.piped_test_app import PipedTestApp


def test_piped_input_loads_initial_data(piped_test_app: PipedTestApp):
    """Test that piped input loads initial data"""
    # Arrange
    json_lines = [
        '{"level": "info", "message": "First entry", "timestamp": "2023-01-01T10:00:00"}',
        '{"level": "error", "message": "Second entry", "timestamp": "2023-01-01T10:01:00"}',
        '{"level": "debug", "message": "Third entry", "timestamp": "2023-01-01T10:02:00"}',
    ]

    piped_test_app.pipe_data(json_lines)

    # Act
    text = piped_test_app.read_text_until("Row 1/3", timeout=3)

    # Assert
    assert "First entry" in text
    assert "info" in text
    assert "Row 1/3" in text


def test_piped_input_streams_data_incrementally(piped_test_app: PipedTestApp):
    """Test that piped input can stream data incrementally without EOF"""
    # Arrange
    initial_lines = [
        '{"level": "info", "message": "Initial batch 1"}',
        '{"level": "info", "message": "Initial batch 2"}',
    ]

    piped_test_app.pipe_data(initial_lines)
    piped_test_app.read_text_until("Row 1/2", timeout=3)

    additional_lines = [
        '{"level": "error", "message": "Second batch 1"}',
        '{"level": "debug", "message": "Second batch 2"}',
    ]

    # Act
    piped_test_app.pipe_data(additional_lines)

    # Assert
    text = piped_test_app.read_text_until("Row 1/4", timeout=3)
    assert "Second batch 1" in text
    assert "Row 1/4" in text


def test_piped_input_handles_empty_lines(piped_test_app: PipedTestApp):
    """Test that piped input handles empty lines correctly"""
    # Arrange
    lines_with_empty = [
        '{"level": "info", "message": "First"}',
        "",
        "",
        '{"level": "error", "message": "Second"}',
        "   ",
        '{"level": "debug", "message": "Third"}',
    ]

    # Act
    piped_test_app.pipe_data(lines_with_empty)

    # Assert
    text = piped_test_app.read_text_until("Row 1/3", timeout=3)
    assert "First" in text
    assert "Second" in text
    assert "Third" in text
    assert "Row 1/3" in text


def test_piped_input_handles_mixed_json_and_text(piped_test_app: PipedTestApp):
    """Test that piped input handles mixed JSON and plain text"""
    # Arrange
    mixed_lines = [
        '{"level": "info", "message": "JSON entry"}',
        "Plain text log entry",
        '{"level": "error", "count": 42}',
    ]

    # Act
    piped_test_app.pipe_data(mixed_lines)

    # Assert
    text = piped_test_app.read_text_until("Row 1/3", timeout=3)
    assert "JSON entry" in text
    assert "Plain text log entry" in text
    assert "Row 1/3" in text


def test_piped_input_multiple_incremental_updates(piped_test_app: PipedTestApp):
    """Test multiple incremental updates to piped input"""
    for i in range(1, 4):
        # Arrange
        lines = [
            f'{{"level": "info", "message": "Batch {i} entry {j}"}}'
            for j in range(1, 3)
        ]
        expected_count = i * 2

        # Act
        piped_test_app.pipe_data(lines)

        # Assert
        text = piped_test_app.read_text_until(f"Row 1/{expected_count}", timeout=3)
        assert f"Batch {i} entry 1" in text
        assert f"Row 1/{expected_count}" in text


def test_piped_input_with_unicode(piped_test_app: PipedTestApp):
    """Test that piped input handles unicode characters"""
    # Arrange
    unicode_lines = [
        '{"level": "info", "message": "Hello 世界", "emoji": "🚀"}',
        '{"user": "José", "city": "São Paulo"}',
    ]

    # Act
    piped_test_app.pipe_data(unicode_lines)

    # Assert
    text = piped_test_app.read_text_until("Row 1/2", timeout=3)
    assert "Hello 世界" in text or "🚀" in text or "José" in text
    assert "Row 1/2" in text


def test_piped_input_shows_stdin_as_source(piped_test_app: PipedTestApp):
    """Test that piped input shows <stdin> as the source name"""
    # Arrange
    lines = ['{"level": "info", "message": "Test"}']

    # Act
    piped_test_app.pipe_data(lines)

    # Assert
    text = piped_test_app.read_text_until("<stdin>", timeout=3)
    assert "<stdin>" in text
