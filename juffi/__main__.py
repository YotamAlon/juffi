#!/usr/bin/env python3
"""
JSON Log Viewer TUI - A terminal user interface for viewing and analyzing JSON log files
"""
import argparse
import curses
import logging
import os
import sys
from typing import Callable

from juffi.helpers.dev_utils import get_project_root, is_dev, setup_logging
from juffi.input_controller import (
    InputController,
    create_input_controller,
)
from juffi.output_controller import CursesOutputController
from juffi.views.app import App, AppExit

if is_dev():
    setup_logging()

logger = logging.getLogger(__name__)
logger.info("Project root: %s", get_project_root())


def _init_app(
    stdscr: curses.window,
    partial_input_controller: Callable[[curses.window], InputController],
    args: argparse.Namespace,
) -> None:
    output_controller = CursesOutputController(stdscr)
    wrapped_stdscr = output_controller.create_main_window()
    input_controller = partial_input_controller(stdscr)
    logger.info("Starting viewer for %s", input_controller.name)
    viewer = App(wrapped_stdscr, args.no_follow, input_controller, output_controller)
    try:
        viewer.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt")
    except AppExit:
        pass
    except BaseException as e:
        logger.exception("An error occurred")
        raise e
    finally:
        logger.info("Exiting viewer")


def main() -> None:
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

    parser.add_argument("log_file", nargs="?", help="Path to the JSON log file to view")

    parser.add_argument(
        "-n",
        "--no-follow",
        action="store_true",
        help="Follow the log file for new entries (like tail -f)",
    )

    args = parser.parse_args()

    if sys.stdin.isatty():
        if args.log_file is None:
            parser.error("No log file specified")

        if not os.path.exists(args.log_file):
            parser.error(f"File '{args.log_file}' not found")

        if not os.path.isfile(args.log_file):
            parser.error(f"'{args.log_file}' is not a file")

    with create_input_controller(args.log_file) as partial_input_controller:
        curses.wrapper(_init_app, partial_input_controller, args)


if __name__ == "__main__":
    main()
