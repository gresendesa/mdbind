from typer.testing import CliRunner

from mdbind import __version__
from mdbind.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"mdb version {__version__}" in result.output
