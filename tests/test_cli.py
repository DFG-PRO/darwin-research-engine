from typer.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from darwin.cli.app import app
from darwin.config import get_settings
from darwin.db import Base
from darwin.research import ResearchService


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


def test_research_cli_help() -> None:
    result = CliRunner().invoke(app, ["research", "--help"])

    assert result.exit_code == 0
    assert "Research run persistence smoke commands" in result.stdout
    assert "create-run" in result.stdout
    assert "get-run" in result.stdout
    assert "validate-claim" in result.stdout
    assert "run-manual" in result.stdout
    assert "acquire" in result.stdout


def test_research_acquire_cli_fake_provider(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        research_run = ResearchService(session).create_research_run(
            title="CLI acquisition run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        session.commit()
        research_run_id = str(research_run.id)

    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    monkeypatch.setenv("DARWIN_EXTERNAL_SEARCH_PROVIDER", "fake")
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(
            app,
            [
                "research",
                "acquire",
                "CLI source discovery",
                "--research-run-id",
                research_run_id,
                "--provider",
                "fake",
            ],
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Status: SUCCESS" in result.stdout
    assert "Provider: fake" in result.stdout
    assert "Candidates discovered: 1" in result.stdout
    assert "Sources registered: 1" in result.stdout
