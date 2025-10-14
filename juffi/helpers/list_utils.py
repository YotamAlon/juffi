"""List utility functions"""

from typing import Callable, TypeVar, overload

T = TypeVar("T")


@overload
def find_first_index(
    iterable: list[T], predicate: Callable[[T], bool], default: int
) -> int: ...


@overload
def find_first_index(
    iterable: list[T], predicate: Callable[[T], bool], default: None = None
) -> int | None: ...


def find_first_index(
    iterable: list[T], predicate: Callable[[T], bool], default: int | None = None
) -> int | None:
    """Find the index of the first item in the iterable that matches the predicate"""
    for i, item in enumerate(iterable):
        if predicate(item):
            return i
    return default
