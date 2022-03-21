from typing import Callable, Iterable, List, Tuple, TypeVar

T = TypeVar("T")


def partition(items: Iterable[T], is_left: Callable[[T], bool]) -> Tuple[List[T], List[T]]:
    left = []
    right = []

    for item in items:
        if is_left(item):
            left.append(item)
        else:
            right.append(item)

    return left, right
