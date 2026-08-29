"""Controlled research task planner service."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from darwin.config import Settings
from darwin.db.models import (
    ResearchFraming,
    ResearchPlanApprovalMode,
    ResearchPlanItem,
    ResearchPlanItemStatus,
    ResearchPlanProposal,
    ResearchPlanProposalItem,
    ResearchPlanProposalStatus,
    ResearchRun,
    utc_now,
)
from darwin.planning.errors import (
    PlanningApprovalError,
    PlanningProviderError,
    PlanningProviderTimeout,
    PlanningValidationError,
    ResearchPlanningError,
)
from darwin.planning.providers import PlanningProvider, build_planning_provider
from darwin.planning.schemas import (
    PlanningProviderResult,
    ProviderPlanProposal,
    ResearchPlanApprovalResult,
    ResearchPlanProposalRead,
    ResearchPlanningLimits,
    ResearchPlanningRequest,
)
from darwin.research import ResearchService


class ResearchPlanner:
    """Create, validate, persist, and approve auditable research plan proposals."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
        provider: PlanningProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider = provider or build_planning_provider(settings)
        self.research_service = ResearchService(session)

    def plan_research(
        self,
        request: ResearchPlanningRequest,
        *,
        auto_approve: bool = False,
    ) -> ResearchPlanProposalRead:
        """Generate and persist a proposal; optionally approve only when explicitly requested."""

        limits = self._limits()
        try:
            provider_result = self.provider.generate_plan(request, limits)
            proposal = self._validate_provider_result(provider_result, limits)
        except PlanningProviderTimeout as exc:
            self._persist_failed_proposal(
                request,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc) or "planning provider timed out"],
            )
            raise
        except PlanningProviderError as exc:
            self._persist_failed_proposal(
                request,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc) or "planning provider failed"],
            )
            raise
        except (ValidationError, ValueError) as exc:
            provider_id = getattr(self.provider, "identifier", "unknown")
            self._persist_failed_proposal(request, provider_id=provider_id, errors=[str(exc)])
            raise PlanningValidationError(str(exc)) from exc

        record = self._persist_valid_proposal(request, provider_result, proposal)
        if auto_approve:
            self.approve_plan(record.id, approval_mode=ResearchPlanApprovalMode.AUTO_APPROVED)
            record = self.get_proposal(record.id, orm=True)
        return ResearchPlanProposalRead.model_validate(record)

    def approve_plan(
        self,
        proposal_id: uuid.UUID | str,
        *,
        approval_mode: ResearchPlanApprovalMode = ResearchPlanApprovalMode.MANUAL,
    ) -> ResearchPlanApprovalResult:
        """Convert one valid proposal into Phase 1.8-compatible framing and plan records."""

        proposal = self.get_proposal(proposal_id, orm=True)
        if proposal.status is not ResearchPlanProposalStatus.PROPOSED:
            raise PlanningApprovalError(
                f"Proposal {proposal.id} is not approvable from {proposal.status.value}"
            )

        research_run: ResearchRun | None = None
        payload: ProviderPlanProposal | None = None
        try:
            with self.session.begin_nested():
                payload = ProviderPlanProposal.model_validate(proposal.proposal_payload)
                payload.validate_structure(self._limits())
                research_run = self.research_service.create_research_run(
                    title=payload.normalized_research_question,
                    research_method_version=self.settings.research_method_version,
                    darwin_version=self.settings.darwin_version,
                    context={
                        "planning": {
                            "proposal_id": str(proposal.id),
                            "approval_mode": approval_mode.value,
                            "planner_method_version": proposal.planner_method_version,
                        }
                    },
                )
                self._create_framing(research_run, proposal, payload)
                self._create_plan_items(research_run, proposal, payload)
                proposal.research_run = research_run
                proposal.status = ResearchPlanProposalStatus.APPROVED
                proposal.approval_mode = approval_mode
                proposal.approved_at = utc_now()
                self.session.flush()
        except Exception as exc:
            if isinstance(exc, PlanningApprovalError):
                raise
            raise PlanningApprovalError(str(exc)) from exc

        if research_run is None or payload is None:
            raise PlanningApprovalError("Approval failed before a research run was created")
        return ResearchPlanApprovalResult(
            proposal_id=proposal.id,
            research_run_id=research_run.id,
            public_id=research_run.public_id,
            approval_mode=approval_mode,
            plan_item_count=len(payload.tasks),
        )

    def get_proposal(
        self,
        proposal_id: uuid.UUID | str,
        *,
        orm: bool = False,
    ) -> ResearchPlanProposal | ResearchPlanProposalRead:
        parsed_id = proposal_id if isinstance(proposal_id, uuid.UUID) else uuid.UUID(str(proposal_id))
        proposal = self.session.execute(
            select(ResearchPlanProposal)
            .where(ResearchPlanProposal.id == parsed_id)
            .options(selectinload(ResearchPlanProposal.items))
        ).scalar_one_or_none()
        if proposal is None:
            raise PlanningApprovalError(f"Research plan proposal not found: {proposal_id}")
        return proposal if orm else ResearchPlanProposalRead.model_validate(proposal)

    def _validate_provider_result(
        self,
        provider_result: PlanningProviderResult,
        limits: ResearchPlanningLimits,
    ) -> ProviderPlanProposal:
        proposal = (
            provider_result.proposal
            if isinstance(provider_result.proposal, ProviderPlanProposal)
            else ProviderPlanProposal.model_validate(provider_result.proposal)
        )
        proposal.validate_structure(limits)
        return proposal

    def _persist_valid_proposal(
        self,
        request: ResearchPlanningRequest,
        provider_result: PlanningProviderResult,
        proposal: ProviderPlanProposal,
    ) -> ResearchPlanProposal:
        warnings = proposal.planner_warnings + provider_result.warnings
        record = ResearchPlanProposal(
            original_question=request.research_question,
            normalized_question=proposal.normalized_research_question,
            objective=proposal.proposed_objective,
            scope=proposal.proposed_scope,
            exclusions=proposal.proposed_exclusions,
            assumptions=proposal.proposed_assumptions,
            research_categories=proposal.proposed_research_categories,
            expected_evidence_types=proposal.expected_evidence_types,
            suggested_source_types=[source_type.value for source_type in proposal.suggested_source_types],
            status=ResearchPlanProposalStatus.PROPOSED,
            provider_id=provider_result.provider_id,
            provider_model=provider_result.provider_model,
            provider_response_id=provider_result.provider_response_id,
            planner_method_version=proposal.method_version,
            prompt_version=proposal.prompt_version,
            schema_version=proposal.schema_version,
            warning_count=len(warnings),
            warnings=warnings,
            errors=[],
            planning_request=request.model_dump(mode="json"),
            proposal_payload=proposal.model_dump(mode="json"),
            validation_result={"valid": True, "checks": self._validation_checks()},
            provider_metadata=_sanitize_metadata(provider_result.provider_metadata),
            usage_metadata=_sanitize_metadata(provider_result.usage_metadata),
            cost_metadata=_sanitize_metadata(provider_result.cost_metadata),
            planning_metadata=_sanitize_metadata(proposal.planning_provenance),
        )
        self.session.add(record)
        self.session.flush()
        self._persist_items(record, proposal)
        self.session.flush()
        return record

    def _persist_failed_proposal(
        self,
        request: ResearchPlanningRequest,
        *,
        provider_id: str,
        errors: list[str],
    ) -> ResearchPlanProposal:
        normalized_question = _normalize_question(request.research_question)
        record = ResearchPlanProposal(
            original_question=request.research_question,
            normalized_question=normalized_question,
            objective=request.objective or "Planning failed before a valid proposal was accepted.",
            scope=request.scope or "No approved scope; planning failed.",
            exclusions=request.exclusions,
            assumptions=request.assumptions,
            research_categories=[],
            expected_evidence_types=[],
            suggested_source_types=[source_type.value for source_type in request.desired_source_types],
            status=ResearchPlanProposalStatus.FAILED,
            provider_id=provider_id,
            provider_model=None,
            planner_method_version=self.settings.research_planning_method_version,
            prompt_version=self.settings.research_planning_prompt_version,
            schema_version=self.settings.research_planning_schema_version,
            warning_count=0,
            warnings=[],
            errors=errors,
            planning_request=request.model_dump(mode="json"),
            proposal_payload={},
            validation_result={"valid": False, "errors": errors},
            provider_metadata={},
            usage_metadata={},
            cost_metadata={},
            planning_metadata={},
        )
        self.session.add(record)
        self.session.flush()
        return record

    def _persist_items(
        self,
        record: ResearchPlanProposal,
        proposal: ProviderPlanProposal,
    ) -> None:
        for index, item in enumerate(proposal.tasks):
            model = ResearchPlanProposalItem(
                proposal=record,
                item_key=item.item_key,
                requirement=item.requirement,
                category=item.category,
                priority=item.priority,
                is_required=item.required,
                status=ResearchPlanItemStatus.PENDING,
                expected_source_type=item.expected_source_type,
                expected_evidence_types=item.expected_evidence_types,
                suggested_source_types=[source_type.value for source_type in item.suggested_source_types],
                completion_criteria=item.completion_criteria,
                notes=item.notes,
                item_order=index,
            )
            self.session.add(model)

    def _create_framing(
        self,
        research_run: ResearchRun,
        proposal: ResearchPlanProposal,
        payload: ProviderPlanProposal,
    ) -> ResearchFraming:
        framing = ResearchFraming(
            research_run=research_run,
            original_question=proposal.original_question,
            normalized_question=payload.normalized_research_question,
            objective=payload.proposed_objective,
            scope=payload.proposed_scope,
            exclusions=payload.proposed_exclusions,
            key_decision_criteria=[],
            assumptions=payload.proposed_assumptions,
            required_evidence_categories=payload.proposed_research_categories,
            completion_criteria=_proposal_completion_criteria(payload),
            framing_metadata={
                "planning_proposal_id": str(proposal.id),
                "planner_method_version": payload.method_version,
            },
        )
        self.session.add(framing)
        return framing

    def _create_plan_items(
        self,
        research_run: ResearchRun,
        proposal: ResearchPlanProposal,
        payload: ProviderPlanProposal,
    ) -> list[ResearchPlanItem]:
        plan_items: list[ResearchPlanItem] = []
        for item in payload.tasks:
            plan_item = ResearchPlanItem(
                research_run=research_run,
                item_key=item.item_key,
                requirement=item.requirement,
                category=item.category,
                priority=item.priority,
                is_required=item.required,
                status=ResearchPlanItemStatus.PENDING,
                expected_source_type=item.expected_source_type,
                notes=item.notes,
            )
            plan_items.append(plan_item)
            self.session.add(plan_item)
        research_run.context = {
            **research_run.context,
            "planning": {
                **research_run.context.get("planning", {}),
                "proposal_id": str(proposal.id),
                "plan_item_keys": [item.item_key for item in payload.tasks],
            },
        }
        return plan_items

    def _limits(self) -> ResearchPlanningLimits:
        return ResearchPlanningLimits(
            max_plan_items=self.settings.research_planning_max_plan_items,
            max_required_plan_items=self.settings.research_planning_max_required_plan_items,
            max_categories=self.settings.research_planning_max_categories,
            max_breadth=self.settings.research_planning_max_breadth,
            max_depth=self.settings.research_planning_max_depth,
        )

    def _validation_checks(self) -> list[str]:
        return [
            "at_least_one_required_task",
            "no_duplicate_task_keys",
            "bounded_plan_items",
            "explicit_objective",
            "explicit_completion_criteria",
            "non_empty_categories",
            "no_completed_items",
            "no_evidence_ids",
            "no_conclusions",
        ]


def _proposal_completion_criteria(payload: ProviderPlanProposal) -> list[str]:
    criteria: list[str] = []
    for item in payload.tasks:
        criteria.extend(item.completion_criteria)
    return criteria


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    blocked = {"api_key", "authorization", "token", "secret", "password"}
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if any(part in key.lower() for part in blocked):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_metadata(value)
        else:
            sanitized[key] = value
    return sanitized


def _normalize_question(question: str) -> str:
    stripped = " ".join(question.strip().split())
    return stripped if stripped.endswith("?") else f"{stripped}?"
