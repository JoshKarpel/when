import re
from dataclasses import dataclass
from difflib import get_close_matches
from textwrap import dedent
from typing import List, Optional, Sequence, Set, Tuple

import pendulum
import pendulum.tz.timezone
from humanize import precisedelta
from pendulum import UTC
from pytzdata import get_timezones
from rich.box import ROUNDED
from rich.console import Console, ConsoleRenderable, RenderableType
from rich.table import Column, Table
from rich.text import Text
from typer import Argument, Exit, Option, Typer

from when.constants import PACKAGE_NAME, __version__
from when.utils import partition

app = Typer(
    help=dedent(
        f"""\
        Display detailed information about a time.
        """
    ),
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        print(f"{PACKAGE_NAME} {__version__}")
        raise Exit()


@app.command()
def when(
    t: str = Argument(
        None,
        help=dedent(
            """\
            The time to display information about.
            """
        ),
    ),
    timezones: List[str] = Option(
        [],
        "--timezone",
        "-z",
        help=dedent(
            """\
            Add a timezone to convert to.
            Pass this option multiple times to add multiple timezones.
            """
        ),
    ),
    add_utc: bool = Option(
        True,
        help=dedent(
            """\
            Whether to implicitly include UTC in the output.
            """
        ),
    ),
    add_local: bool = Option(
        True,
        help=dedent(
            """\
            Whether to implicitly include the local timezone in the output.
            """
        ),
    ),
    version: Optional[bool] = Option(None, "--version", callback=version_callback),
) -> None:
    """ """
    console = Console()

    now = pendulum.now()
    target = parse_t(t) or now

    available_timezones = set(get_timezones())
    good_timezones, bad_timezones = partition(timezones, lambda tz: tz in available_timezones)
    display_bad_timezone_help(console, available_timezones, bad_timezones)

    display_timezones = {pendulum.timezone(tz) for tz in good_timezones}  # type: ignore[operator]
    if add_utc:
        display_timezones.add(UTC)
    if add_local:
        display_timezones.add(pendulum.local_timezone())  # type: ignore[operator]

    rich_time = RichTime(
        target=target,
        now=now,
        timezones=sorted(display_timezones, key=lambda tz: tz.utcoffset(now), reverse=True),
    )

    console.print(rich_time)


def display_bad_timezone_help(
    console: Console,
    available_timezones: Set[str],
    bad_timezones: Sequence[str],
) -> None:
    if not bad_timezones:
        return

    msg = Text(style="red")
    for tz in bad_timezones:
        msg.append(f"Unknown timezone ").append(tz, style="bold").append(".")
        nearby_timezones = get_close_matches(tz, available_timezones)
        if nearby_timezones:
            msg.append(" Maybe you meant:")
            for match in nearby_timezones:
                msg.append(f"\n  {match}")

        msg.append("\n")

    console.print(msg)


EPOCH_SECONDS = re.compile(r"\d{1,10}(\.\d+)?")
EPOCH_MILLISECONDS = re.compile(r"\d{13}")
EPOCH_MICROSECONDS = re.compile(r"\d{16}")


def parse_t(t: Optional[str]) -> Optional[pendulum.DateTime]:
    if not t:
        return None
    elif EPOCH_SECONDS.fullmatch(t):
        return pendulum.from_timestamp(float(t))
    elif EPOCH_MILLISECONDS.fullmatch(t):
        return pendulum.from_timestamp(float(t) / 1e3)
    elif EPOCH_MICROSECONDS.fullmatch(t):
        return pendulum.from_timestamp(float(t) / 1e6)
    else:
        parsed = pendulum.parse(t)
        if not isinstance(parsed, pendulum.DateTime):
            raise Exception("nope")
        return parsed


@dataclass(frozen=True)
class RichTime:
    target: pendulum.DateTime
    now: pendulum.DateTime
    timezones: List[pendulum.tz._Timezone]

    def __rich__(self) -> ConsoleRenderable:
        metadata = Table(box=ROUNDED, show_header=False)
        diff = self.now.diff(self.target, abs=False)
        if self.target != self.now:
            metadata.add_row(
                "Relative to Now",
                f"{precisedelta(int(diff.total_seconds()))} {'ago' if diff.total_seconds() < 0 else 'from now'}",
            )
        metadata.add_row("Epoch Timestamp (s)", f"{self.target.timestamp()}")
        metadata.add_row("Epoch Timestamp (ms)", f"{int(self.target.timestamp() * 1e3)}")
        metadata.add_row("Epoch Timestamp (µs)", f"{int(self.target.timestamp() * 1e6)}")

        if self.target == self.now:
            columns = [
                Column("Timezone"),
                Column("Now"),
            ]
            rows: List[Tuple[RenderableType, ...]] = [
                (
                    timezone.name,
                    str(self.now.astimezone(timezone).to_datetime_string()),
                )
                for timezone in self.timezones
            ]
        else:
            columns = [
                Column("Timezone"),
                Column("Target"),
                Column("Now"),
            ]
            rows = [
                (
                    timezone.name,
                    str(self.target.astimezone(timezone).to_datetime_string()),
                    str(self.now.astimezone(timezone).to_datetime_string()),
                )
                for timezone in self.timezones
            ]

        by_timezone = Table(*columns, box=ROUNDED)
        for row in rows:
            by_timezone.add_row(*row)

        wrapper = Table.grid(padding=2)
        wrapper.add_row(by_timezone, metadata)

        return wrapper
