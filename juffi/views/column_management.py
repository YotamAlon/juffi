"""Handles the column management screen"""

import curses
import textwrap

from juffi.helpers.curses_utils import Position, Size, Viewport
from juffi.models.juffi_model import JuffiState
from juffi.viewmodels.column_management import ButtonActions, ColumnManagementViewModel


class ColumnManagementMode:
    """Handles the column management screen"""

    def __init__(
        self,
        state: JuffiState,
        window: curses.window,
        colors: dict[str, int],
    ) -> None:
        self._state = state
        self._window = window
        self._colors = colors
        self._view_model = ColumnManagementViewModel()

        # Set up watcher to update view-model when new columns are discovered
        self._state.register_watcher(
            "all_discovered_columns", self._update_view_model_columns
        )

    def enter_mode(self) -> None:
        """Called when entering column management mode"""
        # Initialize with all discovered columns
        self._view_model.all_columns = self._state.all_discovered_columns.copy()
        self._view_model.initialize_from_columns(self._state.columns)

    def _update_view_model_columns(self) -> None:
        """Update view-model when new columns are discovered"""
        self._view_model.update_all_columns(self._state.all_discovered_columns)

    def handle_input(self, key: int) -> None:
        """Handle input for column management mode"""
        if key == ord("\t"):  # Tab - switch focus
            self._view_model.switch_focus()
        elif key == ord("\n"):  # Enter - action based on focus
            action = self._view_model.handle_enter()
            if action:
                self._handle_button_action(action)
        elif key == curses.KEY_UP:
            self._view_model.move_selection(-1)
        elif key == curses.KEY_DOWN:
            self._view_model.move_selection(1)
        elif key == curses.KEY_LEFT:
            self._view_model.move_focus("left")
        elif key == curses.KEY_RIGHT:
            self._view_model.move_focus("right")

    def _handle_button_action(self, action: str) -> None:
        """Handle button actions (OK, Cancel, Reset)"""
        if action == "ok":
            self._apply_column_changes()
            self._state.current_mode = self._state.previous_mode
        elif action == "cancel":
            self._state.current_mode = self._state.previous_mode
        elif action == "reset":
            sorted_columns = self._state.get_default_sorted_columns()
            self._view_model.reset_to_default(sorted_columns)

    def _apply_column_changes(self) -> None:
        """Apply column management changes to the main columns"""
        self._state.set_columns_from_names(self._view_model.selected_columns)

    def draw(self) -> None:
        """Draw the column management screen"""
        size = Size(*self._window.getmaxyx())
        self._window.clear()

        header_lines = self._draw_header(size.width)
        pane_width = max(10, (size.width - 6) // 2)
        pane_height = max(5, size.height - 8 - header_lines)
        left_x = 2
        right_x = left_x + pane_width + 2
        pane_y = 3 + header_lines

        # Draw available columns pane
        self._draw_pane(
            "Available Columns",
            Viewport(Position(pane_y, left_x), Size(pane_height, pane_width)),
            self._view_model.focus == "available",
        )
        self._draw_pane_items(
            self._view_model.focus == "available",
            self._view_model.available_columns,
            self._view_model.available_selection,
            Viewport(Position(pane_y, left_x), size),
        )

        # Draw selected columns pane
        self._draw_pane(
            "Selected Columns",
            Viewport(Position(pane_y, right_x), Size(pane_height, pane_width)),
            self._view_model.focus == "selected",
        )
        self._draw_pane_items(
            self._view_model.focus == "selected",
            self._view_model.selected_columns,
            self._view_model.selected_selection,
            Viewport(Position(pane_y, right_x), size),
        )

        # Draw buttons
        self._draw_buttons(size.height - 3, size.width)

        self._window.refresh()

    def _draw_header(self, width: int) -> int:
        title = "Column Management"
        title_x = max(0, (width - len(title)) // 2)
        if title_x + len(title) <= width:
            self._window.addstr(1, title_x, title, self._colors["HEADER"])

        instructions = (
            "←→: Move between panes/Move column "
            "| ↑↓: Navigate/Move column "
            "| Enter: Select column "
            "| Tab: Buttons"
        )
        wrapped_instructions = textwrap.wrap(instructions, width=width - 4)
        for i, line in enumerate(wrapped_instructions[:2]):
            instructions_x = max(0, (width - len(line)) // 2)
            if instructions_x + len(line) <= width:
                self._window.addstr(
                    2 + i,
                    instructions_x,
                    line,
                    self._colors["INFO"],
                )

        instructions_lines = min(len(wrapped_instructions), 2)
        return instructions_lines

    def _draw_pane(
        self,
        title: str,
        viewport: Viewport,
        is_focused: bool,
    ) -> None:
        """Draw a pane with title, border, and items"""
        border_color = (
            self._colors["SELECTED"] if is_focused else self._colors["DEFAULT"]
        )

        self._window.addstr(
            viewport.y, viewport.x, "┌" + "─" * (viewport.width - 2) + "┐", border_color
        )

        title_x = viewport.x + (viewport.width - len(title)) // 2
        self._window.addstr(viewport.y, title_x, title, self._colors["HEADER"])
        for i in range(1, viewport.height - 1):
            self._window.addstr(viewport.y + i, viewport.x, "│", border_color)
            self._window.addstr(
                viewport.y + i, viewport.x + viewport.width - 1, "│", border_color
            )

        self._window.addstr(
            viewport.y + viewport.height - 1,
            viewport.x,
            "└" + "─" * (viewport.width - 2) + "┘",
            border_color,
        )

    def _draw_pane_items(
        self,
        is_focused: bool,
        items: list[str],
        selection: int,
        viewport: Viewport,
    ) -> None:
        for i, item in enumerate(items):
            if self._view_model.is_column_selected(item):
                item_color = self._colors["HEADER"] | curses.A_REVERSE
            elif i == selection and is_focused:
                item_color = self._colors["SELECTED"]
            else:
                item_color = self._colors["DEFAULT"]

            item_text = item[: viewport.width - 4]
            self._window.addstr(
                viewport.y + i + 1, viewport.x + 2, item_text, item_color
            )

    def _draw_buttons(self, y: int, width: int) -> None:
        """Draw the OK, Cancel, Reset buttons"""
        button_width = 10
        total_width = len(ButtonActions) * button_width + (len(ButtonActions) - 1) * 2
        start_x = (width - total_width) // 2

        for i, button in enumerate(ButtonActions):
            x = start_x + i * (button_width + 2)
            is_selected = self._view_model.is_button_selected(button)

            color = self._colors["SELECTED"] if is_selected else self._colors["DEFAULT"]
            button_text = f"[{button:^8}]"
            self._window.addstr(y, x, button_text, color)
