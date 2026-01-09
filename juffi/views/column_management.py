"""Handles the column management screen"""

import curses
import textwrap

from juffi.helpers.curses_utils import Color, Position, Size, TextAttribute, Viewport
from juffi.models.juffi_model import JuffiState
from juffi.output_controller import Window
from juffi.viewmodels.column_management import ButtonActions, ColumnManagementViewModel


class ColumnManagementMode:
    """Handles the column management screen"""

    def __init__(
        self,
        state: JuffiState,
        window: Window,
    ) -> None:
        self._state = state
        self._window = window
        self._view_model = ColumnManagementViewModel()

        # Set up watcher to update view-model when new columns are discovered
        self._state.register_watcher(
            "all_discovered_columns", self._update_view_model_columns
        )

    def enter_mode(self) -> None:
        """Called when entering column management mode"""
        self._view_model.initialize_from_columns(
            self._state.columns, self._state.all_discovered_columns.copy()
        )

    def _update_view_model_columns(self) -> None:
        """Update view-model when new columns are discovered"""
        self._view_model.update_all_columns(self._state.all_discovered_columns)

    def handle_input(self, key: int) -> None:
        """Handle input for column management mode"""
        if key == ord("\t"):
            self._view_model.switch_focus()
        elif key == ord("\n"):
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

    def _handle_button_action(self, action: ButtonActions) -> None:
        """Handle button actions (OK, Cancel, Reset)"""
        if action == ButtonActions.OK:
            self._apply_column_changes()
            self._state.current_mode = self._state.previous_mode
        elif action == ButtonActions.CANCEL:
            self._state.current_mode = self._state.previous_mode
        elif action == ButtonActions.RESET:
            sorted_columns = self._state.get_default_sorted_columns()
            self._view_model.reset_to_default(sorted_columns)
        else:
            raise NotImplementedError(f"Unhandled button action: {action}")

    def _apply_column_changes(self) -> None:
        """Apply column management changes to the main columns"""
        self._state.set_columns_from_names(self._view_model.selected_columns)

    def draw(self) -> None:
        """Draw the column management screen"""
        size = self._window.getmaxyx()
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
            self._view_model.is_pane_focused("available"),
        )
        self._draw_pane_items(
            self._view_model.is_pane_focused("available"),
            self._view_model.get_available_columns(),
            Viewport(Position(pane_y, left_x), size),
        )

        # Draw selected columns pane
        self._draw_pane(
            "Selected Columns",
            Viewport(Position(pane_y, right_x), Size(pane_height, pane_width)),
            self._view_model.is_pane_focused("selected"),
        )
        self._draw_pane_items(
            self._view_model.is_pane_focused("selected"),
            self._view_model.get_selected_columns(),
            Viewport(Position(pane_y, right_x), size),
        )

        # Draw buttons
        self._draw_buttons(size.height - 3, size.width)

        self._window.refresh()

    def _draw_header(self, width: int) -> int:
        title = "Column Management"
        title_x = max(0, (width - len(title)) // 2)
        if title_x + len(title) <= width:
            self._window.addstr(Position(1, title_x), title, color=Color.HEADER)

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
                    Position(2 + i, instructions_x),
                    line,
                    color=Color.INFO,
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
        border_color = Color.SELECTED if is_focused else Color.DEFAULT

        self._window.addstr(
            Position(viewport.y, viewport.x),
            "┌" + "─" * (viewport.width - 2) + "┐",
            color=border_color,
        )

        title_x = viewport.x + (viewport.width - len(title)) // 2
        self._window.addstr(Position(viewport.y, title_x), title, color=Color.HEADER)
        for i in range(1, viewport.height - 1):
            self._window.addstr(
                Position(viewport.y + i, viewport.x), "│", color=border_color
            )
            self._window.addstr(
                Position(viewport.y + i, viewport.x + viewport.width - 1),
                "│",
                color=border_color,
            )

        self._window.addstr(
            Position(viewport.y + viewport.height - 1, viewport.x),
            "└" + "─" * (viewport.width - 2) + "┘",
            color=border_color,
        )

    def _draw_pane_items(
        self,
        is_focused: bool,
        items: list[tuple[str, bool]],
        viewport: Viewport,
    ) -> None:
        for i, (item, is_selected) in enumerate(items):
            if self._view_model.is_column_selected(item):
                item_color = Color.HEADER
                item_attributes = [TextAttribute.REVERSE]
            elif is_focused and is_selected:
                item_color = Color.SELECTED
                item_attributes = None
            else:
                item_color = Color.DEFAULT
                item_attributes = None

            item_text = item[: viewport.width - 4]
            self._window.addstr(
                Position(viewport.y + i + 1, viewport.x + 2),
                item_text,
                color=item_color,
                attributes=item_attributes,
            )

    def _draw_buttons(self, y: int, width: int) -> None:
        """Draw the OK, Cancel, Reset buttons"""
        button_width = 10
        total_width = len(ButtonActions) * button_width + (len(ButtonActions) - 1) * 2
        start_x = (width - total_width) // 2

        for i, button in enumerate(ButtonActions):
            x = start_x + i * (button_width + 2)
            is_selected = self._view_model.is_button_selected(button)

            color = Color.SELECTED if is_selected else Color.DEFAULT
            button_text = f"[{button.value:^8}]"
            self._window.addstr(Position(y, x), button_text, color=color)
