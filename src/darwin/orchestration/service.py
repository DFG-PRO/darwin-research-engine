"""Deterministic manual research orchestration."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from darwin.config import Settings
from darwin.db.models import (
    Claim,
    ClaimValidationState,
    Conclusion,
    Evidence,
    ResearchCompletionAssessment,
    ResearchFraming,
    ResearchPlanItem,
    ResearchPlanItemStatus,
    ResearchRun,
    ResearchSynthesisRecord,
    Source,
)
from darwin.orchestration.errors import ResearchOrchestrationError
from darwin.orchestration.schemas import (
    ClaimInput,
    ClaimResult,
    ConclusionResult,
    FramingInput,
    FramingResult,
    ManualResearchInput,
    PlanItemInput,
    PlanItemResult,
    ResearchOrchestrationResult,
)
from darwin.research import ResearchService
from darwin.validation import ClaimValidationService


class ResearchOrchestrator:
    """Coordinate the v0.1 manual research method over supplied material."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.research_service = ResearchService(session)
        self.validation_service = ClaimValidationService(
            session,
            method_version=settings.research_method_version,
        )

    def run_manual(self, manual_input: ManualResearchInput) -> ResearchOrchestrationResult:
        self._validate_unique_keys("source", [source.source_key for source in manual_input.sources])
        self._validate_unique_keys(
            "evidence",
            [evidence.evidence_key for evidence in manual_input.evidence],
        )
        self._validate_unique_keys("claim", [claim.claim_key for claim in manual_input.claims])
        self._validate_unique_keys("plan item", [item.item_key for item in manual_input.plan_items])

        research_run = self.research_service.create_research_run(
            title=manual_input.research_question,
            public_id=manual_input.public_id,
            research_method_version=self.settings.research_method_version,
            darwin_version=self.settings.darwin_version,
            context={"orchestration": "manual-supplied-material"},
        )
        self.research_service.mark_started(research_run.id)

        framing = self._create_framing(research_run, manual_input)
        plan_items = self._create_plan_items(research_run, manual_input.plan_items)
        sources = self._register_sources(manual_input)
        evidence = self._register_evidence(research_run, manual_input, sources, plan_items)
        claims = self._register_claims(research_run, manual_input.claims, evidence)
        conclusions = self._register_conclusions(research_run, manual_input.conclusions)

        claim_results = self._validate_claims(manual_input, claims)
        completion_assessment = self._completion_assessment(plan_items, claim_results, evidence)
        evidence_gaps = self._evidence_gaps(plan_items)
        unresolved_contradictions = self._unresolved_contradictions(claim_results)
        warnings = self._warnings(completion_assessment, evidence_gaps, unresolved_contradictions)

        if completion_assessment is ResearchCompletionAssessment.COMPLETE:
            self.research_service.mark_completed(research_run.id)

        result = self._build_result(
            research_run=research_run,
            framing=framing,
            plan_items=plan_items,
            sources=sources,
            evidence=evidence,
            claim_results=claim_results,
            conclusions=conclusions,
            completion_assessment=completion_assessment,
            evidence_gaps=evidence_gaps,
            unresolved_contradictions=unresolved_contradictions,
            warnings=warnings,
        )
        self._persist_synthesis_record(result)
        return result

    def _create_framing(
        self,
        research_run: ResearchRun,
        manual_input: ManualResearchInput,
    ) -> ResearchFraming:
        supplied = manual_input.framing or FramingInput()
        original_question = supplied.original_question or manual_input.research_question
        normalized_question = supplied.normalized_question or self._normalize_question(original_question)
        objective = supplied.objective or f"Answer the research question: {original_question}"

        framing = ResearchFraming(
            research_run=research_run,
            original_question=original_question,
            normalized_question=normalized_question,
            objective=objective,
            scope=supplied.scope,
            exclusions=supplied.exclusions,
            key_decision_criteria=supplied.key_decision_criteria,
            assumptions=supplied.assumptions,
            required_evidence_categories=supplied.required_evidence_categories,
            completion_criteria=supplied.completion_criteria,
            framing_metadata=supplied.metadata,
        )
        self.session.add(framing)
        self.session.flush()
        return framing

    def _create_plan_items(
        self,
        research_run: ResearchRun,
        plan_item_inputs: list[PlanItemInput],
    ) -> dict[str, ResearchPlanItem]:
        plan_items: dict[str, ResearchPlanItem] = {}
        for item_input in plan_item_inputs:
            plan_item = ResearchPlanItem(
                research_run=research_run,
                item_key=item_input.item_key,
                requirement=item_input.requirement,
                category=item_input.category,
                priority=item_input.priority,
                is_required=item_input.required,
                status=ResearchPlanItemStatus.PENDING,
                expected_source_type=item_input.expected_source_type,
                notes=item_input.notes,
            )
            self.session.add(plan_item)
            plan_items[item_input.item_key] = plan_item
        self.session.flush()
        return plan_items

    def _register_sources(self, manual_input: ManualResearchInput) -> dict[str, Source]:
        sources: dict[str, Source] = {}
        for source_input in manual_input.sources:
            origin_source_id = None
            if source_input.origin_source_key is not None:
                origin = sources.get(source_input.origin_source_key)
                if origin is None:
                    raise ResearchOrchestrationError(
                        f"Unknown origin source key: {source_input.origin_source_key}"
                    )
                origin_source_id = origin.id

            source = self.research_service.register_source(
                source_type=source_input.source_type,
                canonical_locator=source_input.canonical_locator,
                title=source_input.title,
                publisher=source_input.publisher,
                publication_date=source_input.publication_date,
                origin_source_id=origin_source_id,
                source_lineage_type=source_input.source_lineage_type,
                content_fingerprint=source_input.content_fingerprint,
                metadata=source_input.metadata,
            )
            sources[source_input.source_key] = source
        return sources

    def _register_evidence(
        self,
        research_run: ResearchRun,
        manual_input: ManualResearchInput,
        sources: dict[str, Source],
        plan_items: dict[str, ResearchPlanItem],
    ) -> dict[str, Evidence]:
        evidence_by_key: dict[str, Evidence] = {}
        for evidence_input in manual_input.evidence:
            source = sources.get(evidence_input.source_key)
            if source is None:
                raise ResearchOrchestrationError(
                    f"Evidence references unknown source key: {evidence_input.source_key}"
                )

            unknown_plan_keys = [
                key for key in evidence_input.plan_item_keys if key not in plan_items
            ]
            if unknown_plan_keys:
                raise ResearchOrchestrationError(
                    f"Evidence references unknown plan item keys: {unknown_plan_keys}"
                )

            metadata = dict(evidence_input.metadata)
            metadata["plan_item_keys"] = evidence_input.plan_item_keys
            evidence = self.research_service.register_evidence(
                research_run_id=research_run.id,
                source_id=source.id,
                evidence_type=evidence_input.evidence_type,
                statement=evidence_input.statement,
                source_locator=evidence_input.source_locator,
                metadata=metadata,
            )
            evidence_by_key[evidence_input.evidence_key] = evidence

            for plan_item_key in evidence_input.plan_item_keys:
                plan_items[plan_item_key].status = ResearchPlanItemStatus.SATISFIED

        self.session.flush()
        return evidence_by_key

    def _register_claims(
        self,
        research_run: ResearchRun,
        claim_inputs: list[ClaimInput],
        evidence: dict[str, Evidence],
    ) -> dict[str, Claim]:
        claims: dict[str, Claim] = {}
        for claim_input in claim_inputs:
            claim = self.research_service.register_claim(
                research_run_id=research_run.id,
                statement=claim_input.statement,
                claim_type=claim_input.claim_type,
                status=claim_input.status,
                confidence=claim_input.confidence,
            )
            claims[claim_input.claim_key] = claim

            for relationship in claim_input.evidence:
                evidence_item = evidence.get(relationship.evidence_key)
                if evidence_item is None:
                    raise ResearchOrchestrationError(
                        f"Claim references unknown evidence key: {relationship.evidence_key}"
                    )
                self.research_service.link_claim_evidence(
                    claim_id=claim.id,
                    evidence_id=evidence_item.id,
                    relation=relationship.relation,
                )
        return claims

    def _register_conclusions(
        self,
        research_run: ResearchRun,
        conclusion_inputs: list[Any],
    ) -> list[Conclusion]:
        return [
            self.research_service.register_conclusion(
                research_run_id=research_run.id,
                statement=conclusion_input.statement,
                status=conclusion_input.status,
                confidence=conclusion_input.confidence,
            )
            for conclusion_input in conclusion_inputs
        ]

    def _validate_claims(
        self,
        manual_input: ManualResearchInput,
        claims: dict[str, Claim],
    ) -> list[ClaimResult]:
        unknown_review_keys = [
            claim_key
            for claim_key in manual_input.human_review_claim_keys
            if claim_key not in claims
        ]
        if unknown_review_keys:
            raise ResearchOrchestrationError(
                f"Human review references unknown claim keys: {unknown_review_keys}"
            )

        claim_results: list[ClaimResult] = []
        for claim_key, claim in claims.items():
            if claim_key in manual_input.human_review_claim_keys:
                validation_result = self.validation_service.request_human_review(claim.id)
            else:
                validation_result = self.validation_service.evaluate_claim(claim.id)
            claim_results.append(
                ClaimResult(
                    claim_id=claim.id,
                    claim_key=claim_key,
                    statement=claim.statement,
                    validation_state=validation_result.validation_state,
                    reason_codes=validation_result.reason_codes,
                    supporting_evidence_count=validation_result.supporting_evidence_count,
                    contradicting_evidence_count=validation_result.contradicting_evidence_count,
                    contextual_evidence_count=validation_result.contextual_evidence_count,
                )
            )
        return claim_results

    def _completion_assessment(
        self,
        plan_items: dict[str, ResearchPlanItem],
        claim_results: list[ClaimResult],
        evidence: dict[str, Evidence],
    ) -> ResearchCompletionAssessment:
        if any(
            result.validation_state is ClaimValidationState.HUMAN_REVIEW_PENDING
            for result in claim_results
        ):
            return ResearchCompletionAssessment.HUMAN_REVIEW_REQUIRED
        if any(
            result.validation_state is ClaimValidationState.CONTESTED
            for result in claim_results
        ):
            return ResearchCompletionAssessment.UNRESOLVED_CONTRADICTION
        if self._evidence_gaps(plan_items):
            return ResearchCompletionAssessment.NEEDS_EVIDENCE
        if plan_items and not evidence:
            return ResearchCompletionAssessment.NEEDS_EVIDENCE
        if not claim_results:
            return ResearchCompletionAssessment.INCOMPLETE
        return ResearchCompletionAssessment.COMPLETE

    def _evidence_gaps(self, plan_items: dict[str, ResearchPlanItem]) -> list[str]:
        return [
            item.item_key
            for item in plan_items.values()
            if item.is_required and item.status is ResearchPlanItemStatus.PENDING
        ]

    def _unresolved_contradictions(self, claim_results: list[ClaimResult]) -> list[str]:
        return [
            result.claim_key
            for result in claim_results
            if result.validation_state is ClaimValidationState.CONTESTED
        ]

    def _warnings(
        self,
        completion_assessment: ResearchCompletionAssessment,
        evidence_gaps: list[str],
        unresolved_contradictions: list[str],
    ) -> list[str]:
        warnings: list[str] = []
        if completion_assessment is ResearchCompletionAssessment.HUMAN_REVIEW_REQUIRED:
            warnings.append("human_review_required")
        if evidence_gaps:
            warnings.append("required_evidence_missing")
        if unresolved_contradictions:
            warnings.append("unresolved_contradiction")
        return warnings

    def _build_result(
        self,
        *,
        research_run: ResearchRun,
        framing: ResearchFraming,
        plan_items: dict[str, ResearchPlanItem],
        sources: dict[str, Source],
        evidence: dict[str, Evidence],
        claim_results: list[ClaimResult],
        conclusions: list[Conclusion],
        completion_assessment: ResearchCompletionAssessment,
        evidence_gaps: list[str],
        unresolved_contradictions: list[str],
        warnings: list[str],
    ) -> ResearchOrchestrationResult:
        return ResearchOrchestrationResult(
            research_run_id=research_run.id,
            public_id=research_run.public_id,
            research_question=research_run.title,
            research_method_version=research_run.research_method_version,
            run_status=research_run.status,
            framing=FramingResult(
                original_question=framing.original_question,
                normalized_question=framing.normalized_question,
                objective=framing.objective,
                scope=framing.scope,
                exclusions=framing.exclusions,
                key_decision_criteria=framing.key_decision_criteria,
                assumptions=framing.assumptions,
                required_evidence_categories=framing.required_evidence_categories,
                completion_criteria=framing.completion_criteria,
            ),
            plan_items=[
                PlanItemResult(
                    item_key=item.item_key,
                    requirement=item.requirement,
                    category=item.category,
                    required=item.is_required,
                    status=item.status,
                )
                for item in plan_items.values()
            ],
            plan_completion=self._plan_completion(plan_items),
            source_count=len({source.id for source in sources.values()}),
            evidence_count=len(evidence),
            claim_results=claim_results,
            unresolved_contradictions=unresolved_contradictions,
            evidence_gaps=evidence_gaps,
            assumptions=framing.assumptions,
            conclusions=[
                ConclusionResult(id=conclusion.id, statement=conclusion.statement, status=conclusion.status)
                for conclusion in conclusions
            ],
            warnings=warnings,
            completion_assessment=completion_assessment,
            synthesis_record_id=uuid.uuid4(),
            created_at=research_run.created_at,
            completed_at=research_run.completed_at,
        )

    def _persist_synthesis_record(
        self,
        result: ResearchOrchestrationResult,
    ) -> ResearchSynthesisRecord:
        synthesis_record = ResearchSynthesisRecord(
            id=result.synthesis_record_id,
            research_run_id=result.research_run_id,
            research_method_version=result.research_method_version,
            completion_assessment=result.completion_assessment,
            source_count=result.source_count,
            evidence_count=result.evidence_count,
            claim_count=len(result.claim_results),
            conclusion_count=len(result.conclusions),
            evidence_gaps=result.evidence_gaps,
            unresolved_contradictions=result.unresolved_contradictions,
            warnings=result.warnings,
            synthesis_payload=result.model_dump(mode="json"),
        )
        self.session.add(synthesis_record)
        self.session.flush()
        return synthesis_record

    def _plan_completion(self, plan_items: dict[str, ResearchPlanItem]) -> dict[str, int]:
        total_required = len([item for item in plan_items.values() if item.is_required])
        satisfied_required = len(
            [
                item
                for item in plan_items.values()
                if item.is_required and item.status is ResearchPlanItemStatus.SATISFIED
            ]
        )
        return {
            "total": len(plan_items),
            "required": total_required,
            "satisfied_required": satisfied_required,
            "pending_required": total_required - satisfied_required,
        }

    def _normalize_question(self, question: str) -> str:
        return " ".join(question.strip().lower().split())

    def _validate_unique_keys(self, label: str, keys: list[str]) -> None:
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ResearchOrchestrationError(f"Duplicate {label} keys: {duplicates}")
