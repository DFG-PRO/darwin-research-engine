"""Command-line interface for Darwin."""

from __future__ import annotations

import typer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from darwin.config import get_settings
from darwin.db import get_engine, session_scope
from darwin.logging import configure_logging
from darwin.research import ResearchService, ResearchServiceError

app = typer.Typer(
    name="darwin",
    help="Darwin Research & Intelligence Engine foundation CLI.",
    no_args_is_help=True,
)
research_app = typer.Typer(help="Research run persistence smoke commands.")


@app.callback()
def callback() -> None:
    """Initialize CLI process state."""

    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def status() -> None:
    """Show application foundation status."""

    settings = get_settings()
    typer.echo(f"Darwin status: ok")
    typer.echo(f"Environment: {settings.env}")


@app.command("db-status")
def db_status() -> None:
    """Check database connectivity without mutating data."""

    settings = get_settings()
    try:
        with get_engine(settings).connect() as connection:
            connection.execute(text("select 1"))
    except SQLAlchemyError as exc:
        typer.echo(f"Database status: unavailable ({exc.__class__.__name__})")
        raise typer.Exit(code=1) from exc

    typer.echo("Database status: ok")


@research_app.command("create-run")
def create_research_run(
    title: str = typer.Argument(..., help="Research question or run title."),
    public_id: str | None = typer.Option(None, help="Optional external research run identifier."),
) -> None:
    """Create a persisted research run."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            research_run = ResearchService(session).create_research_run(
                title=title,
                public_id=public_id,
                research_method_version=settings.research_method_version,
                darwin_version=settings.darwin_version,
            )
            typer.echo(f"Research run created: {research_run.public_id}")
            typer.echo(f"Database id: {research_run.id}")
            typer.echo(f"Status: {research_run.status.value}")
    except (ResearchServiceError, SQLAlchemyError) as exc:
        typer.echo(f"Research command failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("get-run")
def get_research_run(identifier: str = typer.Argument(..., help="Research run UUID or public ID.")) -> None:
    """Inspect a persisted research run."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            record = ResearchService(session).get_research_record(identifier)
            typer.echo(f"Research run: {record.research_run.public_id}")
            typer.echo(f"Title: {record.research_run.title}")
            typer.echo(f"Status: {record.research_run.status.value}")
            typer.echo(f"Sources: {len(record.sources)}")
            typer.echo(f"Evidence: {len(record.evidence)}")
            typer.echo(f"Claims: {len(record.claims)}")
            typer.echo(f"Claim/evidence links: {len(record.claim_evidence)}")
            typer.echo(f"Conclusions: {len(record.conclusions)}")
    except (ResearchServiceError, SQLAlchemyError) as exc:
        typer.echo(f"Research command failed: {exc}")
        raise typer.Exit(code=1) from exc


app.add_typer(research_app, name="research")


def main() -> None:
    """CLI entry point."""

    app()


if __name__ == "__main__":
    main()
