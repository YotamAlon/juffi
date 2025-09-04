import curses
from typing import Callable

from juffi.helpers.curses_utils import ESC, DEL
from juffi.models.juffi_model import JuffiState
from juffi.views.entries import EntriesWindow


class BrowseMode:  # pylint: disable=too-many-instance-attributes
    """Handles browse mode input and drawing logic"""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        state: JuffiState,
        no_follow: bool,
        entries_window: EntriesWindow,
        colors: dict[str, int],
        on_apply_filters: Callable[[], None],
        on_load_entries: Callable[[], None],
        on_reset: Callable[[], None],
    ) -> None:
        self._state = state
        self.entries_window = entries_window
        self.colors = colors
        self.on_apply_filters = on_apply_filters
        self.on_load_entries = on_load_entries
        self.on_reset = on_reset

        # Browse mode specific state (not tracked in JuffiState)
        self.filters: dict[str, str] = {}
        self.search_term: str = ""
        self._state.follow_mode = not no_follow

    def handle_input(self, key: int) -> None:
        """Handle input for browse mode. Returns True if key was handled."""
        if self._state.input_mode:
            self._handle_input_submode(key)

        elif key == ord("/"):
            self._state.input_mode = "search"
            self._state.input_buffer = self._state.search_term
        elif key == ord("f"):
            current_col = self.entries_window.get_current_column()
            if current_col:
                self._state.input_mode = "filter"
                self._state.input_column = current_col
                self._state.input_buffer = self._state.filters.get(current_col, "")
        elif key == ord("g"):
            self._state.input_mode = "goto"
            self._state.input_buffer = ""
        elif key == ord("c"):
            self._state.clear_filters()
            self.search_term = ""
            self.on_apply_filters()
        elif key == ord("s"):
            current_col = self.entries_window.get_current_column()
            if current_col:
                if self._state.sort_column == current_col:
                    self._state.sort_reverse = not self._state.sort_reverse
                else:
                    self._state.sort_column = current_col
                    self._state.sort_reverse = False
                self.on_apply_filters()
        elif key == ord("S"):
            current_col = self.entries_window.get_current_column()
            if current_col:
                self._state.sort_column = current_col
                self._state.sort_reverse = True
                self.on_apply_filters()
        elif key == ord("<"):
            self.entries_window.move_column(to_the_right=False)
        elif key == ord(">"):
            self.entries_window.move_column(to_the_right=True)
        elif key == ord("w"):
            self.entries_window.adjust_column_width(-5)
        elif key == ord("W"):
            self.entries_window.adjust_column_width(5)
        elif key == ord("F"):
            self._state.follow_mode = not self._state.follow_mode
        elif key == ord("r"):
            self.on_load_entries()
            self.on_apply_filters()
        elif key == ord("R"):
            self.on_reset()
            self.on_apply_filters()
        else:
            self.entries_window.handle_navigation(key)

    def _handle_input_submode(self, key: int) -> None:
        """Handle input for search/filter/goto submodes. Returns True if key was handled."""
        if key == ESC or key == ord("\n"):
            if key == ord("\n"):
                if self._state.input_mode == "search":
                    self._state.search_term = self._state.input_buffer
                elif self._state.input_mode == "filter" and self._state.input_column:
                    self._state.update_filters(
                        {self._state.input_column: self._state.input_buffer}
                    )
                elif self._state.input_mode == "goto":
                    try:
                        line_num = int(self._state.input_buffer)
                    except ValueError:
                        pass  # Invalid line number, ignore
                    else:
                        self.entries_window.goto_line(line_num)

                self.on_apply_filters()

            self._state.input_mode = None
            self._state.input_buffer = ""
            self._state.input_column = None
            self._state.input_cursor_pos = 0
        elif key in (curses.KEY_BACKSPACE, DEL):
            self._state.input_buffer = (
                self._state.input_buffer[: self._state.input_cursor_pos - 1]
                + self._state.input_buffer[self._state.input_cursor_pos :]
            )
            self._state.input_cursor_pos = max(0, self._state.input_cursor_pos - 1)
        elif key == curses.KEY_DC:
            self._state.input_buffer = (
                self._state.input_buffer[: self._state.input_cursor_pos]
                + self._state.input_buffer[self._state.input_cursor_pos + 1 :]
            )
        elif key == curses.KEY_LEFT:
            self._state.input_cursor_pos = max(0, self._state.input_cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            self._state.input_cursor_pos = min(
                len(self._state.input_buffer), self._state.input_cursor_pos + 1
            )
        else:
            # Add character to input buffer
            if 32 <= key <= 126:  # Printable ASCII characters
                self._state.input_buffer = (
                    self._state.input_buffer[: self._state.input_cursor_pos]
                    + chr(key)
                    + self._state.input_buffer[self._state.input_cursor_pos :]
                )
                self._state.input_cursor_pos += 1

    def draw(self) -> None:
        """Draw browse mode (entries view)"""
        self.entries_window.draw()
