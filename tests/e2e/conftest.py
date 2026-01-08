"""Shared test infrastructure for view tests"""

import pathlib
import shutil
import tempfile
from typing import Iterator

import pytest

from juffi.helpers.curses_utils import Size
from tests.e2e.file_test_app import LOG_FILE, FileTestApp
from tests.infra.utils import juffi_process


@pytest.fixture(scope="session", name="temp_log_file")
def temp_log_file_fixture() -> Iterator[pathlib.Path]:
    """Create a temporary copy of the test log file"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
        temp_path = pathlib.Path(tmp.name)
        shutil.copy(LOG_FILE, temp_path)
        yield temp_path


@pytest.fixture(scope="session", name="test_app")
def test_app_fixture(temp_log_file: pathlib.Path) -> Iterator[FileTestApp]:
    """Run the app and capture its output"""
    terminal_size = Size(80, 80)
    with juffi_process(temp_log_file, terminal_size) as fd:
        juffi_test_app = FileTestApp(fd, temp_log_file, terminal_size)
        juffi_test_app.read_text_until("Press 'h' for help", timeout=3)
        yield juffi_test_app


@pytest.fixture(autouse=True)
def _reset_test_app(test_app: FileTestApp, temp_log_file: pathlib.Path) -> None:
    """Reset the test app to its initial state"""
    temp_log_file.write_text(LOG_FILE.read_text())
    test_app.reset()
    test_app.read_text_until("Press 'h' for help", timeout=3)
