"""Browse mode viewmodel - handles business logic and state management"""

from typing import Callable

from juffi.models.juffi_model import JuffiState


class BrowseViewModel:
    """Handles browse mode business logic and state management"""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        state: JuffiState,
        no_follow: bool,
        on_apply_filters: Callable[[], None],
        on_load_entries: Callable[[], None],
        on_reset: Callable[[], None],
    ) -> None:
        self._state = state
        self.on_apply_filters = on_apply_filters
        self.on_load_entries = on_load_entries
        self.on_reset = on_reset

        # Initialize follow mode
        self._state.follow_mode = not no_follow

    def handle_search_command(self) -> None:
        """Handle search command (/)"""
        self._state.input_mode = "search"
        self._state.input_buffer = self._state.search_term

    def handle_filter_command(self, current_column: str | None) -> None:
        """Handle filter command (f)"""
        if current_column:
            self._state.input_mode = "filter"
            self._state.input_column = current_column
            self._state.input_buffer = self._state.filters.get(current_column, "")

    def handle_goto_command(self) -> None:
        """Handle goto command (g)"""
        self._state.input_mode = "goto"
        self._state.input_buffer = ""

    def handle_clear_filters_command(self) -> None:
        """Handle clear filters command (c)"""
        self._state.clear_filters()
        self._state.search_term = ""
        self.on_apply_filters()

    def handle_sort_command(
        self, current_column: str | None, reverse: bool = False
    ) -> None:
        """Handle sort command (s/S)"""
        if current_column:
            if reverse:
                self._state.sort_column = current_column
                self._state.sort_reverse = True
            else:
                if self._state.sort_column == current_column:
                    self._state.sort_reverse = not self._state.sort_reverse
                else:
                    self._state.sort_column = current_column
                    self._state.sort_reverse = False
            self.on_apply_filters()

    def handle_toggle_follow_command(self) -> None:
        """Handle toggle follow mode command (F)"""
        self._state.follow_mode = not self._state.follow_mode

    def handle_reload_command(self) -> None:
        """Handle reload command (r)"""
        self.on_load_entries()
        self.on_apply_filters()

    def handle_reset_command(self) -> None:
        """Handle reset command (R)"""
        self.on_reset()
        self.on_apply_filters()

    def handle_input_submission(
        self, goto_line_callback: Callable[[int], None]
    ) -> None:
        """Handle input submission (Enter key)"""
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
                return

            if line_num < 1:
                return
            goto_line_callback(line_num - 1)

        self.on_apply_filters()
        self._clear_input_state()

    def handle_input_cancellation(self) -> None:
        """Handle input cancellation (Escape key)"""
        self._clear_input_state()

    def handle_input_backspace(self) -> None:
        """Handle backspace in input mode"""
        if self._state.input_cursor_pos > 0:
            self._state.input_buffer = (
                self._state.input_buffer[: self._state.input_cursor_pos - 1]
                + self._state.input_buffer[self._state.input_cursor_pos :]
            )
            self._state.input_cursor_pos -= 1

    def handle_input_delete(self) -> None:
        """Handle delete key in input mode"""
        self._state.input_buffer = (
            self._state.input_buffer[: self._state.input_cursor_pos]
            + self._state.input_buffer[self._state.input_cursor_pos + 1 :]
        )

    def handle_input_cursor_left(self) -> None:
        """Handle left arrow in input mode"""
        self._state.input_cursor_pos = max(0, self._state.input_cursor_pos - 1)

    def handle_input_cursor_right(self) -> None:
        """Handle right arrow in input mode"""
        self._state.input_cursor_pos = min(
            len(self._state.input_buffer), self._state.input_cursor_pos + 1
        )

    def handle_input_character(self, char: str) -> None:
        """Handle character input in input mode"""
        self._state.input_buffer = (
            self._state.input_buffer[: self._state.input_cursor_pos]
            + char
            + self._state.input_buffer[self._state.input_cursor_pos :]
        )
        self._state.input_cursor_pos += 1

    def _clear_input_state(self) -> None:
        """Clear input mode state"""
        self._state.input_mode = None
        self._state.input_buffer = ""
        self._state.input_column = None
        self._state.input_cursor_pos = 0
