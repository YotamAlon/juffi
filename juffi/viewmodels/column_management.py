import dataclasses

from juffi.helpers.indexed_dict import IndexedDict
from juffi.models.column import Column


@dataclasses.dataclass
class ColumnManagementViewModel:
    """View-model for column management logic, separate from UI concerns"""

    focus: str = "available"  # "available", "selected", "buttons"
    available_selection: int = 0
    selected_selection: int = 0
    button_selection: int = 0  # 0=OK, 1=Cancel, 2=Reset
    selected_column: str | None = None  # Currently selected column for movement
    available_columns: list[str] = dataclasses.field(default_factory=list)
    selected_columns: list[str] = dataclasses.field(default_factory=list)
    all_columns: set[str] = dataclasses.field(
        default_factory=set
    )  # Track all discovered columns

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
        self.focus = "available"
        self.available_selection = 0
        self.selected_selection = 0
        self.button_selection = 0
        self.selected_column = None

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
        if self.focus == "available":
            self.focus = "selected"
        elif self.focus == "selected":
            self.focus = "buttons"
        else:
            self.focus = "available"

    def move_focus_left(self) -> None:
        """Move focus to the left pane or move selected column to available"""
        if self.selected_column:
            self.move_selected_column_to_available()
        elif self.focus == "selected":
            self.focus = "available"
        elif self.focus == "buttons":
            self.focus = "selected"

    def move_focus_right(self) -> None:
        """Move focus to the right pane or move selected column to selected"""
        if self.selected_column:
            self.move_selected_column_to_selected()
        elif self.focus == "available":
            self.focus = "selected"
        elif self.focus == "selected":
            self.focus = "buttons"

    def move_selected_column_to_available(self) -> None:
        """Move the currently selected column to available list"""
        if not self.selected_column:
            return

        column = self.selected_column

        # Only move if it's currently in selected list
        if column in self.selected_columns:
            self.selected_columns.remove(column)
            self.available_columns.append(column)
            self.available_columns.sort()  # Keep available sorted

            # Update selections and focus
            self.focus = "available"
            self.available_selection = self.available_columns.index(column)

            # Adjust selected selection if needed
            if (
                self.selected_selection >= len(self.selected_columns)
                and self.selected_columns
            ):
                self.selected_selection = len(self.selected_columns) - 1

    def move_selected_column_to_selected(self) -> None:
        """Move the currently selected column to selected list"""
        if not self.selected_column:
            return

        column = self.selected_column

        # Only move if it's currently in available list
        if column in self.available_columns:
            self.available_columns.remove(column)
            self.selected_columns.append(column)

            # Update selections and focus
            self.focus = "selected"
            self.selected_selection = len(self.selected_columns) - 1

            # Adjust available selection if needed
            if (
                self.available_selection >= len(self.available_columns)
                and self.available_columns
            ):
                self.available_selection = len(self.available_columns) - 1

    def handle_enter(self) -> str | None:
        """Handle enter key based on current focus. Returns button action or None"""
        if self.focus == "available":
            self.select_column_from_available()
        elif self.focus == "selected":
            self.select_column_from_selected()
        elif self.focus == "buttons":
            return self.get_button_action()
        return None

    def select_column_from_available(self) -> None:
        """Select a column from available list for movement"""
        if not self.available_columns:
            return

        idx = self.available_selection
        if 0 <= idx < len(self.available_columns):
            column = self.available_columns[idx]
            if self.selected_column == column:
                # Deselect if already selected
                self.selected_column = None
            else:
                # Select this column
                self.selected_column = column

    def select_column_from_selected(self) -> None:
        """Select a column from selected list for movement"""
        if not self.selected_columns:
            return

        idx = self.selected_selection
        if 0 <= idx < len(self.selected_columns):
            column = self.selected_columns[idx]
            if self.selected_column == column:
                # Deselect if already selected
                self.selected_column = None
            else:
                # Select this column
                self.selected_column = column

    def get_button_action(self) -> str:
        """Get the current button action"""
        actions = ["ok", "cancel", "reset"]
        return actions[self.button_selection]

    def move_selection(self, delta: int) -> None:
        """Move selection up or down in current pane, or move selected column"""
        # If we have a selected column, move it instead of changing selection
        if self.selected_column:
            self.move_selected_column(delta)
            return

        # Otherwise, move the selection cursor
        if self.focus == "available":
            if self.available_columns:
                self.available_selection = max(
                    0,
                    min(
                        len(self.available_columns) - 1,
                        self.available_selection + delta,
                    ),
                )
        elif self.focus == "selected":
            if self.selected_columns:
                self.selected_selection = max(
                    0,
                    min(
                        len(self.selected_columns) - 1,
                        self.selected_selection + delta,
                    ),
                )
        elif self.focus == "buttons":
            self.button_selection = max(0, min(2, self.button_selection + delta))

    def move_selected_column(self, delta: int) -> None:
        """Move the currently selected column up or down"""
        if not self.selected_column:
            return

        column = self.selected_column

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
