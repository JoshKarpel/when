import pendulum
import pytest
from pendulum import UTC

from when.main import parse_t


@pytest.mark.parametrize(
    "t, expected",
    [
        (None, None),
        ("", None),
        ("0", pendulum.DateTime(year=1970, month=1, day=1, tzinfo=UTC)),
        (  # epoch seconds with fraction
            "1645478952.985869",
            pendulum.DateTime(
                year=2022,
                month=2,
                day=21,
                hour=21,
                minute=29,
                second=12,
                microsecond=985869,
                tzinfo=UTC,
            ),
        ),
        (  # epoch seconds with fraction
            "1645478952.985",
            pendulum.DateTime(
                year=2022,
                month=2,
                day=21,
                hour=21,
                minute=29,
                second=12,
                microsecond=985000,
                tzinfo=UTC,
            ),
        ),
        (  # epoch seconds
            "1645478952",
            pendulum.DateTime(
                year=2022,
                month=2,
                day=21,
                hour=21,
                minute=29,
                second=12,
                microsecond=0,
                tzinfo=UTC,
            ),
        ),
        (  # epoch milliseconds
            "1645478952985",
            pendulum.DateTime(
                year=2022,
                month=2,
                day=21,
                hour=21,
                minute=29,
                second=12,
                microsecond=985000,
                tzinfo=UTC,
            ),
        ),
        (  # epoch microseconds
            "1645478952985869",
            pendulum.DateTime(
                year=2022,
                month=2,
                day=21,
                hour=21,
                minute=29,
                second=12,
                microsecond=985869,
                tzinfo=UTC,
            ),
        ),
    ],
)
def test_parse_t(t: str, expected: pendulum.DateTime) -> None:
    assert parse_t(t) == expected
