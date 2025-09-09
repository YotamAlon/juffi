"""Indexed dictionary implementation"""

from itertools import islice
from typing import Any, OrderedDict, TypeVar

V = TypeVar("V")


class IndexedDict(OrderedDict[str, V]):
    """Ordered Dictionary that can access values by index"""

    def __getitem__(self, key: int | str | slice) -> Any:
        """Get the value of the key"""
        if isinstance(key, slice):
            return islice(self.values(), key.start, key.stop, key.step)
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

    def index(self, key: str) -> int:
        """Get the index of the key"""
        for i, k in enumerate(self.keys()):
            if k == key:
                return i
        raise KeyError(key)

    def copy(self) -> "IndexedDict[V]":
        """Copy the dictionary"""
        return IndexedDict[V](super().copy())
