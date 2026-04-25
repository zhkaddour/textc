"""Smoke test: `textc view --help` is registered and prints usage."""
from click.testing import CliRunner

from textc.cli import main


def test_view_help_is_registered():
    runner = CliRunner()
    result = runner.invoke(main, ["view", "--help"])
    assert result.exit_code == 0
    assert "Launch the browser-based textc viewer" in result.output
    assert "--port" in result.output
    assert "--no-browser" in result.output
