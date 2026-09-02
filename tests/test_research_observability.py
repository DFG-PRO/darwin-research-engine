from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from darwin.config import get_settings
from darwin.db import Base
from darwin.db.models import (
    ClaimEvidenceRelation,
    EvidenceType,
    ResearchCompletionAssessment,
    ResearchLoopEvent,
    ResearchLoopExecution,
    ResearchLoopExecutionMode,
    ResearchLoopState,
    ResearchLoopStopReason,
    SourceType,
)
from darwin.observability import ResearchRunOverviewService
from darwin.research import ResearchService


def test_research_run_overview_composes_counts_integrity_and_latest_loop() -> None:
    session_factory = _session_factory()
    app_settings = get_settings()
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Observed research run",
            public_id="OBSERVED-RUN",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/overview",
        )
        evidence = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Overview test evidence.",
        )
        claim = service.register_claim(
            research_run_id=research_run.id,
            statement="Overview test claim.",
        )
        service.link_claim_evidence(
            claim_id=claim.id,
            evidence_id=evidence.id,
            relation=ClaimEvidenceRelation.SUPPORTS,
        )
        service.register_conclusion(
            research_run_id=research_run.id,
            statement="Overview test conclusion.",
        )
        old_execution = _persist_loop_execution(session, research_run.id, iteration_count=1)
        latest_execution = _persist_loop_execution(session, research_run.id, iteration_count=2)
        _persist_loop_event(session, old_execution, sequence=1, event_type="OLD")
        _persist_loop_event(session, latest_execution, sequence=1, event_type="LATEST")
        before_counts = _row_counts(session)

        overview = ResearchRunOverviewService(session, app_settings).overview("OBSERVED-RUN")
        after_counts = _row_counts(session)

        assert overview.schema_version == "research-run-overview.v1"
        assert overview.research_run.public_id == "OBSERVED-RUN"
        assert overview.counts.source_count == 1
        assert overview.counts.evidence_count == 1
        assert overview.counts.claim_count == 1
        assert overview.counts.claim_evidence_count == 1
        assert overview.counts.conclusion_count == 1
        assert overview.integrity.healthy is True
        assert overview.loop_count == 2
        assert overview.latest_loop is not None
        assert overview.latest_loop.execution_id == latest_execution.id
        assert overview.overall_state == "COMPLETED"
        assert overview.operator_next_action == "No immediate operator action detected by the overview."
        assert overview.warnings == []
        assert before_counts == after_counts


def test_research_run_overview_reports_missing_loop_and_integrity_warning() -> None:
    session_factory = _session_factory()
    app_settings = get_settings()
    with session_factory() as session:
        research_run = ResearchService(session).create_research_run(
            title="Sparse research run",
            public_id="SPARSE-RUN",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )

        overview = ResearchRunOverviewService(session, app_settings).overview(research_run.public_id)

        assert overview.overall_state == "NEEDS_ATTENTION"
        assert overview.counts.evidence_count == 0
        assert overview.integrity.healthy is False
        assert overview.integrity.error_count == 1
        assert overview.loop_count == 0
        assert overview.latest_loop is None
        assert overview.warnings == ["INTEGRITY_ISSUES_PRESENT", "NO_LOOP_EXECUTIONS"]


def _session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _persist_loop_execution(session, research_run_id, *, iteration_count: int) -> ResearchLoopExecution:
    execution = ResearchLoopExecution(
        research_run_id=research_run_id,
        execution_mode=ResearchLoopExecutionMode.AUTO_GROUNDED,
        state=ResearchLoopState.COMPLETED,
        current_stage=ResearchLoopState.COMPLETED.value,
        iteration_count=iteration_count,
        request_payload={"research_question": "Overview?"},
        budget_payload={},
        counters={
            "iterations": iteration_count,
            "searches": 0,
            "accepted_evidence": 0,
            "accepted_claims": 0,
        },
        provider_payload={"planning_provider": "fake"},
        stop_reason=ResearchLoopStopReason.SUCCESS_COMPLETE,
        completion_assessment=ResearchCompletionAssessment.COMPLETE,
        loop_method_version="test",
    )
    session.add(execution)
    session.flush()
    return execution


def _persist_loop_event(
    session,
    execution: ResearchLoopExecution,
    *,
    sequence: int,
    event_type: str,
) -> ResearchLoopEvent:
    event = ResearchLoopEvent(
        execution_id=execution.id,
        sequence=sequence,
        stage=execution.state,
        event_type=event_type,
        status="OK",
        message=event_type,
        linked_object_ids={},
        counters=execution.counters,
        warnings=[],
        errors=[],
    )
    session.add(event)
    session.flush()
    return event


def _row_counts(session) -> dict[str, int]:
    from darwin.db.models import (
        Claim,
        ClaimEvidence,
        Conclusion,
        Evidence,
        ResearchLoopEvent,
        ResearchLoopExecution,
        ResearchRun,
        Source,
    )

    models = [
        ResearchRun,
        Source,
        Evidence,
        Claim,
        ClaimEvidence,
        Conclusion,
        ResearchLoopExecution,
        ResearchLoopEvent,
    ]
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model))
        for model in models
    }
