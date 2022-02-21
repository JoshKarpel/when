import subprocess
import sys
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockFixture
from typer.testing import CliRunner

from when.constants import PACKAGE_NAME, __version__
from when.main import app


def test_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0


def test_help_via_main() -> None:
    result = subprocess.run([sys.executable, "-m", PACKAGE_NAME, "--help"])

    assert result.returncode == 0
