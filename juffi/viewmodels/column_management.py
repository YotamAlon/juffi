"""Column management viewmodel - handles business logic and state management"""

import enum
from typing import Literal

from juffi.helpers.indexed_dict import IndexedDict
from juffi.models.column import Column


class ButtonActions(enum.Enum):
    """Button actions in column management"""

    OK = "OK"
    CANCEL = "Cancel"
    RESET = "Reset"


class ColumnManagementViewModel:  # pylint: disable=too-many-instance-attributes
    """View-model for column management logic, separate from UI concerns"""

    def __init__(self) -> None:
        self._focus: Literal["panes", "buttons"] = "panes"
        self._button_selection: ButtonActions = ButtonActions.OK
        self._selected_column: str | None = None
        self._pane_manager = PaneManager()

    @property
    def selected_columns(self) -> list[str]:
        """Get the selected columns"""
        return self._pane_manager.selected_columns

    def get_available_columns(self) -> list[tuple[str, bool]]:
        """Get the available columns with selection state"""
        return [
            (col, i == self._pane_manager.available_selection)
            for i, col in enumerate(self._pane_manager.available_columns)
        ]

    def get_selected_columns(self) -> list[tuple[str, bool]]:
        """Get the available columns with selection state"""
        return [
            (col, i == self._pane_manager.selected_selection)
            for i, col in enumerate(self._pane_manager.selected_columns)
        ]

    def is_pane_focused(self, pane: Literal["available", "selected"]) -> bool:
        """Check if a pane is focused"""
        return self._focus == "panes" and self._pane_manager.is_pane_focused(pane)

    def is_column_selected(self, column: str) -> bool:
        """Check if a column is selected"""
        return self._pane_manager.is_column_selected(column)

    def is_button_selected(self, button: ButtonActions) -> bool:
        """Check if a button is selected"""
        return self._focus == "buttons" and button == self._button_selection

    def initialize_from_columns(
        self, current_columns: IndexedDict[Column], all_columns: set[str]
    ) -> None:
        """Initialize column management with current column state"""
        self._focus = "panes"
        self._button_selection = ButtonActions.OK
        self._pane_manager.initialize_from_columns(current_columns, all_columns)

    def update_all_columns(self, new_columns: set[str]) -> None:
        """Update the set of all discovered columns"""
        self._pane_manager.update_all_columns(new_columns)

    def reset_to_default(self, sorted_columns: list[str]) -> None:
        """Reset column management to default state with provided sorted columns"""
        self._pane_manager.reset_to_default(sorted_columns)

    def switch_focus(self) -> None:
        """Switch focus between panes and buttons"""
        if self._focus == "panes":
            self._focus = "buttons"
        else:
            self._focus = "panes"

    def move_focus(self, direction: Literal["left", "right"]) -> None:
        """Move focus left or right"""
        if self._focus == "panes":
            self._pane_manager.move_focus(direction)
        else:
            if direction == "left":
                self._move_button(-1)
            else:
                self._move_button(1)

    def handle_enter(self) -> ButtonActions | None:
        """Handle enter key based on current focus. Returns button action or None"""
        if self._focus == "panes":
            self._pane_manager.handle_enter()
        elif self._focus == "buttons":
            return self._get_button_action()
        return None

    def _get_button_action(self) -> ButtonActions:
        """Get the current button action"""
        return self._button_selection

    def move_selection(self, delta: int) -> None:
        """Move selection up or down in current pane, or move selected column"""
        # If we have a selected column, move it instead of changing selection
        self._pane_manager.move_selection(delta)

    def _move_button(self, delta):
        current_index = list(ButtonActions).index(self._button_selection)
        new_index = max(0, min(2, current_index + delta))
        self._button_selection = list(ButtonActions)[new_index]


class PaneManager:
    """Manages the state of the two panes in column management"""

    def __init__(self) -> None:
        self._focused_pane: Literal["available", "selected"] = "available"
        self.available_selection: int = 0
        self.selected_selection: int = 0
        self.available_columns: list[str] = []
        self.selected_columns: list[str] = []
        self._all_columns: set[str] = set()
        self._selected_column: str | None = None

    def is_pane_focused(self, pane: Literal["available", "selected"]) -> bool:
        """Check if a pane is focused"""
        return self._focused_pane == pane

    def is_column_selected(self, column: str) -> bool:
        """Check if a column is selected"""
        return column == self._selected_column

    def initialize_from_columns(
        self, columns: IndexedDict[Column], all_columns: set[str]
    ) -> None:
        """Initialize column management with current column state"""
        self._all_columns = all_columns
        currently_selected = list(columns.keys())  # Current visible columns

        # Update all_columns with any new columns from the current visible set
        self._all_columns.update(currently_selected)

        self.selected_columns = currently_selected.copy()
        self.available_columns = [
            col for col in self._all_columns if col not in currently_selected
        ]
        self.available_columns.sort()  # Keep available columns sorted

        # Reset selections
        self._focused_pane = "available"
        self.available_selection = 0
        self.selected_selection = 0
        self._selected_column = None

    def update_all_columns(self, new_columns: set[str]) -> None:
        """Update the set of all discovered columns"""
        old_available = set(self.available_columns)
        self._all_columns.update(new_columns)

        # Update available columns with any new columns not currently selected
        self.available_columns = [
            col for col in self._all_columns if col not in self.selected_columns
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

    def move_focus(self, direction: Literal["left", "right"]) -> None:
        """Move focus left or right"""
        if direction == "left":
            self._move_focus_left()
        else:
            self._move_focus_right()

    def _move_focus_left(self) -> None:
        """Move focus to the left pane or move selected column to available"""
        if self._selected_column:
            self.move_selected_column_to_available()
        elif self._focused_pane == "selected":
            self._focused_pane = "available"

    def _move_focus_right(self) -> None:
        """Move focus to the right pane or move selected column to selected"""
        if self._selected_column:
            self.move_selected_column_to_selected()
        elif self._focused_pane == "available":
            self._focused_pane = "selected"

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
            self._focused_pane = "available"
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
            self._focused_pane = "selected"
            self.selected_selection = len(self.selected_columns) - 1

            # Adjust available selection if needed
            if (
                self.available_selection >= len(self.available_columns)
                and self.available_columns
            ):
                self.available_selection = len(self.available_columns) - 1

    def handle_enter(self) -> None:
        """Handle enter key based on current focus. Returns button action or None"""
        if self._focused_pane == "available":
            self._select_column_from_available()
        elif self._focused_pane == "selected":
            self._select_column_from_selected()

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

    def move_selection(self, delta: int) -> None:
        """Move selection up or down in current pane, or move selected column"""
        # If we have a selected column, move it instead of changing selection
        if self._selected_column:
            self.move_selected_column(delta)
            return

        # Otherwise, move the selection cursor
        if self._focused_pane == "available":
            if self.available_columns:
                self.available_selection = max(
                    0,
                    min(
                        len(self.available_columns) - 1,
                        self.available_selection + delta,
                    ),
                )
        elif self._focused_pane == "selected":
            if self.selected_columns:
                self.selected_selection = max(
                    0,
                    min(
                        len(self.selected_columns) - 1,
                        self.selected_selection + delta,
                    ),
                )

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
