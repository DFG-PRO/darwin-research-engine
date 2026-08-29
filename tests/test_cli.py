from typer.testing import CliRunner

from darwin.cli.app import app


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Darwin Research & Intelligence Engine" in result.stdout


def test_cli_status(monkeypatch) -> None:
    monkeypatch.setenv("DARWIN_ENV", "test")

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Darwin status: ok" in result.stdout
    assert "Environment: test" in result.stdout
