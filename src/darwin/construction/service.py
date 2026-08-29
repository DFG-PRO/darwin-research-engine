"""Explicit evidence-to-claim construction service."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from darwin.acquisition.normalization import sanitize_metadata
from darwin.config import Settings
from darwin.construction.errors import ClaimConstructionError
from darwin.construction.schemas import (
    ClaimConstructionRequest,
    ClaimConstructionResult,
    ClaimProvenanceRead,
    EvidenceProvenanceRead,
)
from darwin.db.models import (
    Claim,
    ClaimConstructionEvidence,
    ClaimConstructionMethod,
    ClaimConstructionRecord,
    ClaimEvidence,
    ClaimEvidenceRelation,
    ClaimStatus,
    ClaimValidationEvaluation,
    ClaimValidationReasonCode,
    ClaimValidationState,
    Evidence,
    HumanValidationType,
    Source,
    SourceContentSegment,
    SourceContentSnapshot,
)
from darwin.research import ResearchService
from darwin.validation import ClaimValidationService


class ClaimConstructionService:
    """Construct caller-supplied claims from explicitly selected evidence."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.research_service = ResearchService(session)
        self.validation_service = ClaimValidationService(
            session,
            method_version=settings.research_method_version,
        )

    def construct_claim(self, request: ClaimConstructionRequest) -> ClaimConstructionResult:
        """Persist a claim, evidence links, construction audit, and validation result."""

        self.research_service.get_research_run(request.research_run_id)
        statement = self._normalize_statement(request.statement)
        if request.construction_method is not ClaimConstructionMethod.MANUAL_EXPLICIT:
            raise ClaimConstructionError("Only MANUAL_EXPLICIT claim construction is supported")

        evidence_by_id = {
            selection.evidence_id: self._eligible_evidence(
                research_run_id=request.research_run_id,
                evidence_id=selection.evidence_id,
            )
            for selection in request.evidence
        }

        claim = self.research_service.register_claim(
            research_run_id=request.research_run_id,
            statement=statement,
            claim_type=request.claim_type,
            status=ClaimStatus.PROPOSED,
        )

        for selection in request.evidence:
            self.research_service.link_claim_evidence(
                claim_id=claim.id,
                evidence_id=selection.evidence_id,
                relation=selection.relation,
            )

        warnings = self._construction_warnings(request)
        record = ClaimConstructionRecord(
            research_run_id=request.research_run_id,
            claim_id=claim.id,
            construction_method=request.construction_method,
            construction_method_version=self.settings.claim_construction_method_version,
            claim_statement=statement,
            evidence_count=len(request.evidence),
            warning_count=len(warnings),
            warnings=warnings,
            construction_metadata=sanitize_metadata(request.metadata),
        )
        self.session.add(record)
        self.session.flush()

        for selection in request.evidence:
            self.session.add(
                ClaimConstructionEvidence(
                    construction_record=record,
                    evidence=evidence_by_id[selection.evidence_id],
                    relation=selection.relation,
                )
            )
        self.session.flush()

        validation_result = (
            self.validation_service.evaluate_claim(claim.id) if request.auto_validate else None
        )
        return ClaimConstructionResult(
            construction_record_id=record.id,
            claim_id=claim.id,
            statement=claim.statement,
            claim_type=claim.claim_type,
            construction_method=record.construction_method,
            construction_method_version=record.construction_method_version,
            evidence=[
                evidence_provenance(evidence_by_id[selection.evidence_id], selection.relation)
                for selection in request.evidence
            ],
            validation_state=(
                validation_result.validation_state if validation_result is not None else None
            ),
            validation_reason_codes=(
                validation_result.reason_codes if validation_result is not None else []
            ),
            warnings=warnings,
        )

    def claim_view(self, claim_id: uuid.UUID | str) -> ClaimProvenanceRead:
        """Return an evidence-grounded read model for one claim."""

        claim = self._load_claim(claim_id)
        latest_validation = latest_claim_validation(claim)
        construction_record = latest_construction_record(claim)
        evidence = [
            evidence_provenance(link.evidence, link.relation)
            for link in sorted(claim.evidence_links, key=lambda link: link.created_at)
        ]
        supporting_count = len(
            [link for link in claim.evidence_links if link.relation is ClaimEvidenceRelation.SUPPORTS]
        )
        contradicting_count = len(
            [
                link
                for link in claim.evidence_links
                if link.relation is ClaimEvidenceRelation.CONTRADICTS
            ]
        )
        contextual_count = len(
            [
                link
                for link in claim.evidence_links
                if link.relation is ClaimEvidenceRelation.CONTEXTUALIZES
            ]
        )
        latest_human_event = max(
            claim.human_validation_events,
            key=lambda event: event.created_at,
            default=None,
        )
        human_review_requested = (
            latest_human_event is not None
            and latest_human_event.validation_type is HumanValidationType.REVIEW_REQUESTED
        )
        human_validation_present = (
            latest_human_event is not None
            and latest_human_event.validation_type is HumanValidationType.VALIDATED
        )
        validation_state = (
            latest_validation.validation_state
            if latest_validation is not None
            else ClaimValidationState.UNASSESSED
        )
        reason_codes = (
            [
                ClaimValidationReasonCode(code)
                for code in latest_validation.reason_codes
            ]
            if latest_validation is not None
            else []
        )
        return ClaimProvenanceRead(
            claim_id=claim.id,
            statement=claim.statement,
            claim_type=claim.claim_type,
            validation_state=validation_state,
            validation_reason_codes=reason_codes,
            construction_method=(
                construction_record.construction_method if construction_record is not None else None
            ),
            construction_method_version=(
                construction_record.construction_method_version
                if construction_record is not None
                else None
            ),
            evidence=evidence,
            supporting_evidence_count=supporting_count,
            contradicting_evidence_count=contradicting_count,
            contextual_evidence_count=contextual_count,
            independent_source_count=len(independent_source_ids(claim.evidence_links)),
            unresolved_contradiction=validation_state
            in {ClaimValidationState.CONTESTED, ClaimValidationState.CONTRADICTED},
            human_review_requested=human_review_requested,
            human_validation_present=human_validation_present,
            warnings=claim_warnings(validation_state, human_review_requested, human_validation_present),
        )

    def _normalize_statement(self, statement: str) -> str:
        normalized = " ".join(statement.strip().split())
        if not normalized:
            raise ClaimConstructionError("Claim statement must not be empty")
        if len(normalized) > self.settings.claim_statement_max_chars:
            raise ClaimConstructionError("Claim statement exceeds configured maximum length")
        return normalized

    def _eligible_evidence(self, *, research_run_id: uuid.UUID, evidence_id: uuid.UUID) -> Evidence:
        evidence = self.session.execute(
            select(Evidence)
            .where(Evidence.id == evidence_id)
            .options(selectinload(Evidence.source))
        ).scalar_one_or_none()
        if evidence is None:
            raise ClaimConstructionError(f"Evidence not found: {evidence_id}")
        if evidence.research_run_id != research_run_id:
            raise ClaimConstructionError("Evidence belongs to a different research run")
        if evidence.source is None or evidence.source_id is None:
            raise ClaimConstructionError("Evidence lacks source provenance")
        self._validate_content_provenance(evidence)
        return evidence

    def _validate_content_provenance(self, evidence: Evidence) -> None:
        metadata = evidence.evidence_metadata or {}
        snapshot_id = metadata.get("content_snapshot_id")
        segment_id = metadata.get("source_content_segment_id")
        if snapshot_id is None and segment_id is None:
            return
        if snapshot_id is None or segment_id is None:
            raise ClaimConstructionError("Content-derived evidence must include snapshot and segment provenance")

        snapshot_uuid = self._parse_metadata_uuid(snapshot_id, "content_snapshot_id")
        segment_uuid = self._parse_metadata_uuid(segment_id, "source_content_segment_id")
        snapshot = self.session.get(SourceContentSnapshot, snapshot_uuid)
        segment = self.session.get(SourceContentSegment, segment_uuid)
        if snapshot is None or segment is None:
            raise ClaimConstructionError("Content-derived evidence references missing provenance records")
        if snapshot.research_run_id != evidence.research_run_id:
            raise ClaimConstructionError("Content snapshot belongs to a different research run")
        if snapshot.source_id != evidence.source_id:
            raise ClaimConstructionError("Content snapshot source does not match evidence source")
        if segment.snapshot_id != snapshot.id or segment.source_id != evidence.source_id:
            raise ClaimConstructionError("Content segment provenance does not match evidence source")

    def _parse_metadata_uuid(self, value: str, label: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ClaimConstructionError(f"Invalid {label} metadata UUID") from exc

    def _construction_warnings(self, request: ClaimConstructionRequest) -> list[str]:
        if any(selection.relation is ClaimEvidenceRelation.RELATED for selection in request.evidence):
            return ["related_evidence_is_not_structural_support"]
        return []

    def _load_claim(self, claim_id: uuid.UUID | str) -> Claim:
        parsed_claim_id = claim_id if isinstance(claim_id, uuid.UUID) else uuid.UUID(str(claim_id))
        claim = self.session.execute(
            select(Claim)
            .where(Claim.id == parsed_claim_id)
            .options(
                selectinload(Claim.evidence_links)
                .selectinload(ClaimEvidence.evidence)
                .selectinload(Evidence.source),
                selectinload(Claim.validation_evaluations),
                selectinload(Claim.human_validation_events),
                selectinload(Claim.construction_records),
            )
        ).scalar_one_or_none()
        if claim is None:
            raise ClaimConstructionError(f"Claim not found: {claim_id}")
        return claim


def evidence_provenance(evidence: Evidence, relation: ClaimEvidenceRelation) -> EvidenceProvenanceRead:
    """Build provenance for evidence without creating new claims or validations."""

    metadata = evidence.evidence_metadata or {}
    source = evidence.source
    if source is None:
        raise ClaimConstructionError("Evidence lacks source provenance")
    return EvidenceProvenanceRead(
        evidence_id=evidence.id,
        relation=relation,
        excerpt=evidence.statement,
        source_id=source.id,
        source_locator=source.canonical_locator,
        source_title=source.title,
        source_lineage_type=source.source_lineage_type,
        origin_source_id=source.origin_source_id,
        snapshot_id=_optional_uuid(metadata.get("content_snapshot_id")),
        segment_id=_optional_uuid(metadata.get("source_content_segment_id")),
        evidence_locator=evidence.source_locator,
    )


def latest_claim_validation(claim: Claim) -> ClaimValidationEvaluation | None:
    """Return the newest persisted validation evaluation for a claim."""

    return max(claim.validation_evaluations, key=lambda evaluation: evaluation.evaluated_at, default=None)


def latest_construction_record(claim: Claim) -> ClaimConstructionRecord | None:
    """Return the newest explicit construction audit record for a claim."""

    return max(claim.construction_records, key=lambda record: record.created_at, default=None)


def independent_source_ids(links: list[ClaimEvidence]) -> set[uuid.UUID]:
    """Count evidence source origins so republished/derived sources do not inflate support."""

    return {
        _source_independence_id(link.evidence.source)
        for link in links
        if link.evidence is not None and link.evidence.source is not None
    }


def claim_warnings(
    validation_state: ClaimValidationState | None,
    human_review_requested: bool,
    human_validation_present: bool,
) -> list[str]:
    """Return deterministic synthesis warnings for one claim state."""

    warnings: list[str] = []
    if validation_state is ClaimValidationState.INSUFFICIENT_EVIDENCE:
        warnings.append("claim_has_insufficient_evidence")
    if validation_state in {ClaimValidationState.CONTESTED, ClaimValidationState.CONTRADICTED}:
        warnings.append("claim_has_unresolved_contradiction")
    if human_review_requested:
        warnings.append("claim_human_review_pending")
    if human_validation_present:
        warnings.append("claim_human_validated")
    return warnings


def _source_independence_id(source: Source) -> uuid.UUID:
    seen: set[uuid.UUID] = set()
    current_source = source
    while current_source.origin_source is not None or current_source.origin_source_id is not None:
        if current_source.id in seen:
            return current_source.id
        seen.add(current_source.id)
        if current_source.origin_source is None:
            return current_source.origin_source_id or current_source.id
        current_source = current_source.origin_source
    return current_source.id


def _optional_uuid(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None
