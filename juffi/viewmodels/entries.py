from typing import Callable

from juffi.models.juffi_model import JuffiState


class EntriesModel:
    """ViewModel class for the entries window"""

    def __init__(self, state: JuffiState, needs_redraw: Callable[[], None]) -> None:
        self._state = state
        for field in [
            "current_mode",
            "terminal_size",
            "num_entries",
            "current_row",
            "current_column",
            "sort_column",
            "sort_reverse",
            "filters_count",
            "search_term",
            "columns",
            "filtered_entries",
        ]:
            self._state.register_watcher(field, needs_redraw)
