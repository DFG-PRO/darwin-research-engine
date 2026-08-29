import pytest
from pydantic import ValidationError
from sqlalchemy import event, func, select

from darwin.config import Settings
from darwin.db.models import (
    Claim,
    Conclusion,
    Evidence,
    ResearchAcquisitionRequest,
    ResearchFraming,
    ResearchPlanApprovalMode,
    ResearchPlanItem,
    ResearchPlanItemStatus,
    ResearchPlanPriority,
    ResearchPlanProposal,
    ResearchPlanProposalItem,
    ResearchPlanProposalStatus,
    ResearchRun,
    Source,
    SourceType,
)
from darwin.planning import (
    FakePlanningProvider,
    PlanningProviderError,
    PlanningProviderResult,
    PlanningProviderTimeout,
    PlanningValidationError,
    ProviderPlanProposal,
    ResearchPlanItemProposal,
    ResearchPlanner,
    ResearchPlanningRequest,
)


def settings(tmp_path, **overrides):
    values = {
        "env": "test",
        "database_url": "sqlite+pysqlite:///:memory:",
        "artifact_root": tmp_path,
        "research_planning_model": "fake-deterministic-planner-v1",
    }
    values.update(overrides)
    return Settings(**values)


def valid_provider_result(*, tasks=None, categories=None):
    categories = categories or ["category-a"]
    tasks = tasks or [
        ResearchPlanItemProposal(
            item_key="task-a",
            requirement="Identify authoritative source candidates.",
            category=categories[0],
            priority=ResearchPlanPriority.HIGH,
            required=True,
            expected_source_type=SourceType.WEB_PAGE,
            expected_evidence_types=["primary documentation"],
            suggested_source_types=[SourceType.WEB_PAGE],
            completion_criteria=["At least one source candidate is ready for acquisition."],
        )
    ]
    return PlanningProviderResult(
        provider_id="custom",
        provider_model="custom-model",
        provider_response_id="response-1",
        proposal=ProviderPlanProposal(
            normalized_research_question="What is changing?",
            proposed_objective="Plan a bounded investigation.",
            proposed_scope="Planning only.",
            proposed_research_categories=categories,
            expected_evidence_types=["primary documentation"],
            suggested_source_types=[SourceType.WEB_PAGE],
            tasks=tasks,
            planner_warnings=["proposal is not evidence"],
            method_version="research-planning-1.9a",
            prompt_version="prompt-1",
            schema_version="schema-1",
            planning_provenance={"method": "test"},
        ),
    )


class StaticPlanningProvider:
    identifier = "static"

    def __init__(self, result):
        self.result = result

    def generate_plan(self, request, limits):
        return self.result


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_planning_request_validates_empty_question() -> None:
    with pytest.raises(ValidationError):
        ResearchPlanningRequest(research_question="   ")


def test_fake_provider_creates_deterministic_proposal_without_research_records(
    session_factory,
    tmp_path,
) -> None:
    with session_factory() as session:
        request = ResearchPlanningRequest(
            research_question="How should Darwin evaluate planning?",
            scope="Only produce a proposal.",
            desired_source_types=[SourceType.DOCUMENT],
            domain_constraints=["example.com"],
        )
        proposal = ResearchPlanner(session, settings(tmp_path)).plan_research(request)

        assert proposal.status is ResearchPlanProposalStatus.PROPOSED
        assert proposal.provider_id == "fake"
        assert proposal.provider_model == "fake-deterministic-planner-v1"
        assert proposal.planner_method_version == "research-planning-1.9a"
        assert count(session, ResearchPlanProposal) == 1
        assert count(session, ResearchPlanProposalItem) == 2
        assert count(session, ResearchRun) == 0
        assert count(session, Source) == 0
        assert count(session, Evidence) == 0
        assert count(session, Claim) == 0
        assert count(session, Conclusion) == 0
        assert count(session, ResearchAcquisitionRequest) == 0


def test_planner_rejects_malformed_provider_output(session_factory, tmp_path) -> None:
    with session_factory() as session:
        planner = ResearchPlanner(session, settings(tmp_path), FakePlanningProvider(mode="invalid"))
        with pytest.raises(PlanningValidationError):
            planner.plan_research(ResearchPlanningRequest(research_question="Plan this"))

        failed = session.execute(select(ResearchPlanProposal)).scalar_one()
        assert failed.status is ResearchPlanProposalStatus.FAILED
        assert count(session, ResearchRun) == 0


def test_planner_rejects_duplicate_task_keys(session_factory, tmp_path) -> None:
    task = valid_provider_result().proposal.tasks[0]
    result = valid_provider_result(tasks=[task, task])

    with session_factory() as session:
        planner = ResearchPlanner(session, settings(tmp_path), StaticPlanningProvider(result))
        with pytest.raises(PlanningValidationError):
            planner.plan_research(ResearchPlanningRequest(research_question="Plan duplicates"))

        assert count(session, ResearchPlanProposal) == 1
        assert count(session, ResearchRun) == 0


def test_planner_rejects_zero_required_tasks(session_factory, tmp_path) -> None:
    task = valid_provider_result().proposal.tasks[0].model_copy(update={"required": False})
    result = valid_provider_result(tasks=[task])

    with session_factory() as session:
        planner = ResearchPlanner(session, settings(tmp_path), StaticPlanningProvider(result))
        with pytest.raises(PlanningValidationError):
            planner.plan_research(ResearchPlanningRequest(research_question="Plan optional only"))


def test_planner_rejects_excessive_task_count(session_factory, tmp_path) -> None:
    base_task = valid_provider_result().proposal.tasks[0]
    tasks = [
        base_task.model_copy(update={"item_key": "task-a"}),
        base_task.model_copy(update={"item_key": "task-b"}),
    ]
    result = valid_provider_result(tasks=tasks)

    with session_factory() as session:
        planner = ResearchPlanner(
            session,
            settings(tmp_path, research_planning_max_plan_items=1),
            StaticPlanningProvider(result),
        )
        with pytest.raises(PlanningValidationError):
            planner.plan_research(ResearchPlanningRequest(research_question="Plan too much"))


def test_provider_timeout_and_error_do_not_create_research_run(session_factory, tmp_path) -> None:
    for mode, error_type in [("timeout", PlanningProviderTimeout), ("error", PlanningProviderError)]:
        with session_factory() as session:
            planner = ResearchPlanner(session, settings(tmp_path), FakePlanningProvider(mode=mode))
            with pytest.raises(error_type):
                planner.plan_research(ResearchPlanningRequest(research_question="Plan failure"))

            assert count(session, ResearchPlanProposal) == 1
            assert count(session, ResearchRun) == 0


def test_approval_creates_phase_1_8_framing_and_pending_plan_items(
    session_factory,
    tmp_path,
) -> None:
    with session_factory() as session:
        planner = ResearchPlanner(session, settings(tmp_path))
        proposal = planner.plan_research(ResearchPlanningRequest(research_question="Approve this plan"))

        assert count(session, ResearchRun) == 0
        result = planner.approve_plan(proposal.id)

        approved = session.get(ResearchPlanProposal, proposal.id)
        run = session.get(ResearchRun, result.research_run_id)
        assert approved.status is ResearchPlanProposalStatus.APPROVED
        assert approved.approval_mode is ResearchPlanApprovalMode.MANUAL
        assert approved.research_run_id == run.id
        assert count(session, ResearchFraming) == 1
        assert count(session, ResearchPlanItem) == 2
        assert all(item.status is ResearchPlanItemStatus.PENDING for item in run.plan_items)
        assert count(session, Source) == 0
        assert count(session, Evidence) == 0
        assert count(session, Claim) == 0
        assert count(session, Conclusion) == 0
        assert count(session, ResearchAcquisitionRequest) == 0


def test_auto_approval_is_explicit_and_audited(session_factory, tmp_path) -> None:
    with session_factory() as session:
        proposal = ResearchPlanner(session, settings(tmp_path)).plan_research(
            ResearchPlanningRequest(research_question="Auto approve this plan"),
            auto_approve=True,
        )

        persisted = session.get(ResearchPlanProposal, proposal.id)
        assert persisted.status is ResearchPlanProposalStatus.APPROVED
        assert persisted.approval_mode is ResearchPlanApprovalMode.AUTO_APPROVED
        assert persisted.research_run_id is not None


def test_failed_approval_rolls_back_partial_research_run(session_factory, tmp_path) -> None:
    with session_factory() as session:
        planner = ResearchPlanner(session, settings(tmp_path))
        proposal = planner.plan_research(ResearchPlanningRequest(research_question="Rollback plan"))

        def fail_plan_item_insert(mapper, connection, target):
            raise RuntimeError("forced plan item failure")

        event.listen(ResearchPlanItem, "before_insert", fail_plan_item_insert)
        try:
            with pytest.raises(Exception):
                planner.approve_plan(proposal.id)
        finally:
            event.remove(ResearchPlanItem, "before_insert", fail_plan_item_insert)

        assert count(session, ResearchRun) == 0
        assert count(session, ResearchFraming) == 0
        assert count(session, ResearchPlanItem) == 0
        persisted = session.get(ResearchPlanProposal, proposal.id)
        assert persisted.status is ResearchPlanProposalStatus.PROPOSED
