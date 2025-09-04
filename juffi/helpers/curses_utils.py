import curses


DEL = 127

ESC = 27


def get_curses_yx() -> tuple[int, int]:
    """Get the current terminal size"""
    return curses.LINES, curses.COLS  # pylint: disable=no-member
