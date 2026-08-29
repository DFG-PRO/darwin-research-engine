"""Deterministic evidence-grounded structured synthesis."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from darwin.acquisition.normalization import sanitize_metadata
from darwin.config import Settings
from darwin.construction.service import ClaimConstructionService
from darwin.db.models import (
    Claim,
    ClaimValidationState,
    Conclusion,
    ConclusionClaim,
    Evidence,
    ResearchCompletionAssessment,
    ResearchPlanItem,
    ResearchPlanItemStatus,
    ResearchRun,
    ResearchSynthesisRecord,
    Source,
    utc_now,
)
from darwin.research import ResearchService
from darwin.research.errors import DuplicateResearchRelationship, InvalidResearchRelationship
from darwin.synthesis.schemas import (
    ConclusionClaimLinkRequest,
    ConclusionClaimRead,
    ConclusionSynthesisRead,
    StructuredSynthesisResult,
)


class StructuredSynthesisService:
    """Create append-only structured synthesis records from persisted research state."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.research_service = ResearchService(session)
        self.claim_construction = ClaimConstructionService(session, settings)

    def get_claim_view(self, claim_id: uuid.UUID | str):
        """Return the claim provenance read model used by synthesis."""

        return self.claim_construction.claim_view(claim_id)

    def link_conclusion_claim(
        self,
        request: ConclusionClaimLinkRequest,
    ) -> ConclusionClaim:
        """Persist an explicit conclusion-to-claim relationship."""

        conclusion = self.session.get(Conclusion, request.conclusion_id)
        claim = self.session.get(Claim, request.claim_id)
        if conclusion is None:
            raise InvalidResearchRelationship(f"Conclusion not found: {request.conclusion_id}")
        if claim is None:
            raise InvalidResearchRelationship(f"Claim not found: {request.claim_id}")
        if conclusion.research_run_id != claim.research_run_id:
            raise InvalidResearchRelationship("ConclusionClaim requires the same research run")

        existing = self.session.execute(
            select(ConclusionClaim).where(
                ConclusionClaim.conclusion_id == conclusion.id,
                ConclusionClaim.claim_id == claim.id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateResearchRelationship(
                f"Conclusion {conclusion.id} is already linked to claim {claim.id}"
            )

        link = ConclusionClaim(
            conclusion=conclusion,
            claim=claim,
            relation=request.relation,
            relationship_metadata=sanitize_metadata(request.metadata),
        )
        self.session.add(link)
        self.session.flush()
        return link

    def synthesize(self, research_run_id: uuid.UUID | str) -> StructuredSynthesisResult:
        """Persist and return a deterministic structured synthesis for one research run."""

        research_run = self.research_service.get_research_run(research_run_id)
        claims = self.session.scalars(
            select(Claim)
            .where(Claim.research_run_id == research_run.id)
            .order_by(Claim.created_at)
        ).all()
        claim_views = [self.claim_construction.claim_view(claim.id) for claim in claims]
        conclusions = self.session.scalars(
            select(Conclusion)
            .where(Conclusion.research_run_id == research_run.id)
            .options(
                selectinload(Conclusion.claim_links)
                .selectinload(ConclusionClaim.claim)
            )
            .order_by(Conclusion.created_at)
        ).all()
        conclusion_reads = [
            self._conclusion_read(conclusion)
            for conclusion in conclusions
        ]
        evidence_gaps = self._evidence_gaps(research_run.id, claim_views)
        unresolved_contradictions = [
            str(claim.claim_id)
            for claim in claim_views
            if claim.validation_state
            in {ClaimValidationState.CONTESTED, ClaimValidationState.CONTRADICTED}
        ]
        warnings = self._warnings(claim_views, conclusion_reads, evidence_gaps)
        completion_assessment = self._completion_assessment(
            claim_views=claim_views,
            evidence_gaps=evidence_gaps,
            unresolved_contradictions=unresolved_contradictions,
        )
        source_count = (
            self.session.scalar(
                select(func.count(func.distinct(Evidence.source_id))).where(
                    Evidence.research_run_id == research_run.id
                )
            )
            or 0
        )
        evidence_count = (
            self.session.scalar(
                select(func.count()).select_from(Evidence).where(Evidence.research_run_id == research_run.id)
            )
            or 0
        )
        result = StructuredSynthesisResult(
            synthesis_record_id=uuid.uuid4(),
            research_run_id=research_run.id,
            research_question=research_run.title,
            research_method_version=research_run.research_method_version,
            synthesis_method_version=self.settings.structured_synthesis_method_version,
            completion_assessment=completion_assessment,
            source_count=source_count,
            evidence_count=evidence_count,
            claim_count=len(claim_views),
            conclusion_count=len(conclusion_reads),
            claims=claim_views,
            conclusions=conclusion_reads,
            evidence_gaps=evidence_gaps,
            unresolved_contradictions=unresolved_contradictions,
            warnings=warnings,
            created_at=utc_now(),
        )
        self._persist_synthesis_record(result)
        return result

    def _conclusion_read(self, conclusion: Conclusion) -> ConclusionSynthesisRead:
        claim_links: list[ConclusionClaimRead] = []
        for link in sorted(conclusion.claim_links, key=lambda item: item.created_at):
            claim_view = self.claim_construction.claim_view(link.claim_id)
            claim_links.append(
                ConclusionClaimRead(
                    conclusion_id=conclusion.id,
                    claim_id=link.claim_id,
                    relation=link.relation,
                    claim_validation_state=(
                        claim_view.validation_state.value
                        if claim_view.validation_state is not None
                        else ClaimValidationState.UNASSESSED.value
                    ),
                    warnings=claim_view.warnings,
                )
            )
        warnings = sorted({warning for link in claim_links for warning in link.warnings})
        if not claim_links:
            warnings.append("conclusion_has_no_claim_links")
        return ConclusionSynthesisRead(
            conclusion_id=conclusion.id,
            statement=conclusion.statement,
            status=conclusion.status,
            claim_links=claim_links,
            warnings=warnings,
        )

    def _evidence_gaps(self, research_run_id: uuid.UUID, claim_views) -> list[str]:
        gaps = [
            item.item_key
            for item in self.session.scalars(
                select(ResearchPlanItem)
                .where(
                    ResearchPlanItem.research_run_id == research_run_id,
                    ResearchPlanItem.is_required.is_(True),
                    ResearchPlanItem.status == ResearchPlanItemStatus.PENDING,
                )
                .order_by(ResearchPlanItem.item_key)
            )
        ]
        gaps.extend(
            str(claim.claim_id)
            for claim in claim_views
            if claim.validation_state is ClaimValidationState.INSUFFICIENT_EVIDENCE
        )
        return gaps

    def _warnings(self, claim_views, conclusion_reads, evidence_gaps: list[str]) -> list[str]:
        warnings: set[str] = set()
        if evidence_gaps:
            warnings.add("evidence_gaps_present")
        for claim in claim_views:
            warnings.update(claim.warnings)
        for conclusion in conclusion_reads:
            for warning in conclusion.warnings:
                warnings.add(f"conclusion_{warning}")
        return sorted(warnings)

    def _completion_assessment(
        self,
        *,
        claim_views,
        evidence_gaps: list[str],
        unresolved_contradictions: list[str],
    ) -> ResearchCompletionAssessment:
        if any(claim.human_review_requested for claim in claim_views):
            return ResearchCompletionAssessment.HUMAN_REVIEW_REQUIRED
        if unresolved_contradictions:
            return ResearchCompletionAssessment.UNRESOLVED_CONTRADICTION
        if evidence_gaps:
            return ResearchCompletionAssessment.NEEDS_EVIDENCE
        if not claim_views:
            return ResearchCompletionAssessment.INCOMPLETE
        return ResearchCompletionAssessment.COMPLETE

    def _persist_synthesis_record(
        self,
        result: StructuredSynthesisResult,
    ) -> ResearchSynthesisRecord:
        record = ResearchSynthesisRecord(
            id=result.synthesis_record_id,
            research_run_id=result.research_run_id,
            research_method_version=result.research_method_version,
            completion_assessment=result.completion_assessment,
            source_count=result.source_count,
            evidence_count=result.evidence_count,
            claim_count=result.claim_count,
            conclusion_count=result.conclusion_count,
            evidence_gaps=result.evidence_gaps,
            unresolved_contradictions=result.unresolved_contradictions,
            warnings=result.warnings,
            synthesis_payload=result.model_dump(mode="json"),
        )
        self.session.add(record)
        self.session.flush()
        return record
