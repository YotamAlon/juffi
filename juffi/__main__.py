#!/usr/bin/env python3
"""
JSON Log Viewer TUI - A terminal user interface for viewing and analyzing JSON log files
"""
import argparse
import curses
import os
import sys

from juffi.input_controller import FileInputController
from juffi.views.app import App


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
    with open(args.log_file, "r", encoding="utf-8", errors="ignore") as file:
        input_controller = FileInputController(stdscr, file, args.log_file)
        viewer = App(stdscr, args.no_follow, input_controller)
        viewer.run()


def main() -> None:
    """Main entry point"""
    curses.wrapper(init_app)  # type: ignore


if __name__ == "__main__":
    main()
