import re
from dataclasses import dataclass
from difflib import get_close_matches
from math import cos, pi, sin
from textwrap import dedent
from time import sleep
from typing import List, Optional, Sequence, Set, Tuple

import pendulum
import pendulum.tz.timezone
from humanize import precisedelta
from pendulum import UTC
from pendulum.parsing import ParserError
from pytzdata import get_timezones
from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console, ConsoleOptions, ConsoleRenderable, RenderableType, RenderResult
from rich.live import Live
from rich.style import Style
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
    clock: bool = Option(
        False,
        help=dedent(
            """\
            Display an animated clock showing current local time instead of the normal output.
            """
        ),
    ),
    version: Optional[bool] = Option(
        None,
        "--version",
        callback=version_callback,
        help=dedent(
            """\
            Display version information, then exit.
            """
        ),
    ),
) -> None:
    stdout = Console()
    stderr = Console(stderr=True)

    now = pendulum.now()

    if clock:
        with Live(
            renderable=Clock(target=pendulum.now()), console=stdout, auto_refresh=True, screen=True
        ) as live:
            while True:
                live.update(Clock(target=pendulum.now()))
                sleep(0.1)
    else:
        try:
            target = parse_t(t) or now
        except ParserError as e:
            stderr.print(Text(str(e), style="red"))
            raise Exit(1)

        available_timezones = set(get_timezones())
        good_timezones, bad_timezones = partition(timezones, lambda tz: tz in available_timezones)
        display_bad_timezone_help(stdout, available_timezones, bad_timezones)

        display_timezones = {pendulum.timezone(tz) for tz in good_timezones}  # type: ignore
        if add_utc:
            display_timezones.add(UTC)
        if add_local:
            display_timezones.add(pendulum.local_timezone())  # type: ignore

        rich_time = RichTime(
            target=target,
            now=now,
            timezones=sorted(display_timezones, key=lambda tz: tz.utcoffset(now), reverse=True),
        )

        stdout.print(rich_time)


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


TAU = 2 * pi


@dataclass(frozen=True)
class Clock:
    target: pendulum.DateTime

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        size = options.max_height - 2
        clock = [[Text(" ") for _ in range(size * 2)] + [Text("\n")] for _ in range(size)]

        center = size // 2
        radius = center

        clock[center][center * 2] = Text("✵", style=Style(color="white", bold=True))

        for sixtieth in range(1, 61):
            theta = fraction_to_clock_angle(sixtieth / 60)
            x = round(cos(theta) * radius) + center
            y = round(sin(theta) * radius) + center

            if sixtieth % 5 == 0:
                texts = [Text(c, style=Style(color="white")) for c in str(sixtieth // 5)]
                clock[y][x * 2 : x * 2 + len(texts)] = texts
            else:
                clock[y][x * 2] = Text(".", style=Style(color="white"))

        draw_hand(
            clock,
            center,
            radius,
            fraction_to_clock_angle(
                (self.target.hour + self.target.minute / 60 + self.target.second / 3600) % 12 / 12
            ),
            Style(color="#7570b3"),
            "H",
        )
        draw_hand(
            clock,
            center,
            radius,
            fraction_to_clock_angle((self.target.minute + self.target.second / 60) / 60),
            Style(color="#d95f02"),
            "M",
        )
        draw_hand(
            clock,
            center,
            radius,
            fraction_to_clock_angle(self.target.second / 60),
            Style(color="#1b9e77"),
            "S",
        )

        yield Align.center(
            Text.assemble(*(row for row in (Text.assemble(*x) for x in clock))),
            vertical="middle",
        )


def fraction_to_clock_angle(frac: float) -> float:
    return (frac * TAU) - TAU / 4


def draw_hand(
    clock: List[List[Text]], center: int, radius: int, theta: float, style: Style, last: str
) -> None:
    second_x = round(cos(theta) * radius) + center
    second_y = round(sin(theta) * radius) + center
    dx = abs(center - second_x)
    dy = abs(center - second_y)

    if dx > dy:
        start, stop = sorted((center, second_x))
        slope = (second_y - center) / (second_x - center)
        for x in range(start, stop):
            y = round(slope * (x - center)) + center
            if (x, y) == (center, center):
                continue
            clock[y][x * 2] = Text(".", style=style)
    else:
        start, stop = sorted((center, second_y))
        if second_x != center:
            slope = (second_y - center) / (second_x - center)
            for y in range(start, stop):
                x = round((y - center) / slope) + center
                if (x, y) == (center, center):
                    continue
                clock[y][x * 2] = Text(".", style=style)
        else:
            for y in range(start, stop):
                if (center, y) == (center, center):
                    continue
                clock[y][center * 2] = Text(".", style=style)

    clock[second_y][second_x * 2] = Text(last, style=Style.chain(style, Style(bold=True)))
