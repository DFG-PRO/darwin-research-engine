"""Persistence services for research run lifecycle records."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from darwin.db.models import (
    Claim,
    ClaimEvidence,
    ClaimEvidenceRelation,
    ClaimStatus,
    ClaimType,
    Conclusion,
    ConclusionStatus,
    Evidence,
    EvidenceType,
    ResearchRun,
    ResearchRunStatus,
    Source,
    SourceLineageType,
    SourceType,
    utc_now,
)
from darwin.research.errors import (
    DuplicateResearchRelationship,
    InvalidResearchRelationship,
    InvalidResearchRunTransition,
    ResearchRunNotFound,
)
from darwin.research.schemas import (
    ClaimEvidenceRead,
    ClaimRead,
    ConclusionRead,
    EvidenceRead,
    ResearchRecordRead,
    ResearchRunRead,
    SourceRead,
)

TERMINAL_RUN_STATUSES = {ResearchRunStatus.COMPLETED, ResearchRunStatus.FAILED}
ALLOWED_RUN_TRANSITIONS = {
    ResearchRunStatus.PENDING: {ResearchRunStatus.IN_PROGRESS, ResearchRunStatus.FAILED},
    ResearchRunStatus.IN_PROGRESS: {ResearchRunStatus.COMPLETED, ResearchRunStatus.FAILED},
    ResearchRunStatus.COMPLETED: set(),
    ResearchRunStatus.FAILED: set(),
}


class ResearchService:
    """Application service for persisted research records.

    The caller owns the SQLAlchemy transaction boundary. Methods flush changes so
    database constraints surface before commit, but they do not commit partial work.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_research_run(
        self,
        *,
        title: str,
        research_method_version: str,
        darwin_version: str,
        public_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ResearchRun:
        values: dict[str, Any] = {
            "title": title,
            "research_method_version": research_method_version,
            "darwin_version": darwin_version,
            "context": context or {},
            "status": ResearchRunStatus.PENDING,
        }
        if public_id is not None:
            values["public_id"] = public_id

        research_run = ResearchRun(
            **values,
        )
        self.session.add(research_run)
        self.session.flush()
        return research_run

    def get_research_run(self, identifier: uuid.UUID | str) -> ResearchRun:
        research_run = self._find_research_run(identifier)
        if research_run is None:
            raise ResearchRunNotFound(f"Research run not found: {identifier}")
        return research_run

    def update_status(
        self,
        identifier: uuid.UUID | str,
        new_status: ResearchRunStatus,
        *,
        completed_at: datetime | None = None,
    ) -> ResearchRun:
        research_run = self.get_research_run(identifier)
        current_status = research_run.status

        if current_status == new_status:
            return research_run

        if new_status not in ALLOWED_RUN_TRANSITIONS[current_status]:
            raise InvalidResearchRunTransition(
                f"Cannot transition research run {research_run.id} "
                f"from {current_status.value} to {new_status.value}"
            )

        research_run.status = new_status
        if new_status in TERMINAL_RUN_STATUSES:
            research_run.completed_at = completed_at or utc_now()
        research_run.updated_at = utc_now()
        self.session.flush()
        return research_run

    def mark_started(self, identifier: uuid.UUID | str) -> ResearchRun:
        return self.update_status(identifier, ResearchRunStatus.IN_PROGRESS)

    def mark_completed(self, identifier: uuid.UUID | str) -> ResearchRun:
        return self.update_status(identifier, ResearchRunStatus.COMPLETED)

    def mark_failed(self, identifier: uuid.UUID | str) -> ResearchRun:
        return self.update_status(identifier, ResearchRunStatus.FAILED)

    def register_source(
        self,
        *,
        source_type: SourceType,
        canonical_locator: str,
        title: str | None = None,
        publisher: str | None = None,
        publication_date: date | None = None,
        origin_source_id: uuid.UUID | None = None,
        source_lineage_type: SourceLineageType | None = None,
        content_fingerprint: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Source:
        if (origin_source_id is None) != (source_lineage_type is None):
            raise InvalidResearchRelationship(
                "Source lineage requires both origin_source_id and source_lineage_type"
            )
        origin_source = None
        if origin_source_id is not None:
            origin_source = self._get_required(Source, origin_source_id, "Source")

        existing_source = self._find_existing_source(
            source_type=source_type,
            canonical_locator=canonical_locator,
            content_fingerprint=content_fingerprint,
        )
        if existing_source is not None:
            return existing_source

        source = Source(
            source_type=source_type,
            canonical_locator=canonical_locator,
            title=title,
            publisher=publisher,
            publication_date=publication_date,
            origin_source=origin_source,
            source_lineage_type=source_lineage_type,
            content_fingerprint=content_fingerprint,
            source_metadata=metadata or {},
        )
        self.session.add(source)
        self.session.flush()
        return source

    def register_evidence(
        self,
        *,
        research_run_id: uuid.UUID,
        source_id: uuid.UUID,
        evidence_type: EvidenceType,
        statement: str,
        source_locator: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Evidence:
        research_run = self._get_required(ResearchRun, research_run_id, "ResearchRun")
        source = self._get_required(Source, source_id, "Source")

        evidence = Evidence(
            research_run=research_run,
            source=source,
            evidence_type=evidence_type,
            statement=statement,
            source_locator=source_locator,
            evidence_metadata=metadata or {},
        )
        self.session.add(evidence)
        self.session.flush()
        return evidence

    def register_claim(
        self,
        *,
        research_run_id: uuid.UUID,
        statement: str,
        claim_type: ClaimType = ClaimType.PROPOSITION,
        status: ClaimStatus = ClaimStatus.PROPOSED,
        confidence: Decimal | float | None = None,
    ) -> Claim:
        research_run = self._get_required(ResearchRun, research_run_id, "ResearchRun")
        self._validate_confidence(confidence)

        claim = Claim(
            research_run=research_run,
            statement=statement,
            claim_type=claim_type,
            status=status,
            confidence=confidence,
        )
        self.session.add(claim)
        self.session.flush()
        return claim

    def link_claim_evidence(
        self,
        *,
        claim_id: uuid.UUID,
        evidence_id: uuid.UUID,
        relation: ClaimEvidenceRelation,
    ) -> ClaimEvidence:
        claim = self._get_required(Claim, claim_id, "Claim")
        evidence = self._get_required(Evidence, evidence_id, "Evidence")

        if claim.research_run_id != evidence.research_run_id:
            raise InvalidResearchRelationship(
                "ClaimEvidence requires claim and evidence from the same research run"
            )

        existing_link = self.session.execute(
            select(ClaimEvidence).where(
                ClaimEvidence.claim_id == claim_id,
                ClaimEvidence.evidence_id == evidence_id,
            )
        ).scalar_one_or_none()
        if existing_link is not None:
            raise DuplicateResearchRelationship(
                f"Claim {claim_id} is already linked to evidence {evidence_id}"
            )

        claim_evidence = ClaimEvidence(claim=claim, evidence=evidence, relation=relation)
        self.session.add(claim_evidence)
        self.session.flush()
        return claim_evidence

    def register_conclusion(
        self,
        *,
        research_run_id: uuid.UUID,
        statement: str,
        status: ConclusionStatus = ConclusionStatus.DRAFT,
        confidence: Decimal | float | None = None,
    ) -> Conclusion:
        research_run = self._get_required(ResearchRun, research_run_id, "ResearchRun")
        self._validate_confidence(confidence)

        conclusion = Conclusion(
            research_run=research_run,
            statement=statement,
            status=status,
            confidence=confidence,
        )
        self.session.add(conclusion)
        self.session.flush()
        return conclusion

    def get_research_record(self, identifier: uuid.UUID | str) -> ResearchRecordRead:
        research_run = self._find_research_run(
            identifier,
            options=(
                selectinload(ResearchRun.evidence_items).selectinload(Evidence.source),
                selectinload(ResearchRun.claims).selectinload(Claim.evidence_links),
                selectinload(ResearchRun.conclusions),
            ),
        )
        if research_run is None:
            raise ResearchRunNotFound(f"Research run not found: {identifier}")

        sources_by_id = {
            evidence.source.id: evidence.source
            for evidence in research_run.evidence_items
            if evidence.source is not None
        }
        claim_evidence_links = [
            link for claim in research_run.claims for link in claim.evidence_links
        ]

        return ResearchRecordRead(
            research_run=ResearchRunRead.model_validate(research_run),
            sources=[SourceRead.model_validate(source) for source in sources_by_id.values()],
            evidence=[EvidenceRead.model_validate(item) for item in research_run.evidence_items],
            claims=[ClaimRead.model_validate(claim) for claim in research_run.claims],
            claim_evidence=[
                ClaimEvidenceRead.model_validate(link) for link in claim_evidence_links
            ],
            conclusions=[
                ConclusionRead.model_validate(conclusion)
                for conclusion in research_run.conclusions
            ],
        )

    def _find_research_run(
        self,
        identifier: uuid.UUID | str,
        *,
        options: Iterable[Any] = (),
    ) -> ResearchRun | None:
        research_run_id = self._parse_uuid(identifier)
        if research_run_id is not None:
            statement: Select[tuple[ResearchRun]] = select(ResearchRun).where(
                ResearchRun.id == research_run_id
            )
        else:
            statement = select(ResearchRun).where(ResearchRun.public_id == str(identifier))

        for option in options:
            statement = statement.options(option)

        return self.session.execute(statement).scalar_one_or_none()

    def _find_existing_source(
        self,
        *,
        source_type: SourceType,
        canonical_locator: str,
        content_fingerprint: str | None,
    ) -> Source | None:
        if content_fingerprint:
            statement = select(Source).where(Source.content_fingerprint == content_fingerprint)
        else:
            statement = select(Source).where(
                Source.source_type == source_type,
                Source.canonical_locator == canonical_locator,
            )
        return self.session.execute(statement).scalar_one_or_none()

    def _get_required(self, model: type[Any], identifier: uuid.UUID, label: str) -> Any:
        instance = self.session.get(model, identifier)
        if instance is None:
            raise InvalidResearchRelationship(f"{label} not found: {identifier}")
        return instance

    def _validate_confidence(self, confidence: Decimal | float | None) -> None:
        if confidence is None:
            return
        if confidence < 0 or confidence > 1:
            raise InvalidResearchRelationship("Confidence must be between 0 and 1")

    def _parse_uuid(self, identifier: uuid.UUID | str) -> uuid.UUID | None:
        if isinstance(identifier, uuid.UUID):
            return identifier
        try:
            return uuid.UUID(identifier)
        except ValueError:
            return None
