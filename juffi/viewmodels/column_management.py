"""Column management viewmodel - handles business logic and state management"""

import enum
from typing import Literal

from juffi.helpers.indexed_dict import IndexedDict
from juffi.models.column import Column


class ButtonActions(enum.StrEnum):
    """Button actions in column management"""

    OK = "OK"
    CANCEL = "Cancel"
    RESET = "Reset"


class ColumnManagementViewModel:  # pylint: disable=too-many-instance-attributes
    """View-model for column management logic, separate from UI concerns"""

    def __init__(self) -> None:
        self.focus: Literal["panes", "buttons"] = "panes"
        self.focused_pane: Literal["available", "selected"] = "available"
        self.available_selection: int = 0
        self.selected_selection: int = 0
        self.button_selection: ButtonActions = ButtonActions.OK
        self.available_columns: list[str] = []
        self.selected_columns: list[str] = []
        self.all_columns: set[str] = set()
        self._selected_column: str | None = None

    def is_column_selected(self, column: str) -> bool:
        """Check if a column is selected"""
        return column == self._selected_column

    def is_button_selected(self, button: ButtonActions) -> bool:
        """Check if a button is selected"""
        return self.focus == "buttons" and button == self.button_selection

    def initialize_from_columns(self, columns: IndexedDict[Column]) -> None:
        """Initialize column management with current column state"""
        currently_selected = list(columns.keys())  # Current visible columns

        # Update all_columns with any new columns from the current visible set
        self.all_columns.update(currently_selected)

        self.selected_columns = currently_selected.copy()
        self.available_columns = [
            col for col in self.all_columns if col not in currently_selected
        ]
        self.available_columns.sort()  # Keep available columns sorted

        # Reset selections
        self.focus = "panes"
        self.focused_pane = "available"
        self.available_selection = 0
        self.selected_selection = 0
        self.button_selection = ButtonActions.OK
        self._selected_column = None

    def update_all_columns(self, new_columns: set[str]) -> None:
        """Update the set of all discovered columns"""
        old_available = set(self.available_columns)
        self.all_columns.update(new_columns)

        # Update available columns with any new columns not currently selected
        self.available_columns = [
            col for col in self.all_columns if col not in self.selected_columns
        ]
        self.available_columns.sort()

        # Adjust available selection if the list changed
        if set(self.available_columns) != old_available and self.available_columns:
            self.available_selection = min(
                self.available_selection, len(self.available_columns) - 1
            )

    def reset_to_default(self, sorted_columns: list[str]) -> None:
        """Reset column management to default state with provided sorted columns"""
        self.selected_columns = sorted_columns.copy()
        self.available_columns = []

    def switch_focus(self) -> None:
        """Switch focus between panes and buttons"""
        if self.focus == "panes":
            self.focus = "buttons"
        else:
            self.focus = "panes"

    def move_focus(self, direction: Literal["left", "right"]) -> None:
        """Move focus left or right"""
        if direction == "left":
            self._move_focus_left()
        else:
            self._move_focus_right()

    def _move_focus_left(self) -> None:
        """Move focus to the left pane or move selected column to available"""
        if self.focus == "panes":
            if self._selected_column:
                self.move_selected_column_to_available()
            elif self.focused_pane == "selected":
                self.focused_pane = "available"
        else:
            self._move_button(-1)

    def _move_focus_right(self) -> None:
        """Move focus to the right pane or move selected column to selected"""
        if self.focus == "panes":
            if self._selected_column:
                self.move_selected_column_to_selected()
            elif self.focused_pane == "available":
                self.focused_pane = "selected"
        else:
            self._move_button(1)

    def move_selected_column_to_available(self) -> None:
        """Move the currently selected column to available list"""
        if not self._selected_column:
            return

        column = self._selected_column

        # Only move if it's currently in selected list
        if column in self.selected_columns:
            self.selected_columns.remove(column)
            self.available_columns.append(column)
            self.available_columns.sort()  # Keep available sorted

            # Update selections and focus
            self.focused_pane = "available"
            self.available_selection = self.available_columns.index(column)

            # Adjust selected selection if needed
            if (
                self.selected_selection >= len(self.selected_columns)
                and self.selected_columns
            ):
                self.selected_selection = len(self.selected_columns) - 1

    def move_selected_column_to_selected(self) -> None:
        """Move the currently selected column to selected list"""
        if not self._selected_column:
            return

        column = self._selected_column

        # Only move if it's currently in available list
        if column in self.available_columns:
            self.available_columns.remove(column)
            self.selected_columns.append(column)

            # Update selections and focus
            self.focused_pane = "selected"
            self.selected_selection = len(self.selected_columns) - 1

            # Adjust available selection if needed
            if (
                self.available_selection >= len(self.available_columns)
                and self.available_columns
            ):
                self.available_selection = len(self.available_columns) - 1

    def handle_enter(self) -> ButtonActions | None:
        """Handle enter key based on current focus. Returns button action or None"""
        if self.focus == "panes":
            if self.focused_pane == "available":
                self._select_column_from_available()
            elif self.focused_pane == "selected":
                self._select_column_from_selected()
        elif self.focus == "buttons":
            return self._get_button_action()
        return None

    def _select_column_from_available(self) -> None:
        """Select a column from available list for movement"""
        if not self.available_columns:
            return

        idx = self.available_selection
        if 0 <= idx < len(self.available_columns):
            column = self.available_columns[idx]
            if self._selected_column == column:
                # Deselect if already selected
                self._selected_column = None
            else:
                # Select this column
                self._selected_column = column

    def _select_column_from_selected(self) -> None:
        """Select a column from selected list for movement"""
        if not self.selected_columns:
            return

        idx = self.selected_selection
        if 0 <= idx < len(self.selected_columns):
            column = self.selected_columns[idx]
            if self._selected_column == column:
                # Deselect if already selected
                self._selected_column = None
            else:
                # Select this column
                self._selected_column = column

    def _get_button_action(self) -> ButtonActions:
        """Get the current button action"""
        return self.button_selection

    def move_selection(self, delta: int) -> None:
        """Move selection up or down in current pane, or move selected column"""
        # If we have a selected column, move it instead of changing selection
        if self._selected_column:
            self.move_selected_column(delta)
            return

        # Otherwise, move the selection cursor
        if self.focused_pane == "available":
            if self.available_columns:
                self.available_selection = max(
                    0,
                    min(
                        len(self.available_columns) - 1,
                        self.available_selection + delta,
                    ),
                )
        elif self.focused_pane == "selected":
            if self.selected_columns:
                self.selected_selection = max(
                    0,
                    min(
                        len(self.selected_columns) - 1,
                        self.selected_selection + delta,
                    ),
                )

    def _move_button(self, delta):
        current_index = list(ButtonActions).index(self.button_selection)
        new_index = max(0, min(2, current_index + delta))
        self.button_selection = list(ButtonActions)[new_index]

    def move_selected_column(self, delta: int) -> None:
        """Move the currently selected column up or down"""
        if not self._selected_column:
            return

        column = self._selected_column

        # Find which list contains the selected column
        if column in self.available_columns:
            items = self.available_columns
            current_idx = items.index(column)
            new_idx = max(0, min(len(items) - 1, current_idx + delta))

            if new_idx != current_idx:
                # Move the column
                items.insert(new_idx, items.pop(current_idx))
                self.available_selection = new_idx

        elif column in self.selected_columns:
            items = self.selected_columns
            current_idx = items.index(column)
            new_idx = max(0, min(len(items) - 1, current_idx + delta))

            if new_idx != current_idx:
                # Move the column
                items.insert(new_idx, items.pop(current_idx))
                self.selected_selection = new_idx
