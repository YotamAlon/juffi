import curses

from juffi.helpers.curses_utils import get_curses_yx


class HelpMode:
    """Handles help mode input and drawing logic"""

    def __init__(
        self,
        colors: dict[str, int],
    ) -> None:
        self._colors = colors

    def handle_input(self, _: int) -> None:
        """Handle input for help mode. Returns True if key was handled."""
        return

    def draw(self, stdscr: curses.window) -> None:
        """Draw help screen"""
        height, width = get_curses_yx()

        help_text = [
            "JSON LOG VIEWER - HELP",
            "",
            "Navigation:",
            "  ↑         - Move up",
            "  ↓         - Move down",
            "  PgUp      - Page up",
            "  PgDn      - Page down",
            "  Home      - Go to top",
            "  End       - Go to bottom",
            "  g         - Go to specific line",
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

        stdscr.clear()

        start_row = max(0, (height - len(help_text)) // 2)
        x_pos = max(0, width // 4)
        for i, line in enumerate(help_text):
            if start_row + i < height - 1:
                color = self._colors["HEADER"] if i == 0 else self._colors["DEFAULT"]
                stdscr.addstr(start_row + i, x_pos, line, color)

        stdscr.refresh()
