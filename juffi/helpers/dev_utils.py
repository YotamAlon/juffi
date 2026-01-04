"""Environment detection utilities"""

import contextlib
import logging
import pathlib
import time
from typing import Iterator


def get_project_root() -> pathlib.Path:
    """Get the project root directory."""
    return pathlib.Path(__file__).parent.parent.parent


def is_dev() -> bool:
    """
    Check if running in development mode (from source) vs installed package.
    Development mode is detected when pyproject.toml exists in the parent directory of the package
    """
    project_root = get_project_root()
    has_pyproject = (project_root / "pyproject.toml").exists()
    return has_pyproject


def setup_logging():
    """Setup logging to file"""

    log_file = get_project_root() / "juffi.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s[%(process)d]: %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        ],
    )


@contextlib.contextmanager
def measure(logger: logging.Logger, name: str) -> Iterator[None]:
    """Measure execution time of a block of code"""
    start = time.time()
    yield
    logger.info("%s took %f seconds", name, time.time() - start)
