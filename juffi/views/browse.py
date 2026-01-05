"""Browse mode view - handles UI rendering and input delegation"""

import curses
from typing import Callable

from juffi.helpers.curses_utils import DEL, ESC
from juffi.models.juffi_model import JuffiState
from juffi.viewmodels.browse import BrowseViewModel
from juffi.views.entries import EntriesWindow


class BrowseMode:
    """Handles browse mode UI rendering and input delegation"""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        state: JuffiState,
        no_follow: bool,
        entries_window: EntriesWindow,
        on_apply_filters: Callable[[], None],
        on_load_entries: Callable[[], None],
        on_reset: Callable[[], None],
    ) -> None:
        self._state = state
        self.entries_window = entries_window

        # Create viewmodel to handle business logic
        self.viewmodel = BrowseViewModel(
            state=state,
            no_follow=no_follow,
            on_apply_filters=on_apply_filters,
            on_load_entries=on_load_entries,
            on_reset=on_reset,
        )

    def handle_input(self, key: int) -> None:  # pylint: disable=too-many-branches
        """Handle input for browse mode, delegating business logic to viewmodel"""
        if self._state.input_mode:
            self._handle_input_submode(key)
        elif key == ord("/"):
            self.viewmodel.handle_search_command()
        elif key == ord("f"):
            current_col = self.entries_window.get_current_column()
            self.viewmodel.handle_filter_command(current_col)
        elif key == ord("g"):
            self.viewmodel.handle_goto_command()
        elif key == ord("c"):
            self.viewmodel.handle_clear_filters_command()
        elif key == ord("s"):
            current_col = self.entries_window.get_current_column()
            self.viewmodel.handle_sort_command(current_col, reverse=False)
        elif key == ord("S"):
            current_col = self.entries_window.get_current_column()
            self.viewmodel.handle_sort_command(current_col, reverse=True)
        elif key == ord("<"):
            self.entries_window.move_column(to_the_right=False)
        elif key == ord(">"):
            self.entries_window.move_column(to_the_right=True)
        elif key == ord("w"):
            self.entries_window.adjust_column_width(-5)
        elif key == ord("W"):
            self.entries_window.adjust_column_width(5)
        elif key == ord("F"):
            self.viewmodel.handle_toggle_follow_command()
        elif key == ord("r"):
            self.viewmodel.handle_reload_command()
        else:
            self.entries_window.handle_navigation(key)

    def _handle_input_submode(self, key: int) -> None:
        """Handle input for search/filter/goto submodes, delegating to viewmodel"""
        if key == ESC:
            self.viewmodel.handle_input_cancellation()
        elif key == ord("\n"):
            self.viewmodel.handle_input_submission(self.entries_window.goto_line)
        elif key in (curses.KEY_BACKSPACE, DEL):
            self.viewmodel.handle_input_backspace()
        elif key == curses.KEY_DC:
            self.viewmodel.handle_input_delete()
        elif key == curses.KEY_LEFT:
            self.viewmodel.handle_input_cursor_left()
        elif key == curses.KEY_RIGHT:
            self.viewmodel.handle_input_cursor_right()
        elif 32 <= key <= 126:  # Printable ASCII characters
            self.viewmodel.handle_input_character(chr(key))

    def draw(self) -> None:
        """Draw browse mode (entries view)"""
        self.entries_window.draw()
