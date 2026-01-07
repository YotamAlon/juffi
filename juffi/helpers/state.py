"""Helper class for tracking changes to attributes."""

import collections
from typing import Any, Callable, Generic, TypeVar, overload

from juffi.helpers.indexed_dict import IndexedDict

_MISSING = object()
T = TypeVar("T")


_MUTATING_METHODS: dict[type, set[str]] = {
    list: {
        "__setitem__",
        "__delitem__",
        "append",
        "extend",
        "insert",
        "remove",
        "pop",
        "clear",
        "sort",
        "reverse",
    },
    dict: {
        "__setitem__",
        "__delitem__",
        "clear",
        "pop",
        "popitem",
        "setdefault",
        "update",
    },
    set: {
        "add",
        "discard",
        "remove",
        "pop",
        "clear",
        "update",
        "intersection_update",
        "difference_update",
        "symmetric_difference_update",
    },
}

_MUTATING_METHODS[IndexedDict] = _MUTATING_METHODS[dict]


class Observable(Generic[T]):
    """Generic wrapper that notifies on mutations to wrapped data"""

    def __init__(self, data: T, on_change: Callable[[], None]) -> None:
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_on_change", on_change)
        mutating_methods = _MUTATING_METHODS.get(type(data), set())
        object.__setattr__(self, "_mutating_methods", mutating_methods)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._data, name)
        if name in self._mutating_methods and callable(attr):

            def wrapper(*args: Any, **kwargs: Any) -> Any:
                result = attr(*args, **kwargs)
                self._on_change()
                return result

            return wrapper
        return attr

    def __getitem__(self, key: Any) -> Any:
        result = self._data[key]
        if isinstance(key, slice) and isinstance(self._data, list):
            return Observable(result, self._on_change)
        return result

    def __setitem__(self, key: Any, value: Any) -> None:
        self._data[key] = value
        self._on_change()

    def __delitem__(self, key: Any) -> None:
        del self._data[key]
        self._on_change()

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Any:
        return iter(self._data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Observable):
            return self._data == other._data
        return self._data == other

    def __str__(self) -> str:
        return str(self._data)

    def __repr__(self) -> str:
        return f"Observable({repr(self._data)})"


class Field(Generic[T]):
    """Descriptor for state fields that automatically tracks changes

    Handles both mutable collections (list, dict, set) and immutable values.
    For mutable collections, wraps them in Observable wrappers and returns copies.
    For immutable values, stores them directly without wrapping or copying.
    """

    def __init__(self, default: T | Callable[[], T]) -> None:
        if callable(default):
            self.default_factory: Callable[[], T] = default
            self.default_value = None
            self.is_factory = True
        else:
            self.default_factory = lambda: default
            self.default_value = default
            self.is_factory = False
        self.name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __class_getitem__(cls, item: type) -> type:
        """Support Field[T] syntax for type annotations"""
        return cls

    @overload
    def __get__(self, instance: None, owner: type) -> "Field[T]": ...

    @overload
    def __get__(self, instance: object, owner: type) -> T: ...

    def __get__(self, instance: object | None, owner: type) -> "Field[T] | T":
        if instance is None:
            return self
        private_name = f"_{self.name}"
        if not hasattr(instance, private_name):
            value = self.default_factory()
            wrapped = self._wrap_if_mutable(instance, value)
            object.__setattr__(instance, private_name, wrapped)
        return getattr(instance, private_name)

    def __set__(self, instance: object, value: T) -> None:
        private_name = f"_{self.name}"
        old_value = getattr(instance, private_name, _MISSING)
        wrapped = self._wrap_if_mutable(instance, value)
        object.__setattr__(instance, private_name, wrapped)
        if isinstance(instance, State) and old_value != value:
            instance._changed(self.name)

    def _wrap_if_mutable(self, instance: object, value: T) -> T:
        """Wrap mutable types in observable wrappers"""
        if not isinstance(instance, State):
            return value

        def on_change() -> None:
            instance._changed(self.name)  # pylint: disable=protected-access

        if isinstance(value, Observable):
            return value

        if isinstance(value, (list, dict, set, IndexedDict)):
            return Observable(value, on_change)  # type: ignore

        return value


class State:
    """A simple state dataclass that tracks changes to its attributes."""

    _CHANGES: set[str] = set()
    _WATCHERS: dict[str, list[Callable[[], None]]] = collections.defaultdict(list)

    def __init__(self) -> None:
        """Initialize all Field descriptors by accessing them"""
        for name in dir(type(self)):
            attr = getattr(type(self), name)
            if isinstance(attr, Field):
                _ = getattr(self, name)
        self.clear_changes()

    def __setattr__(self, name: str, value: Any) -> None:
        """Override setattr to track changes to public attributes."""
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        cls_attr = getattr(type(self), name, None)
        is_field_descriptor = isinstance(cls_attr, Field)

        if is_field_descriptor:
            super().__setattr__(name, value)
        else:
            old_value = getattr(self, name, _MISSING)
            super().__setattr__(name, value)
            if old_value != value:
                self._changed(name)

    def _changed(self, name: str) -> None:
        self._CHANGES.add(name)
        self._notify_watchers(name)

    @property
    def changes(self) -> set[str]:
        """Get the list of attribute names that have changed."""
        return self._CHANGES.copy()

    def clear_changes(self) -> None:
        """Clear the changes list."""
        self._CHANGES.clear()

    def register_watcher(self, name: str, callback: Callable[[], None]) -> None:
        """Register a callback to be notified when an attribute changes"""
        self._WATCHERS[name].append(callback)

    def _notify_watchers(self, name: str) -> None:
        """Notify watchers of a change"""
        for callback in self._WATCHERS[name]:
            callback()
