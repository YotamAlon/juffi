"""Main application view - handles UI rendering and input delegation"""

import curses
import logging

from juffi.helpers.curses_utils import ESC, get_curses_yx
from juffi.input_controller import InputController
from juffi.models.juffi_model import JuffiState, ViewMode
from juffi.viewmodels.app import AppModel
from juffi.views.browse import BrowseMode
from juffi.views.column_management import ColumnManagementMode
from juffi.views.details import DetailsMode
from juffi.views.entries import EntriesWindow
from juffi.views.help import HelpMode

COLORS = {
    "DEFAULT": (curses.COLOR_WHITE, -1),
    "INFO": (curses.COLOR_GREEN, -1),
    "WARNING": (curses.COLOR_YELLOW, -1),
    "ERROR": (curses.COLOR_RED, -1),
    "DEBUG": (curses.COLOR_BLUE, -1),
    "HEADER": (curses.COLOR_CYAN, -1),
    "SELECTED": (curses.COLOR_MAGENTA, -1),
}

logger = logging.getLogger(__name__)


class App:  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """Main application class"""

    HEADER_HEIGHT = 2
    FOOTER_HEIGHT = 2

    def __init__(
        self,
        stdscr: curses.window,
        no_follow: bool,
        input_controller: InputController,
    ) -> None:
        self._stdscr = stdscr
        self._input_controller = input_controller
        self._needs_header_redraw = True
        self._needs_footer_redraw = True
        self._needs_resize = True
        self._state = JuffiState()
        self._model = AppModel(
            self._state,
            self._input_controller,
            header_update=self._update_needs_header_redraw,
            footer_update=self._update_needs_footer_redraw,
            size_update=self._update_needs_resize,
        )

        curses.start_color()
        curses.use_default_colors()

        self._colors: dict[str, int] = {}
        for i, (name, (fg, bg)) in enumerate(COLORS.items(), start=1):
            curses.init_pair(i, fg, bg)
            self._colors[name] = curses.color_pair(i)

        width = get_curses_yx()[1]

        self._header_win: curses.window = stdscr.derwin(  # type: ignore
            self.HEADER_HEIGHT, width, 0, 0
        )

        self._entries_win: curses.window = stdscr.derwin(  # type: ignore
            self._entries_height, width, self.HEADER_HEIGHT, 0
        )

        self._footer_win: curses.window = stdscr.derwin(  # type: ignore
            self.FOOTER_HEIGHT, width, self._footer_start, 0
        )

        self._entries_window = EntriesWindow(
            self._state, self._colors, self._entries_win
        )

        self._browse_mode = BrowseMode(
            self._state,
            no_follow=no_follow,
            entries_window=self._entries_window,
            colors=self._colors,
            on_apply_filters=self._apply_filters,
            on_load_entries=self._load_entries,
            on_reset=self._reset,
        )
        self._help_mode = HelpMode(
            colors=self._colors,
        )
        self._column_management_mode = ColumnManagementMode(
            self._state,
            self._stdscr,
            colors=self._colors,
        )
        self._details_mode = DetailsMode(
            self._state,
            entries_window=self._entries_window,
            colors=self._colors,
            entries_win=self._entries_win,
        )

    def _update_needs_header_redraw(self) -> None:
        self._needs_header_redraw = True

    def _update_needs_footer_redraw(self) -> None:
        self._needs_footer_redraw = True

    def _update_needs_resize(self) -> None:
        self._needs_resize = True

    def _apply_filters(self) -> None:
        self._model.apply_filters()
        self._entries_window.set_data()

    def _load_entries(self) -> None:
        self._model.load_entries()
        self._apply_filters()
        self._entries_window.set_data()

    def _reset(self) -> None:
        self._model.reset()
        self._entries_window.reset()
        self._state.current_mode = ViewMode.BROWSE
        self._apply_filters()

    def _resize_windows(self) -> None:
        """Resize all windows to fit the new terminal size"""

        width = get_curses_yx()[1]
        self._header_win.resize(self.HEADER_HEIGHT, width)
        self._header_win.mvderwin(0, 0)

        self._entries_win.resize(self._entries_height, width)
        self._entries_win.mvderwin(self.HEADER_HEIGHT, 0)

        self._footer_win.mvderwin(self._footer_start, 0)
        self._footer_win.resize(self.FOOTER_HEIGHT, width)
        self._entries_window.resize()
        self._details_mode.resize()

    @property
    def _footer_start(self):
        return get_curses_yx()[0] - self.FOOTER_HEIGHT

    @property
    def _entries_height(self):
        return self._footer_start - self.HEADER_HEIGHT

    def _draw_header(self) -> None:
        _, width = self._header_win.getmaxyx()
        self._header_win.clear()

        input_name = self._input_controller.get_input_name()
        title = f"Juffi - JSON Log Viewer - {input_name}"
        self._header_win.addstr(0, 1, title[: width - 2], self._colors["HEADER"])

        self._header_win.addstr(1, 1, "─" * (width - 2), self._colors["HEADER"])

        self._header_win.refresh()

    def _draw_footer(self) -> None:
        _, width = self._footer_win.getmaxyx()
        self._footer_win.clear()

        status = self._get_status_line()

        self._footer_win.addstr(0, 1, status[: width - 2], self._colors["INFO"])

        if self._state.input_mode:
            visible_prompt, input_text = self._get_prompt_and_input_text(width)
            self._footer_win.addstr(1, 1, visible_prompt, self._colors["DEFAULT"])
            self._footer_win.addstr(
                1, 1 + len(visible_prompt), input_text, self._colors["DEFAULT"]
            )
            self._footer_win.move(
                1, 1 + len(visible_prompt) + self._state.input_cursor_pos
            )
            curses.curs_set(1)
        else:
            curses.curs_set(0)

        self._footer_win.refresh()

    def _get_prompt_and_input_text(self, width):
        prompt = ""
        if self._state.input_mode == "search":
            prompt = "Search: "
        elif self._state.input_mode == "filter" and self._state.current_column:
            prompt = f"Filter {self._state.current_column}: "
        elif self._state.input_mode == "goto":
            prompt = "Go to line: "

        visible_prompt = prompt[: width - 2]
        input_text = self._state.input_buffer[: width - 2 - len(visible_prompt)]

        return visible_prompt, input_text

    def _get_status_line(self):
        status_parts = []
        if self._state.current_mode == ViewMode.DETAILS:
            status_parts.append("DETAILS")
        if self._state.follow_mode:
            status_parts.append("FOLLOW")
        if self._state.filtered_entries:
            status_parts.append(
                f"Row {self._state.current_row + 1}/{len(self._state.filtered_entries)}"
            )
        else:
            status_parts.append("No entries")

        if self._state.sort_column:
            direction = "DESC" if self._state.sort_reverse else "ASC"
            status_parts.append(f"Sort: {self._state.sort_column} {direction}")

        if self._state.filters_count > 0:
            status_parts.append(f"Filters: {self._state.filters_count}")

        status_parts.append("Press 'h' for help")
        status = " | ".join(status_parts)
        return status

    def run(self) -> None:  # pylint: disable=too-many-branches
        """Main TUI loop"""
        self._state.terminal_size = get_curses_yx()
        curses.curs_set(0)
        self._stdscr.timeout(100)

        self._stdscr.keypad(True)

        while True:
            key = self._input_controller.get_input()
            logger.debug("Key pressed: %s", key)

            if key == -1 and self._model.update_entries():
                self._entries_window.set_data()

            elif key == curses.KEY_RESIZE:
                curses.update_lines_cols()
                self._model.update_terminal_size()

            elif (not self._state.input_mode and key == ord("q")) or key == ESC:
                return
            elif not self._state.input_mode and key == ord("R"):
                self._reset()
            elif not self._state.input_mode and key in {
                ord("d"),
                ord("h"),
                ord("?"),
                ord("m"),
            }:
                self._switch_mode(key)
            elif self._state.current_mode == ViewMode.HELP:
                self._help_mode.handle_input(key)
            elif self._state.current_mode == ViewMode.COLUMN_MANAGEMENT:
                self._column_management_mode.handle_input(key)
            elif self._state.current_mode == ViewMode.BROWSE:
                self._browse_mode.handle_input(key)
            else:
                self._details_mode.handle_input(key)

            if "follow_mode" in self._state.changes:
                self._stdscr.timeout(1000 if self._state.follow_mode else -1)

            if self._needs_resize:
                self._resize_windows()
                self._needs_resize = False

            if self._needs_header_redraw:
                self._draw_header()
                self._needs_header_redraw = False

            if self._state.current_mode == ViewMode.HELP:
                self._help_mode.draw(self._stdscr)
            elif self._state.current_mode == ViewMode.COLUMN_MANAGEMENT:
                self._column_management_mode.draw()
            elif self._state.current_mode == ViewMode.BROWSE:
                self._browse_mode.draw()
            else:
                self._details_mode.draw(self._state.filtered_entries)

            if self._needs_footer_redraw:
                self._draw_footer()
                self._needs_footer_redraw = False

            self._state.clear_changes()

    def _switch_mode(self, key: int) -> None:
        previous_mode = self._state.current_mode

        if key == ord("d"):
            self._state.current_mode = (
                ViewMode.DETAILS
                if self._state.current_mode == ViewMode.BROWSE
                else ViewMode.BROWSE
            )
        elif key == ord("m"):
            self._state.current_mode = (
                ViewMode.COLUMN_MANAGEMENT
                if self._state.current_mode == ViewMode.BROWSE
                else ViewMode.BROWSE
            )
        elif key in {ord("h"), ord("?")}:
            self._state.current_mode = (
                ViewMode.HELP
                if self._state.current_mode != ViewMode.HELP
                else self._state.previous_mode
            )

        self._state.previous_mode = previous_mode
        if self._state.current_mode == ViewMode.DETAILS:
            self._details_mode.enter_mode()
        elif self._state.current_mode == ViewMode.COLUMN_MANAGEMENT:
            self._column_management_mode.enter_mode()
