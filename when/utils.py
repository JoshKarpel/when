from typing import Callable, Iterable, List, Tuple, TypeVar

T = TypeVar("T")


def partition(it: Iterable[T], is_left: Callable[[T], bool]) -> Tuple[List[T], List[T]]:
    left = []
    right = []

    for item in it:
        if is_left(item):
            left.append(item)
        else:
            right.append(item)

    return left, right
