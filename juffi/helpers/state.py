import collections
from typing import Callable, Any

_MISSING = object()


class State:
    """A simple state dataclass that tracks changes to its attributes."""

    _CHANGES: set[str] = set()
    _WATCHERS: dict[str, list[Callable[[], None]]] = collections.defaultdict(list)

    def __setattr__(self, name: str, value: Any) -> None:
        """Override setattr to track changes to public attributes."""
        # Only track changes for public attributes (not starting with _)
        old_value = getattr(self, name, _MISSING)
        super().__setattr__(name, value)
        if not name.startswith("_") and old_value != value:
            self._changed(name)

    def _changed(self, name):
        self._CHANGES.add(name)
        self._notify_watchers(name)

    @property
    def changes(self) -> set[str]:
        """Get the list of attribute names that have changed."""
        return self._CHANGES.copy()

    def clear_changes(self) -> None:
        """Clear the changes list."""
        self._CHANGES.clear()

    def register_watcher(self, name: str, callback: Callable[[], None]):
        """Register a callback to be notified when an attribute changes"""
        self._WATCHERS[name].append(callback)

    def _notify_watchers(self, name: str) -> None:
        """Notify watchers of a change"""
        for callback in self._WATCHERS[name]:
            callback()
