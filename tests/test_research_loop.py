import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from darwin.acquisition.schemas import ProviderSearchResult, ProviderSourceCandidate
from darwin.claim_assistance import AssistedClaimConstructionService
from darwin.config import Settings
from darwin.db.models import (
    Claim,
    ClaimCandidateAcceptanceMode,
    ClaimCandidateProposal,
    ClaimEvidence,
    ClaimValidationEvaluation,
    Evidence,
    EvidenceCandidateAcceptanceMode,
    EvidenceCandidateProposal,
    NarrativeResearchReport,
    NarrativeSynthesisProposal,
    ResearchCompletionAssessment,
    ResearchAcquisitionRequest,
    ResearchLoopEvent,
    ResearchLoopExecution,
    ResearchLoopExecutionMode,
    ResearchLoopQuery,
    ResearchLoopState,
    ResearchLoopStopReason,
    ResearchPlanPriority,
    SourceContentSnapshot,
    SourceType,
    utc_now,
)
from darwin.extraction import AssistedEvidenceExtractionService
from darwin.planning.schemas import (
    PlanningProviderResult,
    ProviderPlanProposal,
    ResearchPlanItemProposal,
)
from darwin.research_loop import (
    ResearchLoopBudgets,
    ResearchLoopController,
    ResearchLoopCounters,
    ResearchLoopRequest,
    ResearchLoopValidationError,
    validate_loop_transition,
)
from darwin.research import ResearchRunNotFound, ResearchService
from darwin.validation import ClaimValidationService


def settings(tmp_path, **overrides):
    values = {
        "env": "test",
        "database_url": "sqlite+pysqlite:///:memory:",
        "artifact_root": tmp_path / "artifacts",
        "research_loop_max_iterations": 3,
        "research_loop_max_searches": 4,
        "research_loop_max_sources": 5,
        "research_loop_max_fetched_sources": 4,
        "research_loop_max_segments": 5,
        "research_loop_max_evidence_candidates": 5,
        "research_loop_max_accepted_evidence": 4,
        "research_loop_max_claim_candidates": 4,
        "research_loop_max_accepted_claims": 4,
        "research_loop_max_provider_calls": 20,
        "research_loop_max_runtime_seconds": 60,
    }
    values.update(overrides)
    return Settings(**values)


def loop_request(**overrides):
    values = {
        "research_question": "What does the controlled research loop prove?",
        "execution_mode": ResearchLoopExecutionMode.AUTO_GROUNDED,
        "budgets": ResearchLoopBudgets(),
    }
    values.update(overrides)
    return ResearchLoopRequest(**values)


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_loop_request_rejects_empty_question_invalid_mode_and_excessive_budget(tmp_path) -> None:
    with pytest.raises(ValidationError):
        loop_request(research_question="")
    with pytest.raises(ValidationError):
        ResearchLoopRequest(research_question="Question?", execution_mode="NOPE")

    app_settings = settings(tmp_path, research_loop_max_searches=1)
    request = loop_request(budgets=ResearchLoopBudgets(max_searches=2))
    with pytest.raises(ResearchLoopValidationError):
        ResearchLoopController(None, app_settings)._validate_request_against_settings(request)


def test_state_machine_transitions_and_terminal_states() -> None:
    validate_loop_transition(ResearchLoopState.PENDING, ResearchLoopState.PLANNING)
    validate_loop_transition(ResearchLoopState.WAITING_EVIDENCE_APPROVAL, ResearchLoopState.CONSTRUCTING_CLAIMS)
    with pytest.raises(ResearchLoopValidationError):
        validate_loop_transition(ResearchLoopState.PENDING, ResearchLoopState.CONSTRUCTING_CLAIMS)
    with pytest.raises(ResearchLoopValidationError):
        validate_loop_transition(ResearchLoopState.COMPLETED, ResearchLoopState.PLANNING)


def test_dry_run_persists_execution_events_and_no_canonical_research(session_factory, tmp_path) -> None:
    with session_factory() as session:
        result = ResearchLoopController(session, settings(tmp_path)).start(
            loop_request(execution_mode=ResearchLoopExecutionMode.DRY_RUN)
        )

        assert result.state is ResearchLoopState.COMPLETED
        assert result.stop_reason is ResearchLoopStopReason.DRY_RUN_COMPLETE
        assert result.completion_assessment.value == "INCOMPLETE"
        assert result.research_run_id is None
        assert count(session, ResearchLoopExecution) == 1
        assert count(session, ResearchLoopEvent) >= 3
        assert count(session, Evidence) == 0
        assert count(session, Claim) == 0


def test_auto_grounded_loop_completes_with_audited_acceptance_and_report(
    session_factory,
    tmp_path,
) -> None:
    with session_factory() as session:
        result = ResearchLoopController(session, settings(tmp_path)).start(
            loop_request(publish_report=True)
        )

        assert result.state is ResearchLoopState.COMPLETED
        assert result.stop_reason is ResearchLoopStopReason.SUCCESS_COMPLETE
        assert result.completion_assessment.value == "COMPLETE"
        assert result.research_run_id is not None
        assert result.accepted_evidence_count == 1
        assert result.accepted_claim_count == 1
        assert result.synthesis_proposal_id is not None
        assert result.report_id is not None
        assert (settings(tmp_path).artifact_root / result.report_artifact_path).is_file()
        assert count(session, ResearchLoopQuery) == 1
        assert count(session, ResearchAcquisitionRequest) == 1
        assert count(session, SourceContentSnapshot) == 1
        assert count(session, NarrativeSynthesisProposal) == 1
        assert count(session, NarrativeResearchReport) == 1
        evidence_candidate = session.execute(select(EvidenceCandidateProposal)).scalar_one()
        claim_candidate = session.execute(select(ClaimCandidateProposal)).scalar_one()
        assert evidence_candidate.acceptance_mode is EvidenceCandidateAcceptanceMode.AUTO_ACCEPTED
        assert claim_candidate.acceptance_mode is ClaimCandidateAcceptanceMode.AUTO_ACCEPTED
        assert count(session, ClaimValidationEvaluation) >= 1


def test_phase_1_9e_deterministic_loop_benchmark_fixture(session_factory, tmp_path) -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "phase_1_9e_loop_benchmark.json"
    fixture = json.loads(fixture_path.read_text())
    request = ResearchLoopRequest(
        research_question=fixture["question"],
        objective=fixture["objective"],
        scope=fixture["scope"],
        assumptions=fixture["assumptions"],
        execution_mode=ResearchLoopExecutionMode[fixture["mode"]],
        publish_report=fixture["publish_report"],
        budgets=ResearchLoopBudgets(**fixture["budgets"]),
        metadata={"fixture_id": fixture["fixture_id"]},
    )

    with session_factory() as session:
        result = ResearchLoopController(session, settings(tmp_path)).start(request)

        assert result.state.value == fixture["expected"]["state"]
        assert result.stop_reason.value == fixture["expected"]["stop_reason"]
        assert result.completion_assessment.value == fixture["expected"]["completion_assessment"]
        assert result.iteration_count == fixture["expected"]["iterations"]
        assert result.source_count == fixture["expected"]["sources"]
        assert result.accepted_evidence_count == fixture["expected"]["accepted_evidence"]
        assert result.accepted_claim_count == fixture["expected"]["accepted_claims"]
        assert result.validation_distribution == fixture["expected"]["validation_distribution"]
        assert result.synthesis_proposal_id is not None
        assert result.report_id is not None
        assert result.report_artifact_path is not None
        assert (settings(tmp_path).artifact_root / result.report_artifact_path).is_file()
        assert count(session, ResearchLoopQuery) == fixture["expected"]["queries"]
        assert count(session, ResearchLoopEvent) >= fixture["expected"]["minimum_events"]


def test_manual_gate_stops_at_evidence_then_claim_and_resumes_without_duplicates(
    session_factory,
    tmp_path,
) -> None:
    app_settings = settings(tmp_path)
    with session_factory() as session:
        controller = ResearchLoopController(session, app_settings)
        first = controller.start(loop_request(execution_mode=ResearchLoopExecutionMode.MANUAL_GATE))
        assert first.state is ResearchLoopState.WAITING_EVIDENCE_APPROVAL
        assert first.next_required_action == "Accept or reject Evidence candidates, then resume the loop."
        evidence_candidate = session.execute(select(EvidenceCandidateProposal)).scalar_one()
        AssistedEvidenceExtractionService(session, app_settings).accept_candidate(evidence_candidate.id)

        second = controller.resume(first.execution_id)
        assert second.state is ResearchLoopState.WAITING_CLAIM_APPROVAL
        claim_candidate = session.execute(select(ClaimCandidateProposal)).scalar_one()
        AssistedClaimConstructionService(session, app_settings).accept_claim_candidate(claim_candidate.id)

        final = controller.resume(first.execution_id)
        assert final.state is ResearchLoopState.COMPLETED
        assert final.stop_reason is ResearchLoopStopReason.SUCCESS_COMPLETE
        assert count(session, Evidence) == 1
        assert count(session, Claim) == 1
        assert count(session, ClaimEvidence) == 1


def test_manual_gate_human_review_stops_on_resume(session_factory, tmp_path) -> None:
    app_settings = settings(tmp_path)
    with session_factory() as session:
        controller = ResearchLoopController(session, app_settings)
        first = controller.start(loop_request(execution_mode=ResearchLoopExecutionMode.MANUAL_GATE))
        evidence_candidate = session.execute(select(EvidenceCandidateProposal)).scalar_one()
        AssistedEvidenceExtractionService(session, app_settings).accept_candidate(evidence_candidate.id)
        second = controller.resume(first.execution_id)
        claim_candidate = session.execute(select(ClaimCandidateProposal)).scalar_one()
        accepted = AssistedClaimConstructionService(session, app_settings).accept_claim_candidate(
            claim_candidate.id
        )
        ClaimValidationService(session).request_human_review(accepted.claim_id)

        final = controller.resume(first.execution_id)

        assert final.state is ResearchLoopState.STOPPED_HUMAN_REVIEW
        assert final.stop_reason is ResearchLoopStopReason.HUMAN_REVIEW_REQUIRED
        assert final.completion_assessment.value == "HUMAN_REVIEW_REQUIRED"


def test_budget_exhaustion_hard_stops_before_exceeding_source_budget(
    session_factory,
    tmp_path,
) -> None:
    with session_factory() as session:
        result = ResearchLoopController(session, settings(tmp_path)).start(
            loop_request(budgets=ResearchLoopBudgets(max_sources=0))
        )

        assert result.state is ResearchLoopState.STOPPED_BUDGET
        assert result.stop_reason is ResearchLoopStopReason.BUDGET_EXHAUSTED
        assert result.counters.source_candidates == 0


def test_no_fetch_budget_stops_without_canonical_evidence_or_claims(
    session_factory,
    tmp_path,
) -> None:
    with session_factory() as session:
        result = ResearchLoopController(session, settings(tmp_path)).start(
            loop_request(budgets=ResearchLoopBudgets(max_fetched_sources=0))
        )

        assert result.stop_reason in {
            ResearchLoopStopReason.NO_USABLE_SOURCES,
            ResearchLoopStopReason.NO_CANONICAL_EVIDENCE,
        }
        assert count(session, Evidence) == 0
        assert count(session, Claim) == 0


def test_loop_deduplicates_registered_sources_before_fetching(session_factory, tmp_path) -> None:
    class TwoItemPlanningProvider:
        identifier = "two-item-fake"

        def generate_plan(self, request, limits):
            proposal = ProviderPlanProposal(
                normalized_research_question=request.research_question,
                proposed_objective="Verify duplicate source handling.",
                proposed_scope="Two required items intentionally discover the same source.",
                proposed_research_categories=["fees", "operations"],
                expected_evidence_types=["official documentation"],
                suggested_source_types=[SourceType.WEB_PAGE],
                tasks=[
                    ResearchPlanItemProposal(
                        item_key="fees",
                        requirement="Find fee evidence.",
                        category="fees",
                        priority=ResearchPlanPriority.HIGH,
                        required=True,
                        expected_source_type=SourceType.WEB_PAGE,
                        expected_evidence_types=["fee documentation"],
                        suggested_source_types=[SourceType.WEB_PAGE],
                        completion_criteria=["Fee evidence is present."],
                    ),
                    ResearchPlanItemProposal(
                        item_key="operations",
                        requirement="Find operational evidence.",
                        category="operations",
                        priority=ResearchPlanPriority.HIGH,
                        required=True,
                        expected_source_type=SourceType.WEB_PAGE,
                        expected_evidence_types=["operational documentation"],
                        suggested_source_types=[SourceType.WEB_PAGE],
                        completion_criteria=["Operational evidence is present."],
                    ),
                ],
                method_version="test",
                schema_version="test",
            )
            return PlanningProviderResult(
                provider_id=self.identifier,
                provider_model="test",
                proposal=proposal,
                created_at=utc_now(),
            )

    class DuplicateSourceProvider:
        identifier = "duplicate-source-fake"

        def search(self, request):
            return ProviderSearchResult(
                provider_id=self.identifier,
                original_query=request.query,
                candidates=[
                    ProviderSourceCandidate(
                        canonical_locator="https://example.com/duplicate-loop-source",
                        title="Duplicate loop source",
                        publisher="Example",
                        retrieved_at=utc_now(),
                        source_type=SourceType.WEB_PAGE,
                        provider_candidate_id="duplicate",
                    )
                ],
            )

    class DuplicateSourceController(ResearchLoopController):
        def _planning_provider(self, request):
            return TwoItemPlanningProvider()

        def _acquisition_provider(self, request):
            return DuplicateSourceProvider()

    app_settings = settings(
        tmp_path,
        research_loop_max_searches=2,
        research_loop_max_sources=2,
        research_loop_max_fetched_sources=2,
        research_loop_max_segments=2,
        research_loop_max_evidence_candidates=2,
        research_loop_max_accepted_evidence=2,
        research_loop_max_provider_calls=10,
        research_planning_max_required_plan_items=2,
        research_planning_max_categories=2,
    )
    request = loop_request(
        budgets=ResearchLoopBudgets(
            max_searches=2,
            max_sources=2,
            max_fetched_sources=2,
            max_segments=2,
            max_evidence_candidates=2,
            max_accepted_evidence=2,
            max_provider_calls=10,
        )
    )

    with session_factory() as session:
        result = DuplicateSourceController(session, app_settings).start(request)

        assert result.counters.searches == 2
        assert result.counters.sources_registered == 2
        assert result.counters.content_fetches == 1
        assert count(session, SourceContentSnapshot) == 1


def test_prompt_injection_source_text_is_inert(session_factory, tmp_path) -> None:
    with session_factory() as session:
        result = ResearchLoopController(session, settings(tmp_path)).start(loop_request())
        evidence = session.execute(select(Evidence)).scalar_one()

        assert "Ignore all previous instructions" in evidence.statement
        assert result.state is ResearchLoopState.COMPLETED
        assert count(session, ResearchLoopExecution) == 1
        assert count(session, ResearchLoopEvent) > 0


def test_resume_requires_waiting_state(session_factory, tmp_path) -> None:
    with session_factory() as session:
        result = ResearchLoopController(session, settings(tmp_path)).start(loop_request())
        with pytest.raises(Exception):
            ResearchLoopController(session, settings(tmp_path)).resume(result.execution_id)


def test_loop_list_returns_multiple_execution_summaries_for_research_run(session_factory, tmp_path) -> None:
    app_settings = settings(tmp_path)
    with session_factory() as session:
        research_run = ResearchService(session).create_research_run(
            title="Loop list run",
            public_id="LOOP-LIST-RUN",
            research_method_version="test",
            darwin_version="test",
        )
        first = _persist_loop_execution(session, research_run.id, iteration_count=1)
        second = _persist_loop_execution(session, research_run.id, iteration_count=2)
        first_event = _persist_loop_event(session, first, sequence=1, event_type="FIRST")
        second_event = _persist_loop_event(session, second, sequence=1, event_type="SECOND")
        _persist_loop_event(session, second, sequence=2, event_type="LATEST")

        before_counts = (
            count(session, ResearchLoopExecution),
            count(session, ResearchLoopEvent),
        )
        summaries = ResearchLoopController(session, app_settings).list_for_research_run(research_run.id)
        after_counts = (
            count(session, ResearchLoopExecution),
            count(session, ResearchLoopEvent),
        )

        assert [item.execution_id for item in summaries] == [first.id, second.id]
        assert summaries[0].research_run_id == research_run.id
        assert summaries[0].latest_event_at == first_event.created_at
        assert summaries[1].latest_event_at >= second_event.created_at
        assert summaries[1].iteration_count == 2
        assert summaries[1].counters.iterations == 2
        assert before_counts == after_counts


def test_loop_list_returns_empty_for_run_without_executions(session_factory, tmp_path) -> None:
    with session_factory() as session:
        research_run = ResearchService(session).create_research_run(
            title="Empty loop list run",
            research_method_version="test",
            darwin_version="test",
        )

        summaries = ResearchLoopController(session, settings(tmp_path)).list_for_research_run(
            research_run.public_id
        )

        assert summaries == []


def test_loop_list_rejects_unknown_research_run(session_factory, tmp_path) -> None:
    with session_factory() as session:
        with pytest.raises(ResearchRunNotFound):
            ResearchLoopController(session, settings(tmp_path)).list_for_research_run("missing-run")


def _persist_loop_execution(session, research_run_id, *, iteration_count: int) -> ResearchLoopExecution:
    execution = ResearchLoopExecution(
        research_run_id=research_run_id,
        execution_mode=ResearchLoopExecutionMode.AUTO_GROUNDED,
        state=ResearchLoopState.COMPLETED,
        current_stage=ResearchLoopState.COMPLETED.value,
        iteration_count=iteration_count,
        request_payload={"research_question": "Loop list?"},
        budget_payload=ResearchLoopBudgets().model_dump(mode="json"),
        counters=ResearchLoopCounters(iterations=iteration_count, accepted_evidence=1).model_dump(),
        provider_payload={"planning_provider": "fake"},
        stop_reason=ResearchLoopStopReason.SUCCESS_COMPLETE,
        completion_assessment=ResearchCompletionAssessment.COMPLETE,
        loop_method_version="test",
        started_at=utc_now(),
        completed_at=utc_now(),
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
        created_at=utc_now(),
    )
    session.add(event)
    session.flush()
    return event
