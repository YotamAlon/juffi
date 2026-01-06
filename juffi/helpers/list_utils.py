"""List utility functions"""

from typing import Any, Callable, Iterable, TypeGuard, TypeVar, overload

T = TypeVar("T")
S = TypeVar("S")


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


@overload
def find_first(
    iterable: Iterable[T], predicate: Callable[[T], TypeGuard[S]]
) -> S | None: ...


@overload
def find_first(iterable: Iterable[T], predicate: Callable[[T], bool]) -> T | None: ...


def find_first(iterable: Iterable[Any], predicate: Callable[[T], bool]) -> Any:
    """Find the first item in the iterable that matches the predicate"""
    for item in iterable:
        if predicate(item):
            return item
    return None
