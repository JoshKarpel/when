from typing import Callable, Iterable

from hypothesis import given
from hypothesis import strategies as st

from when.utils import partition


class TestPartition:
    g = given(
        items=st.iterables(st.integers()),
        is_left=st.functions(like=lambda x: None, returns=st.booleans(), pure=True),
    )

    @g
    def test_left_items_are_left(
        self, items: Iterable[int], is_left: Callable[[int], bool]
    ) -> None:
        left, right = partition(items, is_left)
        assert all(is_left(l) for l in left)

    @g
    def test_right_items_are_not_left(
        self, items: Iterable[int], is_left: Callable[[int], bool]
    ) -> None:
        left, right = partition(items, is_left)
        assert all(not is_left(r) for r in right)

    @g
    def test_can_combine_partitions_back_into_original(
        self, items: Iterable[int], is_left: Callable[[int], bool]
    ) -> None:
        items = list(items)

        left, right = partition(items, is_left)

        assert sorted(left + right) == sorted(items)
