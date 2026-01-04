"""Utilities for working with screen data"""

import functools

from juffi.helpers.list_utils import find_first
from tests.infra.terminal_parser import Char, CharType


class ScreenData:
    """Wrapper for screen data that provides text search and color checking"""

    def __init__(self):
        self._screen = []
        self._regular_chars = []
        self._screen_bytes = b""
        self._screen_text = b""

    def append(self, char: Char) -> None:
        """Append a character to the screen"""
        self._screen.append(char)
        self._screen_bytes += char.value
        if char.type == CharType.REGULAR:
            self._regular_chars.append(char)
            self._screen_text += char.value

    @property
    def text(self) -> str:
        """Get the plain text representation"""
        return self._screen_text.decode()

    @property
    def data(self) -> bytes:
        """Get the full binary data including ANSI codes"""
        return self._screen_bytes

    def __contains__(self, text: str) -> bool:
        """Check if text exists in the screen (for backward compatibility)"""
        return text in self.text

    def __str__(self) -> str:
        """Return the plain text representation"""
        return self.text

    def startswith(self, prefix: str) -> bool:
        """Check if the text starts with the given prefix"""
        return self.text.startswith(prefix)

    def split(self, sep: str | None = None) -> list[str]:
        """Split the text by the given separator"""
        return self.text.split(sep)

    def _find_all_text_indices(self, text: str) -> list[int]:
        indices = []
        next_index = -1
        data = self.data
        text_bytes = text.encode()

        while (next_index := data.find(text_bytes, next_index + 1)) != -1:
            screen_index = self._byte_to_index_map.get(next_index)
            if screen_index is not None:
                indices.append(screen_index)

        return indices

    @functools.cached_property
    def _byte_to_index_map(self) -> dict[int, int]:
        """Build a lookup table for byte position to screen index"""
        result = {}
        current_byte_pos = 0
        for i, char in enumerate(self._screen):
            result[current_byte_pos] = i
            current_byte_pos += len(char.value)
        return result

    def is_selected(self, text: str) -> bool:
        """Check if the text is selected (magenta color)"""
        if text not in self.text:
            return False

        indices = self._find_all_text_indices(text)
        if not indices:
            return False

        for idx in indices:
            color_char = find_first(
                reversed(self._screen[:idx]), lambda c: c.type == CharType.ANSI_COLOR
            )
            if color_char and b"35m" in color_char.value:
                return True

        return False
