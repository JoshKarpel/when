import re
from dataclasses import dataclass
from textwrap import dedent
from typing import List, Optional, Tuple

import pendulum
import pendulum.tz.timezone
from humanize import precisedelta
from pendulum import UTC
from rich.box import ROUNDED
from rich.console import Console, ConsoleRenderable, RenderableType
from rich.table import Column, Table
from typer import Argument, Typer

app = Typer(
    help=dedent(
        f"""\
        Display detailed information about a time.
        """
    ),
    no_args_is_help=True,
)


@app.command()
def when(
    t: str = Argument(
        None,
        help=dedent(
            """\
            The time to display information about.
            """
        ),
    )
) -> None:
    """ """
    console = Console()

    now = pendulum.now()
    target = parse_t(t) or now

    timezones = [UTC, pendulum.local_timezone()]  # type: ignore[operator]

    rich_time = RichTime(target=target, now=now, timezones=timezones)

    console.print(rich_time)


EPOCH_SECONDS = re.compile(r"\d{,10}(\.\d+)?")
EPOCH_MILLISECONDS = re.compile(r"\d{13}")
EPOCH_MICROSECONDS = re.compile(r"\d{16}")


def parse_t(t: Optional[str]) -> Optional[pendulum.DateTime]:
    if not t:
        return None
    elif EPOCH_SECONDS.match(t):
        return pendulum.from_timestamp(float(t))
    elif EPOCH_MILLISECONDS.match(t):
        return pendulum.from_timestamp(float(t) / 1e3)
    elif EPOCH_MICROSECONDS.match(t):
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
        metadata.add_row("Epoch Timestamp (ms)", f"{int(self.target.timestamp() * 1000)}")

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
