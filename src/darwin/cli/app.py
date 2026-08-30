"""Command-line interface for Darwin."""

from __future__ import annotations

import uuid
from pathlib import Path

import typer
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from darwin.claim_assistance import (
    AssistedClaimConstructionRequest,
    AssistedClaimConstructionService,
    ClaimCandidateAcceptanceError,
    ClaimCandidateRejectionError,
    ClaimCandidateValidationError,
    ClaimConstructionConfigurationError,
    ClaimConstructionProviderError,
    FakeClaimConstructionProvider,
    OpenAIClaimConstructionProvider,
)
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
from darwin.construction import ClaimConstructionError, ClaimConstructionRequest, ClaimConstructionService
from darwin.db import get_engine, session_scope
from darwin.db.models import ClaimType, Source, SourceContentSnapshot, SourceType
from darwin.extraction import (
    AssistedEvidenceExtractionRequest,
    AssistedEvidenceExtractionService,
    EvidenceCandidateAcceptanceError,
    EvidenceCandidateRejectionError,
    ExtractionConfigurationError,
    ExtractionProviderError,
    ExtractionValidationError,
    FakeEvidenceExtractionProvider,
    OpenAIEvidenceExtractionProvider,
)
from darwin.logging import configure_logging
from darwin.orchestration import ManualResearchInput, ResearchOrchestrationError, ResearchOrchestrator
from darwin.planning import (
    FakePlanningProvider,
    OpenAIPlanningProvider,
    PlanningApprovalError,
    PlanningConfigurationError,
    PlanningProviderError,
    PlanningValidationError,
    ResearchPlanner,
    ResearchPlanningRequest,
)
from darwin.research import ResearchService, ResearchServiceError
from darwin.synthesis import StructuredSynthesisService
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


@research_app.command("construct-claim")
def construct_claim(
    input_file: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
) -> None:
    """Construct one caller-supplied claim from explicit evidence selections."""

    settings = get_settings()
    try:
        request = ClaimConstructionRequest.model_validate_json(input_file.read_text())
        with session_scope(settings) as session:
            result = ClaimConstructionService(session, settings).construct_claim(request)
            typer.echo(result.model_dump_json(indent=2))
    except (OSError, ValidationError, ClaimConstructionError) as exc:
        typer.echo(f"Claim construction input failed: {exc}")
        raise typer.Exit(code=1) from exc
    except (ClaimValidationError, ResearchServiceError, SQLAlchemyError) as exc:
        typer.echo(f"Claim construction command failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("claim")
def inspect_claim(claim_id: str = typer.Argument(..., help="Claim UUID to inspect.")) -> None:
    """Show a claim with validation and evidence provenance."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            claim = StructuredSynthesisService(session, settings).get_claim_view(claim_id)
            typer.echo(f"Claim: {claim.claim_id}")
            typer.echo(f"Statement: {claim.statement}")
            typer.echo(
                "Validation state: "
                f"{claim.validation_state.value if claim.validation_state is not None else 'UNASSESSED'}"
            )
            typer.echo(f"Construction method: {claim.construction_method}")
            typer.echo(f"Evidence: {len(claim.evidence)}")
            for evidence in claim.evidence:
                typer.echo(
                    f"- {evidence.relation.value}: {evidence.evidence_id} "
                    f"source={evidence.source_id} snapshot={evidence.snapshot_id} "
                    f"segment={evidence.segment_id}"
                )
            if claim.warnings:
                typer.echo("Warnings: " + ", ".join(claim.warnings))
    except (ValueError, ClaimConstructionError, SQLAlchemyError) as exc:
        typer.echo(f"Claim inspection failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("synthesize")
def synthesize_research_run(
    research_run_id: str = typer.Argument(..., help="Research run UUID or public ID."),
) -> None:
    """Create a deterministic structured synthesis record for a research run."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            result = StructuredSynthesisService(session, settings).synthesize(research_run_id)
            typer.echo(result.model_dump_json(indent=2))
    except (ResearchServiceError, ClaimConstructionError, SQLAlchemyError) as exc:
        typer.echo(f"Synthesis command failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("plan")
def plan_research(
    question: str = typer.Argument(..., help="Explicit research question to plan."),
    objective: str | None = typer.Option(None, help="Optional planning objective."),
    scope: str | None = typer.Option(None, help="Optional planning scope."),
    exclusion: list[str] | None = typer.Option(None, help="Optional exclusion. Repeatable."),
    assumption: list[str] | None = typer.Option(None, help="Optional assumption. Repeatable."),
    domain: list[str] | None = typer.Option(None, help="Optional domain constraint. Repeatable."),
    provider: str | None = typer.Option(None, help="Planning provider override: fake or openai."),
    auto_approve: bool = typer.Option(False, help="Explicitly approve the proposal after planning."),
) -> None:
    """Generate a bounded ResearchPlanProposal without executing research."""

    settings = get_settings()
    try:
        request = ResearchPlanningRequest(
            research_question=question,
            objective=objective,
            scope=scope,
            exclusions=exclusion or [],
            assumptions=assumption or [],
            domain_constraints=domain or [],
        )
        selected_provider = _planning_provider(settings, provider)
        with session_scope(settings) as session:
            proposal = ResearchPlanner(session, settings, selected_provider).plan_research(
                request,
                auto_approve=auto_approve,
            )
            _echo_plan_summary(session, settings, proposal.id)
    except (ValidationError, PlanningConfigurationError, PlanningProviderError, PlanningValidationError) as exc:
        typer.echo(f"Research planning failed: {exc}")
        raise typer.Exit(code=1) from exc
    except SQLAlchemyError as exc:
        typer.echo(f"Research planning persistence failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("plan-show")
def show_research_plan(
    proposal_id: str = typer.Argument(..., help="Research plan proposal UUID."),
) -> None:
    """Show a persisted planning proposal summary."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            _echo_plan_summary(session, settings, proposal_id)
    except (ValueError, PlanningApprovalError, SQLAlchemyError) as exc:
        typer.echo(f"Research plan lookup failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("plan-approve")
def approve_research_plan(
    proposal_id: str = typer.Argument(..., help="Research plan proposal UUID."),
) -> None:
    """Explicitly approve a proposal into a ResearchRun, framing, and pending plan items."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            result = ResearchPlanner(session, settings).approve_plan(proposal_id)
            typer.echo(f"Proposal approved: {result.proposal_id}")
            typer.echo(f"Research run: {result.public_id}")
            typer.echo(f"Database id: {result.research_run_id}")
            typer.echo(f"Approval mode: {result.approval_mode.value}")
            typer.echo(f"Plan items: {result.plan_item_count}")
    except (ValueError, PlanningApprovalError, SQLAlchemyError) as exc:
        typer.echo(f"Research plan approval failed: {exc}")
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


@research_app.command("propose-evidence")
def propose_assisted_evidence(
    research_run_id: str = typer.Option(..., help="Research run UUID."),
    research_plan_item_id: str = typer.Option(..., help="Research plan item UUID."),
    source_id: str = typer.Option(..., help="Source UUID."),
    snapshot_id: str = typer.Option(..., help="Source content snapshot UUID."),
    segment_id: list[str] | None = typer.Option(None, help="Source content segment UUID. Repeatable."),
    objective: str = typer.Option(..., help="Research objective for extraction."),
    requirement: str = typer.Option(..., help="Evidence requirement for extraction."),
    provider: str | None = typer.Option(None, help="Assisted extraction provider override: fake or openai."),
    max_candidates: int = typer.Option(3, min=1, help="Maximum evidence candidates."),
) -> None:
    """Propose grounded Evidence candidates without creating canonical Evidence."""

    settings = get_settings()
    try:
        request = AssistedEvidenceExtractionRequest(
            research_run_id=research_run_id,
            research_plan_item_id=research_plan_item_id,
            source_id=source_id,
            snapshot_id=snapshot_id,
            segment_ids=[uuid.UUID(value) for value in segment_id or []],
            research_objective=objective,
            evidence_requirement=requirement,
            max_candidate_count=max_candidates,
        )
        selected_provider = _assisted_extraction_provider(settings, provider)
        with session_scope(settings) as session:
            result = AssistedEvidenceExtractionService(
                session,
                settings,
                selected_provider,
            ).propose_evidence(request)
            typer.echo(f"Extraction request: {result.extraction_request_id}")
            typer.echo(f"Provider: {result.provider_id}")
            typer.echo(f"Model: {result.provider_model or 'n/a'}")
            typer.echo(f"Candidates: {result.candidate_count}")
            for candidate in result.candidates:
                _echo_candidate(candidate)
            if result.warnings:
                typer.echo("Warnings: " + ", ".join(result.warnings))
    except (
        ValueError,
        ValidationError,
        ExtractionConfigurationError,
        ExtractionProviderError,
        ExtractionValidationError,
        SQLAlchemyError,
    ) as exc:
        typer.echo(f"Assisted evidence proposal failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("evidence-candidates")
def list_evidence_candidates(
    extraction_request_id: str | None = typer.Option(None, help="Optional extraction request UUID."),
) -> None:
    """List persisted assisted evidence candidates."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            candidates = AssistedEvidenceExtractionService(session, settings).list_candidates(
                extraction_request_id
            )
            typer.echo(f"Candidates: {len(candidates)}")
            for candidate in candidates:
                _echo_candidate(candidate)
    except (ValueError, SQLAlchemyError) as exc:
        typer.echo(f"Evidence candidate listing failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("accept-evidence")
def accept_assisted_evidence(
    candidate_id: str = typer.Argument(..., help="Evidence candidate UUID."),
) -> None:
    """Explicitly accept one grounded candidate into canonical Evidence."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            result = AssistedEvidenceExtractionService(session, settings).accept_candidate(candidate_id)
            typer.echo(f"Candidate accepted: {result.candidate_id}")
            typer.echo(f"Evidence: {result.evidence_id}")
            typer.echo(f"Acceptance mode: {result.acceptance_mode.value}")
            typer.echo(f"Status: {result.status.value}")
    except (ValueError, EvidenceCandidateAcceptanceError, SQLAlchemyError) as exc:
        typer.echo(f"Evidence candidate acceptance failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("reject-evidence")
def reject_assisted_evidence(
    candidate_id: str = typer.Argument(..., help="Evidence candidate UUID."),
    reason: str = typer.Option(..., help="Rejection reason."),
) -> None:
    """Reject one assisted evidence candidate and preserve audit history."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            result = AssistedEvidenceExtractionService(session, settings).reject_candidate(
                candidate_id,
                reason=reason,
            )
            typer.echo(f"Candidate rejected: {result.candidate_id}")
            typer.echo(f"Status: {result.status.value}")
            typer.echo(f"Reason: {result.rejection_reason}")
    except (ValueError, EvidenceCandidateRejectionError, SQLAlchemyError) as exc:
        typer.echo(f"Evidence candidate rejection failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("propose-claims")
def propose_assisted_claims(
    research_run_id: str = typer.Option(..., help="Research run UUID."),
    research_plan_item_id: str = typer.Option(..., help="Research plan item UUID."),
    evidence_id: list[str] | None = typer.Option(None, help="Canonical Evidence UUID. Repeatable."),
    objective: str = typer.Option(..., help="Research objective for construction."),
    instruction: str = typer.Option(..., help="Claim construction instruction."),
    claim_type: ClaimType | None = typer.Option(None, help="Optional expected Claim type."),
    temporal_scope: str | None = typer.Option(None, help="Optional temporal scope for proposed Claims."),
    provider: str | None = typer.Option(None, help="Assisted claim provider override: fake or openai."),
    max_candidates: int = typer.Option(3, min=1, help="Maximum Claim candidates."),
) -> None:
    """Propose Evidence-grounded Claim candidates without creating canonical Claims."""

    settings = get_settings()
    try:
        request = AssistedClaimConstructionRequest(
            research_run_id=research_run_id,
            research_plan_item_id=research_plan_item_id,
            evidence_ids=[uuid.UUID(value) for value in evidence_id or []],
            research_objective=objective,
            construction_instruction=instruction,
            expected_claim_type=claim_type,
            temporal_scope=temporal_scope,
            max_candidate_count=max_candidates,
        )
        selected_provider = _assisted_claim_provider(settings, provider)
        with session_scope(settings) as session:
            result = AssistedClaimConstructionService(
                session,
                settings,
                selected_provider,
            ).propose_claims(request)
            typer.echo(f"Construction request: {result.construction_request_id}")
            typer.echo(f"Provider: {result.provider_id}")
            typer.echo(f"Model: {result.provider_model or 'n/a'}")
            typer.echo(f"Candidates: {result.candidate_count}")
            for candidate in result.candidates:
                _echo_claim_candidate(candidate)
            if result.warnings:
                typer.echo("Warnings: " + ", ".join(result.warnings))
    except (
        ValueError,
        ValidationError,
        ClaimConstructionConfigurationError,
        ClaimConstructionProviderError,
        ClaimCandidateValidationError,
        SQLAlchemyError,
    ) as exc:
        typer.echo(f"Assisted claim proposal failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("claim-candidates")
def list_claim_candidates(
    construction_request_id: str | None = typer.Option(None, help="Optional construction request UUID."),
) -> None:
    """List persisted assisted Claim candidates."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            candidates = AssistedClaimConstructionService(session, settings).list_candidates(
                construction_request_id
            )
            typer.echo(f"Candidates: {len(candidates)}")
            for candidate in candidates:
                _echo_claim_candidate(candidate)
    except (ValueError, SQLAlchemyError) as exc:
        typer.echo(f"Claim candidate listing failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("accept-claim")
def accept_assisted_claim(
    candidate_id: str = typer.Argument(..., help="Claim candidate UUID."),
) -> None:
    """Explicitly accept one Claim candidate into canonical Claim records."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            result = AssistedClaimConstructionService(session, settings).accept_claim_candidate(
                candidate_id
            )
            typer.echo(f"Candidate accepted: {result.candidate_id}")
            typer.echo(f"Claim: {result.claim_id}")
            typer.echo(f"Acceptance mode: {result.acceptance_mode.value}")
            typer.echo(f"Status: {result.status.value}")
    except (ValueError, ClaimCandidateAcceptanceError, SQLAlchemyError) as exc:
        typer.echo(f"Claim candidate acceptance failed: {exc}")
        raise typer.Exit(code=1) from exc


@research_app.command("reject-claim")
def reject_assisted_claim(
    candidate_id: str = typer.Argument(..., help="Claim candidate UUID."),
    reason: str = typer.Option(..., help="Rejection reason."),
) -> None:
    """Reject one assisted Claim candidate and preserve audit history."""

    settings = get_settings()
    try:
        with session_scope(settings) as session:
            result = AssistedClaimConstructionService(session, settings).reject_claim_candidate(
                candidate_id,
                reason=reason,
            )
            typer.echo(f"Candidate rejected: {result.candidate_id}")
            typer.echo(f"Status: {result.status.value}")
            typer.echo(f"Reason: {result.rejection_reason}")
    except (ValueError, ClaimCandidateRejectionError, SQLAlchemyError) as exc:
        typer.echo(f"Claim candidate rejection failed: {exc}")
        raise typer.Exit(code=1) from exc


def _planning_provider(settings, provider: str | None):
    provider_name = provider or settings.research_planning_provider
    if provider_name == "fake":
        return FakePlanningProvider(model=settings.research_planning_model)
    if provider_name == "openai":
        return OpenAIPlanningProvider(settings)
    raise PlanningConfigurationError(f"unknown planning provider {provider_name!r}")


def _assisted_extraction_provider(settings, provider: str | None):
    provider_name = provider or settings.assisted_evidence_extraction_provider
    if provider_name == "fake":
        return FakeEvidenceExtractionProvider(model=settings.assisted_evidence_extraction_model)
    if provider_name == "openai":
        return OpenAIEvidenceExtractionProvider(settings)
    raise ExtractionConfigurationError(f"unknown assisted extraction provider {provider_name!r}")


def _assisted_claim_provider(settings, provider: str | None):
    provider_name = provider or settings.assisted_claim_construction_provider
    if provider_name == "fake":
        return FakeClaimConstructionProvider(model=settings.assisted_claim_construction_model)
    if provider_name == "openai":
        return OpenAIClaimConstructionProvider(settings)
    raise ClaimConstructionConfigurationError(f"unknown assisted claim provider {provider_name!r}")


def _echo_candidate(candidate) -> None:
    typer.echo(f"- Candidate: {candidate.id}")
    typer.echo(f"  Status: {candidate.status.value}")
    typer.echo(f"  Source: {candidate.source_id}")
    typer.echo(f"  Segment: {candidate.source_content_segment_id}")
    typer.echo(f"  Type: {candidate.proposed_evidence_type.value}")
    typer.echo(f"  Grounding: {candidate.grounding_validation.get('reason', 'unknown')}")
    typer.echo(f"  Excerpt: {candidate.exact_excerpt}")
    typer.echo(f"  Relevance: {candidate.relevance_explanation}")


def _echo_claim_candidate(candidate) -> None:
    typer.echo(f"- Candidate: {candidate.id}")
    typer.echo(f"  Status: {candidate.status.value}")
    if candidate.claim_id is not None:
        typer.echo(f"  Claim: {candidate.claim_id}")
    typer.echo(f"  Type: {candidate.proposed_claim_type.value}")
    typer.echo(f"  Claim text: {candidate.proposed_claim_text}")
    evidence_ids = ", ".join(f"{link.relation.value}:{link.evidence_id}" for link in candidate.evidence)
    typer.echo(f"  Evidence: {evidence_ids}")
    if candidate.qualifiers:
        typer.echo("  Qualifiers: " + ", ".join(candidate.qualifiers))
    if candidate.provider_warnings:
        typer.echo("  Warnings: " + ", ".join(candidate.provider_warnings))


def _echo_plan_summary(session, settings, proposal_id: str | uuid.UUID) -> None:
    proposal = ResearchPlanner(session, settings).get_proposal(proposal_id, orm=True)
    typer.echo(f"Proposal: {proposal.id}")
    typer.echo(f"Approval status: {proposal.status.value}")
    if proposal.research_run is not None:
        typer.echo(f"Research run: {proposal.research_run.public_id}")
    typer.echo(f"Provider: {proposal.provider_id}")
    typer.echo(f"Model: {proposal.provider_model or 'n/a'}")
    typer.echo(f"Method: {proposal.planner_method_version}")
    typer.echo(f"Objective: {proposal.objective}")
    typer.echo("Categories: " + ", ".join(proposal.research_categories))
    typer.echo(f"Tasks: {len(proposal.items)}")
    for item in sorted(proposal.items, key=lambda row: row.item_order):
        required = "required" if item.is_required else "optional"
        typer.echo(
            f"- {item.item_key} [{required}/{item.priority.value}]: "
            f"{item.requirement}"
        )
    if proposal.warnings:
        typer.echo("Warnings: " + ", ".join(proposal.warnings))
    if proposal.errors:
        typer.echo("Errors: " + ", ".join(proposal.errors))


app.add_typer(research_app, name="research")


def main() -> None:
    """CLI entry point."""

    app()


if __name__ == "__main__":
    main()
