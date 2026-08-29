"""Command-line interface for Darwin."""

from __future__ import annotations

import uuid
from pathlib import Path

import typer
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from darwin.acquisition import (
    AcquisitionConfigurationError,
    AcquisitionRequest,
    AcquisitionService,
    BraveSearchProvider,
    FakeResearchProvider,
)
from darwin.config import get_settings
from darwin.content import (
    EvidenceExtractionError,
    FakeSourceFetcher,
    HTTPSourceFetcher,
    SegmentExtractionRequest,
    SourceContentService,
    SourceFetchRequest,
    UnsupportedSourceLocator,
)
from darwin.db import get_engine, session_scope
from darwin.db.models import Source, SourceContentSnapshot, SourceType
from darwin.logging import configure_logging
from darwin.orchestration import ManualResearchInput, ResearchOrchestrationError, ResearchOrchestrator
from darwin.research import ResearchService, ResearchServiceError
from darwin.validation import ClaimValidationError, ClaimValidationService

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


@research_app.command("validate-claim")
def validate_claim(claim_id: str = typer.Argument(..., help="Claim UUID to validate structurally.")) -> None:
    """Validate a claim's structural evidentiary state."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            result = ClaimValidationService(session).evaluate_claim(claim_id)
            typer.echo(f"Claim: {result.claim_id}")
            typer.echo(f"Validation state: {result.validation_state.value}")
            typer.echo(f"Supporting evidence: {result.supporting_evidence_count}")
            typer.echo(f"Contradicting evidence: {result.contradicting_evidence_count}")
            typer.echo(f"Contextual evidence: {result.contextual_evidence_count}")
            typer.echo(f"Distinct sources: {result.distinct_source_count}")
            typer.echo(
                "Independent supporting sources: "
                f"{result.independent_supporting_source_count}"
            )
            typer.echo(f"Contradiction exists: {result.contradiction_exists}")
            typer.echo(f"Independent corroboration: {result.independent_corroboration_exists}")
            typer.echo(
                "Reasons: "
                + ", ".join(reason.value for reason in result.reason_codes)
            )
    except (ClaimValidationError, ResearchServiceError, SQLAlchemyError) as exc:
        typer.echo(f"Validation command failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("run-manual")
def run_manual_research(
    input_file: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
) -> None:
    """Run the deterministic manual research method from supplied JSON."""

    settings = get_settings()
    try:
        manual_input = ManualResearchInput.model_validate_json(input_file.read_text())
        with session_scope(settings) as session:
            result = ResearchOrchestrator(session, settings).run_manual(manual_input)
            typer.echo(result.model_dump_json(indent=2))
    except (OSError, ValidationError, ResearchOrchestrationError) as exc:
        typer.echo(f"Manual research input failed: {exc}")
        raise typer.Exit(code=1) from exc
    except (ClaimValidationError, ResearchServiceError, SQLAlchemyError) as exc:
        typer.echo(f"Manual research execution failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("acquire")
def acquire_sources(
    query: str = typer.Argument(..., help="Explicit external source discovery query."),
    research_run_id: str = typer.Option(..., help="Research run UUID for acquisition provenance."),
    provider: str | None = typer.Option(None, help="Provider override: fake or brave."),
    result_limit: int = typer.Option(10, min=1, max=50, help="Maximum source candidates."),
    domain: list[str] | None = typer.Option(None, help="Optional allowed domain constraint."),
) -> None:
    """Discover source candidates and register accepted Sources."""

    settings = get_settings()
    provider_name = provider or settings.external_search_provider
    if provider_name not in {"fake", "brave"}:
        typer.echo(f"Acquisition input failed: unknown provider {provider_name!r}")
        raise typer.Exit(code=1)
    try:
        request = AcquisitionRequest(
            research_run_id=research_run_id,
            query=query,
            domain_constraints=domain or [],
            requested_source_types=[SourceType.WEB_PAGE],
            result_limit=result_limit,
        )
        selected_provider = (
            BraveSearchProvider(settings)
            if provider_name == "brave"
            else FakeResearchProvider()
        )
        with session_scope(settings) as session:
            result = AcquisitionService(session, selected_provider).acquire(request)
            typer.echo(f"Acquisition: {result.acquisition_id}")
            typer.echo(f"Status: {result.status.value}")
            typer.echo(f"Provider: {result.provider_id}")
            typer.echo(f"Query: {result.query}")
            typer.echo(f"Candidates discovered: {result.candidate_count}")
            typer.echo(f"Sources registered: {result.registered_source_count}")
            if result.warnings:
                typer.echo("Warnings: " + ", ".join(result.warnings))
            if result.errors:
                typer.echo("Errors: " + ", ".join(result.errors))
    except (ValidationError, AcquisitionConfigurationError) as exc:
        typer.echo(f"Acquisition input failed: {exc}")
        raise typer.Exit(code=1) from exc
    except (ResearchServiceError, SQLAlchemyError) as exc:
        typer.echo(f"Acquisition command failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("fetch-source")
def fetch_source_content(
    source_id: str = typer.Argument(..., help="Registered Source UUID to fetch."),
    research_run_id: str = typer.Option(..., help="Research run UUID for snapshot provenance."),
    fetcher: str = typer.Option("http", help="Fetcher override: http or fake."),
) -> None:
    """Fetch registered Source content and persist a snapshot."""

    if fetcher not in {"http", "fake"}:
        typer.echo(f"Source fetch input failed: unknown fetcher {fetcher!r}")
        raise typer.Exit(code=1)
    settings = get_settings()
    try:
        fetch_request = SourceFetchRequest(research_run_id=research_run_id, source_id=source_id)
        with session_scope(settings) as session:
            source = session.get(Source, fetch_request.source_id)
            if source is None:
                typer.echo(f"Source fetch input failed: Source not found: {source_id}")
                raise typer.Exit(code=1)
            selected_fetcher = FakeSourceFetcher() if fetcher == "fake" else HTTPSourceFetcher(settings)
            result = SourceContentService(session, settings, selected_fetcher).fetch_source(
                fetch_request.model_copy(update={"canonical_locator": source.canonical_locator})
            )
            typer.echo(f"Source: {result.snapshot.source_id}")
            typer.echo(f"Fetch status: {result.snapshot.fetch_status.value}")
            typer.echo(f"Snapshot: {result.snapshot.id}")
            typer.echo(f"Content fingerprint: {result.snapshot.raw_content_fingerprint}")
            typer.echo(f"Segments: {len(result.segments)}")
            if result.snapshot.errors:
                typer.echo("Errors: " + ", ".join(result.snapshot.errors))
    except (ValidationError, UnsupportedSourceLocator) as exc:
        typer.echo(f"Source fetch input failed: {exc}")
        raise typer.Exit(code=1) from exc
    except (SQLAlchemyError, OSError) as exc:
        typer.echo(f"Source fetch command failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("source-content")
def source_content(snapshot_id: str = typer.Argument(..., help="Source content snapshot UUID.")) -> None:
    """List source content segments for a snapshot."""

    settings = get_settings()
    try:
        parsed_snapshot_id = uuid.UUID(snapshot_id)
        with session_scope(settings) as session:
            snapshot = session.get(SourceContentSnapshot, parsed_snapshot_id)
            if snapshot is None:
                typer.echo(f"Source content input failed: Snapshot not found: {snapshot_id}")
                raise typer.Exit(code=1)
            segments = SourceContentService(session, settings, FakeSourceFetcher()).list_segments(
                snapshot.id
            )
            typer.echo(f"Snapshot: {snapshot.id}")
            typer.echo(f"Fetch status: {snapshot.fetch_status.value}")
            typer.echo(f"Segments: {len(segments)}")
            for segment in segments:
                preview = segment.text[:80].replace("\n", " ")
                typer.echo(f"{segment.segment_identifier}: {segment.id} {preview}")
    except (ValueError, SQLAlchemyError) as exc:
        typer.echo(f"Source content command failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("extract-evidence")
def extract_evidence(
    segment_id: str = typer.Argument(..., help="Source content segment UUID."),
    research_run_id: str = typer.Option(..., help="Research run UUID for evidence provenance."),
    char_start: int | None = typer.Option(None, min=0, help="Optional segment-relative start char."),
    char_end: int | None = typer.Option(None, min=0, help="Optional segment-relative end char."),
) -> None:
    """Register explicit Evidence from a selected segment or exact span."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            result = SourceContentService(session, settings, FakeSourceFetcher()).extract_evidence(
                SegmentExtractionRequest(
                    research_run_id=research_run_id,
                    segment_id=segment_id,
                    char_start=char_start,
                    char_end=char_end,
                )
            )
            typer.echo(f"Extraction: {result.extraction_id}")
            typer.echo(f"Extraction status: {result.extraction_status.value}")
            typer.echo(f"Evidence: {result.evidence_id}")
            typer.echo(f"Snapshot: {result.snapshot_id}")
            typer.echo(f"Segment: {result.segment_id}")
            if result.errors:
                typer.echo("Errors: " + ", ".join(result.errors))
    except (ValidationError, EvidenceExtractionError) as exc:
        typer.echo(f"Evidence extraction input failed: {exc}")
        raise typer.Exit(code=1) from exc
    except SQLAlchemyError as exc:
        typer.echo(f"Evidence extraction command failed: {exc}")
        raise typer.Exit(code=1) from exc


app.add_typer(research_app, name="research")


def main() -> None:
    """CLI entry point."""

    app()


if __name__ == "__main__":
    main()
