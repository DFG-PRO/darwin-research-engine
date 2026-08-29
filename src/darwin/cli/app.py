"""Command-line interface for Darwin."""

from __future__ import annotations

import typer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from darwin.config import get_settings
from darwin.db import get_engine
from darwin.logging import configure_logging

app = typer.Typer(
    name="darwin",
    help="Darwin Research & Intelligence Engine foundation CLI.",
    no_args_is_help=True,
)


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


def main() -> None:
    """CLI entry point."""

    app()


if __name__ == "__main__":
    main()
