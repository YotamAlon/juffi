"""Test the browse view functionality with plain text log files"""

import os
import pathlib
import pty
import shutil
import subprocess
import tempfile
from typing import Iterator

import pytest

from juffi.helpers.curses_utils import Size
from tests.infra.utils import set_terminal_size
from tests.views.file_test_app import FileTestApp

CURRENT_DIR = pathlib.Path(__file__).parent
PLAIN_TEXT_LOG_FILE = CURRENT_DIR / "test_plain.log"


@pytest.fixture(scope="module", name="temp_plain_text_log_file")
def temp_plain_text_log_file_fixture() -> Iterator[pathlib.Path]:
    """Create a temporary copy of the plain text test log file"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
        temp_path = pathlib.Path(tmp.name)
        shutil.copy(PLAIN_TEXT_LOG_FILE, temp_path)
        yield temp_path


@pytest.fixture(scope="module", name="plain_text_test_app")
def plain_text_test_app_fixture(
    temp_plain_text_log_file: pathlib.Path,
) -> Iterator[FileTestApp]:
    """Run the app with plain text log file and capture its output"""
    master, slave = pty.openpty()
    terminal_size = Size(80, 80)
    set_terminal_size(slave, terminal_size)
    with subprocess.Popen(
        ["python", "-m", "juffi", str(temp_plain_text_log_file)],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        env=os.environ.copy() | {"TERM": "linux"},
    ) as process:
        os.close(slave)
        juffi_test_app = FileTestApp(master, temp_plain_text_log_file, terminal_size)
        juffi_test_app.read_text_until("Press 'h' for help", timeout=3)
        yield juffi_test_app
        os.close(master)
        process.terminate()


@pytest.fixture(autouse=True)
def _reset_plain_text_test_app(
    plain_text_test_app: FileTestApp, temp_plain_text_log_file: pathlib.Path
) -> None:
    """Reset the plain text test app to its initial state"""
    temp_plain_text_log_file.write_text(PLAIN_TEXT_LOG_FILE.read_text())
    plain_text_test_app.reset()
    plain_text_test_app.read_text_until("Press 'h' for help", timeout=3)


def test_plain_text_file_shows_unreversed_sort_order(
    plain_text_test_app: FileTestApp,
):
    """Test that plain text files are displayed in unreversed (chronological) order"""
    # Act
    text = plain_text_test_app.read_text_until("Row 5/5")

    # Assert
    assert "Request processed successfully" in text


def test_plain_text_file_new_lines_added_at_bottom(
    plain_text_test_app: FileTestApp,
):
    """Test that new lines are added at the bottom for plain text files"""
    # Arrange
    new_lines = [
        "2024-01-01 10:00:05 INFO New entry 1",
        "2024-01-01 10:00:06 DEBUG New entry 2",
    ]

    # Act
    plain_text_test_app.append_to_log(new_lines)

    # Assert
    text = plain_text_test_app.read_text_until("Row 7/7")
    assert "New entry 2" in text
