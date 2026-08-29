"""Deterministic claim validation service."""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from darwin.db.models import (
    Claim,
    ClaimEvidence,
    ClaimEvidenceRelation,
    ClaimHumanValidation,
    ClaimValidationEvaluation,
    ClaimValidationReasonCode,
    ClaimValidationState,
    Evidence,
    HumanValidationType,
    Source,
    utc_now,
)
from darwin.research.errors import InvalidResearchRelationship
from darwin.validation.errors import ClaimValidationPersistenceError
from darwin.validation.schemas import ClaimValidationResult

DEFAULT_VALIDATION_METHOD_VERSION = "claim-validation-1.8d"


class ClaimValidationService:
    """Validate a claim's structural evidentiary state.

    The service does not determine truth, classify evidence semantics, infer source
    independence automatically, or generate numeric confidence scores.
    """

    def __init__(
        self,
        session: Session,
        *,
        method_version: str = DEFAULT_VALIDATION_METHOD_VERSION,
    ) -> None:
        self.session = session
        self.method_version = method_version

    def evaluate_claim(self, claim_id: uuid.UUID | str) -> ClaimValidationResult:
        claim = self._get_claim(claim_id)
        links = list(claim.evidence_links)

        supporting_links = self._filter_links(links, {ClaimEvidenceRelation.SUPPORTS})
        contradicting_links = self._filter_links(links, {ClaimEvidenceRelation.CONTRADICTS})
        contextual_links = self._filter_links(links, {ClaimEvidenceRelation.CONTEXTUALIZES})

        distinct_source_ids = {
            link.evidence.source_id
            for link in links
            if link.evidence is not None and link.evidence.source_id is not None
        }
        independent_supporting_source_ids = self._independent_source_ids(supporting_links)
        independent_contradicting_source_ids = self._independent_source_ids(contradicting_links)
        distinct_supporting_source_ids = {
            link.evidence.source_id
            for link in supporting_links
            if link.evidence is not None and link.evidence.source_id is not None
        }

        latest_human_event = self._latest_human_event(claim.human_validation_events)
        human_review_requested = (
            latest_human_event is not None
            and latest_human_event.validation_type is HumanValidationType.REVIEW_REQUESTED
        )
        human_validation_present = (
            latest_human_event is not None
            and latest_human_event.validation_type is HumanValidationType.VALIDATED
        )

        reason_codes = self._reason_codes(
            links=links,
            supporting_links=supporting_links,
            contradicting_links=contradicting_links,
            contextual_links=contextual_links,
            distinct_supporting_source_count=len(distinct_supporting_source_ids),
            independent_supporting_source_count=len(independent_supporting_source_ids),
            human_review_requested=human_review_requested,
            human_validation_present=human_validation_present,
        )
        validation_state = self._validation_state(
            supporting_count=len(supporting_links),
            contradicting_count=len(contradicting_links),
            contextual_count=len(contextual_links),
            independent_supporting_source_count=len(independent_supporting_source_ids),
            human_review_requested=human_review_requested,
            human_validation_present=human_validation_present,
        )

        evaluation = ClaimValidationEvaluation(
            claim=claim,
            validation_state=validation_state,
            supporting_evidence_count=len(supporting_links),
            contradicting_evidence_count=len(contradicting_links),
            contextual_evidence_count=len(contextual_links),
            distinct_source_count=len(distinct_source_ids),
            independent_supporting_source_count=len(independent_supporting_source_ids),
            independent_contradicting_source_count=len(independent_contradicting_source_ids),
            independent_corroboration_exists=len(independent_supporting_source_ids) >= 2,
            contradiction_exists=bool(contradicting_links),
            human_review_requested=human_review_requested,
            human_validation_present=human_validation_present,
            reason_codes=[reason.value for reason in reason_codes],
            evaluated_at=utc_now(),
            validation_method_version=self.method_version,
        )
        self.session.add(evaluation)
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise ClaimValidationPersistenceError("Claim validation could not be persisted") from exc

        return ClaimValidationResult(
            claim_id=evaluation.claim_id,
            validation_state=evaluation.validation_state,
            supporting_evidence_count=evaluation.supporting_evidence_count,
            contradicting_evidence_count=evaluation.contradicting_evidence_count,
            contextual_evidence_count=evaluation.contextual_evidence_count,
            distinct_source_count=evaluation.distinct_source_count,
            independent_supporting_source_count=evaluation.independent_supporting_source_count,
            independent_contradicting_source_count=evaluation.independent_contradicting_source_count,
            independent_corroboration_exists=evaluation.independent_corroboration_exists,
            contradiction_exists=evaluation.contradiction_exists,
            human_review_requested=evaluation.human_review_requested,
            human_validation_present=evaluation.human_validation_present,
            reason_codes=reason_codes,
            evaluated_at=evaluation.evaluated_at,
            validation_method_version=evaluation.validation_method_version,
        )

    def request_human_review(
        self,
        claim_id: uuid.UUID | str,
        *,
        validator_label: str | None = None,
        note: str | None = None,
    ) -> ClaimValidationResult:
        claim = self._get_claim(claim_id)
        self.session.add(
            ClaimHumanValidation(
                claim=claim,
                validation_type=HumanValidationType.REVIEW_REQUESTED,
                validator_label=validator_label,
                note=note,
            )
        )
        self.session.flush()
        return self.evaluate_claim(claim.id)

    def record_human_validation(
        self,
        claim_id: uuid.UUID | str,
        *,
        validator_label: str | None = None,
        note: str | None = None,
    ) -> ClaimValidationResult:
        claim = self._get_claim(claim_id)
        self.session.add(
            ClaimHumanValidation(
                claim=claim,
                validation_type=HumanValidationType.VALIDATED,
                validator_label=validator_label,
                note=note,
            )
        )
        self.session.flush()
        return self.evaluate_claim(claim.id)

    def _get_claim(self, claim_id: uuid.UUID | str) -> Claim:
        parsed_claim_id = self._parse_uuid(claim_id)
        if parsed_claim_id is None:
            raise InvalidResearchRelationship(f"Claim not found: {claim_id}")

        claim = self.session.execute(
            select(Claim)
            .where(Claim.id == parsed_claim_id)
            .options(
                selectinload(Claim.evidence_links)
                .selectinload(ClaimEvidence.evidence)
                .selectinload(Evidence.source),
                selectinload(Claim.human_validation_events),
            )
        ).scalar_one_or_none()
        if claim is None:
            raise InvalidResearchRelationship(f"Claim not found: {claim_id}")
        return claim

    def _filter_links(
        self,
        links: Iterable[ClaimEvidence],
        relations: set[ClaimEvidenceRelation],
    ) -> list[ClaimEvidence]:
        return [link for link in links if link.relation in relations]

    def _independent_source_ids(self, links: Iterable[ClaimEvidence]) -> set[uuid.UUID]:
        return {
            self._source_independence_id(link.evidence.source)
            for link in links
            if link.evidence is not None and link.evidence.source is not None
        }

    def _source_independence_id(self, source: Source) -> uuid.UUID:
        seen: set[uuid.UUID] = set()
        current_source = source
        while current_source.origin_source_id is not None:
            if current_source.id in seen:
                return current_source.id
            seen.add(current_source.id)
            origin_source = current_source.origin_source or self.session.get(
                Source,
                current_source.origin_source_id,
            )
            if origin_source is None:
                return current_source.origin_source_id
            current_source = origin_source
        return current_source.id

    def _latest_human_event(
        self,
        events: Iterable[ClaimHumanValidation],
    ) -> ClaimHumanValidation | None:
        return max(events, key=lambda event: event.created_at, default=None)

    def _reason_codes(
        self,
        *,
        links: list[ClaimEvidence],
        supporting_links: list[ClaimEvidence],
        contradicting_links: list[ClaimEvidence],
        contextual_links: list[ClaimEvidence],
        distinct_supporting_source_count: int,
        independent_supporting_source_count: int,
        human_review_requested: bool,
        human_validation_present: bool,
    ) -> list[ClaimValidationReasonCode]:
        reason_codes: list[ClaimValidationReasonCode] = []

        if not links:
            reason_codes.append(ClaimValidationReasonCode.NO_EVIDENCE)
        if contextual_links and not supporting_links and not contradicting_links:
            reason_codes.append(ClaimValidationReasonCode.ONLY_CONTEXTUAL_EVIDENCE)
        if contradicting_links and not supporting_links:
            reason_codes.append(ClaimValidationReasonCode.ONLY_CONTRADICTING_EVIDENCE)
        if contradicting_links:
            reason_codes.append(ClaimValidationReasonCode.CONTRADICTORY_EVIDENCE_PRESENT)
        if supporting_links and independent_supporting_source_count == 1:
            reason_codes.append(ClaimValidationReasonCode.SINGLE_SUPPORTING_SOURCE)
        if independent_supporting_source_count >= 2:
            reason_codes.append(
                ClaimValidationReasonCode.MULTIPLE_INDEPENDENT_SUPPORTING_SOURCES
            )
        if supporting_links and distinct_supporting_source_count > independent_supporting_source_count:
            reason_codes.append(ClaimValidationReasonCode.DERIVED_SOURCES_NOT_COUNTED_AS_INDEPENDENT)
        if human_review_requested:
            reason_codes.append(ClaimValidationReasonCode.HUMAN_REVIEW_REQUIRED)
        if human_validation_present:
            reason_codes.append(ClaimValidationReasonCode.HUMAN_VALIDATION_PRESENT)

        return reason_codes

    def _validation_state(
        self,
        *,
        supporting_count: int,
        contradicting_count: int,
        contextual_count: int,
        independent_supporting_source_count: int,
        human_review_requested: bool,
        human_validation_present: bool,
    ) -> ClaimValidationState:
        if human_validation_present:
            return ClaimValidationState.HUMAN_VALIDATED
        if human_review_requested:
            return ClaimValidationState.HUMAN_REVIEW_PENDING
        if supporting_count and contradicting_count:
            return ClaimValidationState.CONTESTED
        if contradicting_count and not supporting_count:
            return ClaimValidationState.CONTRADICTED
        if independent_supporting_source_count >= 2:
            return ClaimValidationState.CORROBORATED
        if supporting_count:
            return ClaimValidationState.SUPPORTED
        if contextual_count:
            return ClaimValidationState.INSUFFICIENT_EVIDENCE
        return ClaimValidationState.INSUFFICIENT_EVIDENCE

    def _parse_uuid(self, value: uuid.UUID | str) -> uuid.UUID | None:
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(value)
        except ValueError:
            return None
