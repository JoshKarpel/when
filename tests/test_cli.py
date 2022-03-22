import subprocess
import sys

from pendulum.parsing import ParserError
from typer.testing import CliRunner

from when.constants import PACKAGE_NAME, __version__
from when.main import app


def test_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0


def test_help_via_main() -> None:
    result = subprocess.run([sys.executable, "-m", PACKAGE_NAME, "--help"])

    assert result.returncode == 0


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--version"])

    assert __version__ in result.stdout
    assert result.exit_code == 0


def test_parse_error(runner: CliRunner) -> None:
    result = runner.invoke(app, ["not a time"])

    assert result.exit_code == 1
    assert "not a time" in result.stderr
    assert ParserError.__name__ not in result.stderr
