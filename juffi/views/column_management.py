import curses

from juffi.models.juffi_model import JuffiState
from juffi.viewmodels.column_management import ColumnManagementViewModel


class ColumnManagementMode:
    """Handles the column management screen"""

    def __init__(
        self,
        state: JuffiState,
        colors: dict[str, int],
    ) -> None:
        self._state = state
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
        if key == 27:  # ESC - cancel
            self._state.current_mode = self._state.previous_mode
        elif key == ord("\t"):  # Tab - switch focus
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
            self._view_model.move_focus_left()
        elif key == curses.KEY_RIGHT:
            self._view_model.move_focus_right()

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

    def draw(self, stdscr: curses.window) -> None:
        """Draw the column management screen"""
        height, width = stdscr.getmaxyx()
        stdscr.clear()

        # Title
        title = "Column Management"
        stdscr.addstr(1, (width - len(title)) // 2, title, self._colors["HEADER"])

        # Instructions
        instructions = "←→: Move between panes/Move column | ↑↓: Navigate/Move column | Enter: Select column | Tab: Buttons | Esc: Cancel"
        stdscr.addstr(
            2,
            (width - len(instructions)) // 2,
            instructions,
            self._colors["INFO"],
        )

        # Calculate pane dimensions
        pane_width = (width - 6) // 2
        pane_height = height - 8
        left_x = 2
        right_x = left_x + pane_width + 2
        pane_y = 4

        # Draw available columns pane
        self._draw_pane(
            stdscr,
            "Available Columns",
            self._view_model.available_columns,
            self._view_model.available_selection,
            left_x,
            pane_y,
            pane_width,
            pane_height,
            self._view_model.focus == "available",
        )

        # Draw selected columns pane
        self._draw_pane(
            stdscr,
            "Selected Columns",
            self._view_model.selected_columns,
            self._view_model.selected_selection,
            right_x,
            pane_y,
            pane_width,
            pane_height,
            self._view_model.focus == "selected",
        )

        # Draw buttons
        self._draw_buttons(stdscr, height - 3, width)

        stdscr.refresh()

    def _draw_pane(
        self,
        stdscr: curses.window,
        title: str,
        items: list[str],
        selection: int,
        x: int,
        y: int,
        width: int,
        height: int,
        is_focused: bool,
    ) -> None:
        """Draw a pane with title, border, and items"""
        # Draw border
        border_color = (
            self._colors["SELECTED"] if is_focused else self._colors["DEFAULT"]
        )

        # Top border
        stdscr.addstr(y, x, "┌" + "─" * (width - 2) + "┐", border_color)
        # Title
        title_x = x + (width - len(title)) // 2
        stdscr.addstr(y, title_x, title, self._colors["HEADER"])

        # Side borders and content
        for i in range(1, height - 1):
            stdscr.addstr(y + i, x, "│", border_color)
            stdscr.addstr(y + i, x + width - 1, "│", border_color)

            # Draw item if within range
            item_idx = i - 1
            if 0 <= item_idx < len(items):
                item = items[item_idx]

                # Determine color based on selection state
                if item == self._view_model.selected_column:
                    # Highlight selected column for movement
                    item_color = self._colors["HEADER"] | curses.A_REVERSE
                elif item_idx == selection and is_focused:
                    # Normal selection highlight
                    item_color = self._colors["SELECTED"]
                else:
                    # Default color
                    item_color = self._colors["DEFAULT"]

                item_text = item[: width - 4]  # Leave space for borders and padding
                stdscr.addstr(y + i, x + 2, item_text, item_color)

        # Bottom border
        stdscr.addstr(y + height - 1, x, "└" + "─" * (width - 2) + "┘", border_color)

    def _draw_buttons(self, stdscr: curses.window, y: int, width: int) -> None:
        """Draw the OK, Cancel, Reset buttons"""
        buttons = ["OK", "Cancel", "Reset"]
        button_width = 10
        total_width = len(buttons) * button_width + (len(buttons) - 1) * 2
        start_x = (width - total_width) // 2

        for i, button in enumerate(buttons):
            x = start_x + i * (button_width + 2)
            is_selected = (
                self._view_model.focus == "buttons"
                and self._view_model.button_selection == i
            )

            color = self._colors["SELECTED"] if is_selected else self._colors["DEFAULT"]
            button_text = f"[{button:^8}]"
            stdscr.addstr(y, x, button_text, color)
