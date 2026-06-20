from typer.testing import CliRunner
from htdp.cli import app

runner = CliRunner()


def test_cli_lists_all_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("synth", "validate", "process", "qc", "package", "replay"):
        assert cmd in result.stdout
