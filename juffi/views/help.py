"""Handles help mode drawing"""

import curses

from juffi.helpers.curses_utils import Color, Position
from juffi.models.juffi_model import JuffiState
from juffi.output_controller import Window


class HelpMode:
    """Handles help mode input and drawing logic"""

    def __init__(self, state: JuffiState) -> None:
        self._state = state
        self._scroll_offset = 0

    def enter_mode(self) -> None:
        """Called when entering help mode"""
        self._scroll_offset = 0

    def handle_input(self, key: int) -> None:
        """Handle input for help mode. Returns True if key was handled."""
        if key == curses.KEY_UP:
            self._scroll_offset = max(0, self._scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            self._scroll_offset += 1

    def draw(self, stdscr: Window) -> None:
        """Draw help screen"""
        height, width = self._state.terminal_size

        help_text = [
            "JSON LOG VIEWER - HELP",
            "",
            "Use ↑/↓ to scroll",
            "",
            "Navigation:",
            "  ↑         - Move up",
            "  ↓         - Move down",
            "  PgUp      - Page up",
            "  PgDn      - Page down",
            "  Home      - Go to top",
            "  End       - Go to bottom",
            "  g         - Go to specific row",
            "",
            "Column Operations:",
            "  ←/→       - Scroll columns left/right",
            "  s         - Sort by current column",
            "  S         - Reverse sort by current column",
            "  </>       - Move column left/right",
            "  w/W       - Decrease/increase column width",
            "  m         - Column management screen",
            "",
            "Filtering & Search:",
            "  /         - Search all fields",
            "  f         - Filter by column",
            "  c         - Clear all filters",
            "  n/N       - Next/previous search result",
            "",
            "View Options:",
            "  d         - Toggle details view for current entry",
            "",
            "Details Mode Navigation:",
            "  ↑/↓       - Navigate between fields",
            "  ←/→       - Navigate between entries",
            "  Enter     - Toggle fullscreen view of current field",
            "",
            "Fullscreen Mode (in Details):",
            "  ↑/↓       - Scroll by line",
            "  PgUp/PgDn - Scroll by page",
            "  Enter/Esc - Exit fullscreen",
            "",
            "File Operations:",
            "  F         - Toggle follow mode",
            "  r         - Refresh/reload",
            "  R         - Reset view (clear filters, sort)",
            "",
            "Other:",
            "  h/?       - Toggle this help",
            "  q/Esc     - Quit",
            "",
            "Press any key to continue...",
        ]

        max_scroll = max(0, len(help_text) - height)
        self._scroll_offset = max(0, min(self._scroll_offset, max_scroll))

        stdscr.clear()

        x_pos = max(0, width // 4)
        visible_lines = min(height, len(help_text) - self._scroll_offset)

        for i in range(visible_lines):
            text_index = self._scroll_offset + i
            if text_index < len(help_text):
                line = help_text[text_index]
                color = Color.HEADER if text_index == 0 else Color.DEFAULT
                stdscr.addstr(Position(i, x_pos), line, color=color)

        stdscr.refresh()
