from typing import Callable, TypeVar

T = TypeVar("T")


def find_first_index(iterable: list[T], predicate: Callable[[T], bool]) -> int | None:
    """Find the index of the first item in the iterable that matches the predicate"""
    for i, item in enumerate(iterable):
        if predicate(item):
            return i
    return None
