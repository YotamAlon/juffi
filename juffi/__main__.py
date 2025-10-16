#!/usr/bin/env python3
"""
JSON Log Viewer TUI - A terminal user interface for viewing and analyzing JSON log files
"""
import argparse
import curses
import logging
import os
import sys
from pathlib import Path

from juffi.input_controller import FileInputController
from juffi.views.app import App

LOG_FILE = Path(__file__).parent / "juffi.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s[%(process)d]: %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


def init_app(stdscr: curses.window) -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="JSON Log Viewer TUI - View and analyze JSON log files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s app.log
  %(prog)s -f app.log
  %(prog)s --follow app.log

Key Features:
  - Automatic column detection from JSON fields
  - Sortable columns (press 's' on any column)
  - Column reordering (use '<' and '>' keys)
  - Horizontal scrolling for wide tables
  - Filtering by any column (press 'f')
  - Search across all fields (press '/')
  - Real-time log following (press 'F' to toggle)
        """,
    )

    parser.add_argument("log_file", help="Path to the JSON log file to view")

    parser.add_argument(
        "-n",
        "--no-follow",
        action="store_true",
        help="Follow the log file for new entries (like tail -f)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.log_file):
        print(f"Error: Log file '{args.log_file}' not found", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(args.log_file):
        print(f"Error: '{args.log_file}' is not a file", file=sys.stderr)
        sys.exit(1)

    logger.info("Starting viewer")
    with open(args.log_file, "r", encoding="utf-8", errors="ignore") as file:
        input_controller = FileInputController(stdscr, file, args.log_file)
        viewer = App(stdscr, args.no_follow, input_controller)
        try:
            viewer.run()
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt")
        except BaseException as e:
            logger.exception("An error occurred")
            raise e
        finally:
            logger.info("Exiting viewer")


def main() -> None:
    """Main entry point"""
    curses.wrapper(init_app)  # type: ignore


if __name__ == "__main__":
    main()
