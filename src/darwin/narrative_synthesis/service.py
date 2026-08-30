"""Controlled assisted narrative synthesis service."""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from darwin.acquisition.normalization import sanitize_metadata
from darwin.config import Settings
from darwin.construction import ClaimConstructionService
from darwin.db.models import (
    Claim,
    ClaimEvidenceRelation,
    ClaimValidationState,
    Conclusion,
    ConclusionClaim,
    Evidence,
    NarrativeResearchReport,
    NarrativeSynthesisFinding as NarrativeSynthesisFindingRecord,
    NarrativeSynthesisProposal as NarrativeSynthesisProposalRecord,
    NarrativeSynthesisProposalStatus,
    NarrativeSynthesisRequest as NarrativeSynthesisRequestRecord,
    NarrativeSynthesisRequestStatus,
    ResearchCompletionAssessment,
    ResearchFraming,
    ResearchPlanItem,
    ResearchPlanItemStatus,
    ResearchRun,
    ResearchSynthesisRecord,
    Source,
    utc_now,
)
from darwin.narrative_synthesis.errors import (
    NarrativeSynthesisContextOverflow,
    NarrativeSynthesisProviderError,
    NarrativeSynthesisProviderTimeout,
    NarrativeSynthesisPublicationError,
    NarrativeSynthesisRejectionError,
    NarrativeSynthesisValidationError,
)
from darwin.narrative_synthesis.providers import (
    NarrativeSynthesisProvider,
    build_narrative_synthesis_provider,
)
from darwin.narrative_synthesis.schemas import (
    ClaimContext,
    ClaimEvidenceContext,
    ConclusionClaimContext,
    ConclusionContext,
    EvidenceContext,
    FramingContext,
    NarrativeFinding,
    NarrativeProposal,
    NarrativeProposalRead,
    NarrativePublicationResult,
    NarrativeRejectionResult,
    NarrativeSynthesisLimits,
    NarrativeSynthesisRequest,
    NarrativeSynthesisResult,
    PlanItemContext,
    ProviderNarrativeSynthesisResult,
    SourceContext,
    SynthesisContext,
)
from darwin.research import ResearchService
from darwin.research.errors import ResearchRunNotFound


class NarrativeSynthesisService:
    """Propose, validate, persist, reject, and publish narrative reports."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
        provider: NarrativeSynthesisProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider = provider or build_narrative_synthesis_provider(settings)
        self.research_service = ResearchService(session)
        self.claim_construction = ClaimConstructionService(session, settings)

    def build_context(self, research_run_id: uuid.UUID | str) -> SynthesisContext:
        """Build bounded canonical context without provider or report mutation."""

        return self._build_context(research_run_id, self._limits())

    def propose_synthesis(self, request: NarrativeSynthesisRequest) -> NarrativeSynthesisResult:
        """Persist a provider proposal only after deterministic grounding validation."""

        limits = self._limits()
        if request.maximum_length is not None and request.maximum_length > limits.max_report_chars:
            raise NarrativeSynthesisValidationError("request exceeds max report length")
        context = self._build_context(request.research_run_id, limits)
        try:
            provider_result = self.provider.propose_synthesis(request, context, limits)
        except NarrativeSynthesisProviderTimeout as exc:
            record = self._persist_request(
                request,
                context,
                status=NarrativeSynthesisRequestStatus.FAILED,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc) or "narrative synthesis provider timed out"],
            )
            raise NarrativeSynthesisProviderTimeout(record.errors[0]) from exc
        except NarrativeSynthesisProviderError as exc:
            record = self._persist_request(
                request,
                context,
                status=NarrativeSynthesisRequestStatus.FAILED,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc) or "narrative synthesis provider failed"],
            )
            raise NarrativeSynthesisProviderError(record.errors[0]) from exc

        request_record = self._persist_request(
            request,
            context,
            status=NarrativeSynthesisRequestStatus.COMPLETED,
            provider_id=provider_result.provider_id,
            provider_model=provider_result.provider_model,
            provider_response_id=provider_result.provider_response_id,
            warnings=provider_result.warnings,
            provider_metadata=provider_result.provider_metadata,
            usage_metadata=provider_result.usage_metadata,
            cost_metadata=provider_result.cost_metadata,
        )
        try:
            proposal = self._coerce_provider_proposal(provider_result, limits)
            validation_result = self._validate_proposal(proposal, context, limits)
            status = NarrativeSynthesisProposalStatus.VALIDATED
            errors: list[str] = []
        except (ValidationError, ValueError, NarrativeSynthesisValidationError) as exc:
            proposal = (
                provider_result.proposal
                if isinstance(provider_result.proposal, NarrativeProposal)
                else None
            )
            if proposal is None:
                request_record.status = NarrativeSynthesisRequestStatus.FAILED
                request_record.error_count = 1
                request_record.errors = [str(exc)]
                request_record.completed_at = utc_now()
                self.session.flush()
                raise NarrativeSynthesisValidationError(str(exc)) from exc
            validation_result = {"valid": False, "errors": [str(exc)]}
            status = NarrativeSynthesisProposalStatus.REJECTED_INVALID_GROUNDING
            errors = [str(exc)]

        proposal_record = self._persist_proposal(
            request_record,
            provider_result,
            proposal,
            status=status,
            validation_result=validation_result,
            errors=errors,
        )
        request_record.proposal_count = 1
        request_record.completed_at = utc_now()
        self.session.flush()
        if status is NarrativeSynthesisProposalStatus.REJECTED_INVALID_GROUNDING:
            raise NarrativeSynthesisValidationError(errors[0])
        return NarrativeSynthesisResult(
            synthesis_request_id=request_record.id,
            proposal_id=proposal_record.id,
            provider_id=proposal_record.provider_id,
            provider_model=proposal_record.provider_model,
            status=proposal_record.status,
            warnings=proposal_record.warnings,
            errors=proposal_record.errors,
        )

    def get_proposal(self, proposal_id: uuid.UUID | str) -> NarrativeProposalRead:
        """Return a persisted narrative proposal."""

        proposal = self._get_proposal_record(proposal_id)
        return self._proposal_read(proposal)

    def publish_synthesis(self, proposal_id: uuid.UUID | str) -> NarrativePublicationResult:
        """Explicitly publish one validated proposal as an immutable Markdown artifact."""

        proposal = self._get_proposal_record(proposal_id)
        existing_report = self._report_for_proposal(proposal.id)
        if proposal.status is NarrativeSynthesisProposalStatus.PUBLISHED:
            if existing_report is None:
                raise NarrativeSynthesisPublicationError("Published proposal is missing report artifact record")
            return self._publication_result(proposal, existing_report)
        if proposal.status is not NarrativeSynthesisProposalStatus.VALIDATED:
            raise NarrativeSynthesisPublicationError(
                f"Proposal {proposal.id} is not eligible for publication from {proposal.status.value}"
            )

        proposal_payload = NarrativeProposal.model_validate(proposal.proposal_payload)
        context = self._build_context(proposal.research_run_id, self._limits())
        validation_result = self._validate_proposal(proposal_payload, context, self._limits())
        markdown = render_markdown_report(proposal_payload, context)
        encoded = markdown.encode("utf-8")
        if len(markdown) > self._limits().max_report_chars:
            raise NarrativeSynthesisPublicationError("rendered report exceeds max report length")

        report_id = uuid.uuid4()
        artifact_path = _write_report_artifact(
            root=self.settings.artifact_root,
            research_run_id=proposal.research_run_id,
            report_id=report_id,
            content=encoded,
        )
        checksum = hashlib.sha256(encoded).hexdigest()
        try:
            with self.session.begin_nested():
                report = NarrativeResearchReport(
                    id=report_id,
                    proposal=proposal,
                    research_run_id=proposal.research_run_id,
                    report_version=1,
                    artifact_path=artifact_path,
                    artifact_sha256=checksum,
                    artifact_size_bytes=len(encoded),
                    report_metadata={"report_format": "markdown"},
                )
                self.session.add(report)
                proposal.status = NarrativeSynthesisProposalStatus.PUBLISHED
                proposal.published_at = utc_now()
                proposal.validation_result = validation_result
                self.session.flush()
        except Exception as exc:
            raise NarrativeSynthesisPublicationError(str(exc)) from exc

        return self._publication_result(proposal, report)

    def reject_synthesis(
        self,
        proposal_id: uuid.UUID | str,
        *,
        reason: str,
    ) -> NarrativeRejectionResult:
        """Reject a proposal while preserving audit history."""

        proposal = self._get_proposal_record(proposal_id)
        reason = reason.strip()
        if not reason:
            raise NarrativeSynthesisRejectionError("Rejection reason is required")
        if proposal.status is NarrativeSynthesisProposalStatus.PUBLISHED:
            raise NarrativeSynthesisRejectionError("Published proposals cannot be rejected")
        if proposal.status is NarrativeSynthesisProposalStatus.REJECTED:
            return NarrativeRejectionResult(
                proposal_id=proposal.id,
                status=proposal.status,
                rejection_reason=proposal.rejection_reason or reason,
            )
        proposal.status = NarrativeSynthesisProposalStatus.REJECTED
        proposal.rejection_reason = reason
        proposal.rejected_at = utc_now()
        self.session.flush()
        return NarrativeRejectionResult(
            proposal_id=proposal.id,
            status=proposal.status,
            rejection_reason=reason,
        )

    def _build_context(
        self,
        research_run_id: uuid.UUID | str,
        limits: NarrativeSynthesisLimits,
    ) -> SynthesisContext:
        run = self.research_service.get_research_run(research_run_id)

        plan_items = self.session.scalars(
            select(ResearchPlanItem)
            .where(ResearchPlanItem.research_run_id == run.id)
            .order_by(ResearchPlanItem.item_key)
        ).all()
        framing = self.session.scalars(
            select(ResearchFraming)
            .where(ResearchFraming.research_run_id == run.id)
            .order_by(ResearchFraming.created_at.desc())
        ).first()
        conclusions = self.session.scalars(
            select(Conclusion)
            .where(Conclusion.research_run_id == run.id)
            .options(selectinload(Conclusion.claim_links).selectinload(ConclusionClaim.claim))
            .order_by(Conclusion.created_at)
        ).all()
        conclusion_claim_ids = {link.claim_id for conclusion in conclusions for link in conclusion.claim_links}
        claim_rows = self.session.scalars(
            select(Claim)
            .where(Claim.research_run_id == run.id)
            .order_by(Claim.created_at)
        ).all()
        if not claim_rows:
            raise NarrativeSynthesisValidationError("Narrative synthesis requires canonical Claims")
        claim_views = [self.claim_construction.claim_view(claim.id) for claim in claim_rows]
        selected_claims = self._select_claims(claim_views, conclusion_claim_ids, limits)
        evidence_ids = _ordered_unique(
            link.evidence_id for claim in selected_claims for link in claim.evidence
        )
        if len(evidence_ids) > limits.max_evidence_items:
            raise NarrativeSynthesisContextOverflow("selected claims exceed max Evidence items")
        evidence_rows = self.session.scalars(
            select(Evidence)
            .where(Evidence.id.in_(evidence_ids))
            .options(selectinload(Evidence.source))
        ).all()
        evidence_by_id = {item.id: item for item in evidence_rows}
        evidence_context, evidence_warnings = self._evidence_context(evidence_ids, evidence_by_id, limits)
        source_ids = _ordered_unique(item.source_id for item in evidence_context)
        sources = self.session.scalars(select(Source).where(Source.id.in_(source_ids))).all()
        source_context = [
            SourceContext(
                id=source.id,
                source_type=source.source_type,
                canonical_locator=source.canonical_locator,
                title=source.title,
                publisher=source.publisher,
                publication_date=source.publication_date,
                retrieved_at=source.retrieved_at,
                source_lineage_type=source.source_lineage_type,
                origin_source_id=source.origin_source_id,
                metadata=sanitize_metadata(source.source_metadata),
            )
            for source in sorted(sources, key=lambda source: str(source.id))
        ]
        claim_context = [
            ClaimContext(
                id=claim.claim_id,
                statement=claim.statement,
                claim_type=claim.claim_type,
                validation_state=claim.validation_state or ClaimValidationState.UNASSESSED,
                validation_reason_codes=[reason.value for reason in claim.validation_reason_codes],
                evidence=[
                    ClaimEvidenceContext(evidence_id=link.evidence_id, relation=link.relation)
                    for link in claim.evidence
                ],
                supporting_evidence_count=claim.supporting_evidence_count,
                contradicting_evidence_count=claim.contradicting_evidence_count,
                contextual_evidence_count=claim.contextual_evidence_count,
                independent_source_count=claim.independent_source_count,
                unresolved_contradiction=claim.unresolved_contradiction,
                human_review_requested=claim.human_review_requested,
                human_validation_present=claim.human_validation_present,
                warnings=claim.warnings,
            )
            for claim in selected_claims
        ]
        claim_state_by_id = {claim.id: claim.validation_state for claim in claim_context}
        conclusion_context = [
            ConclusionContext(
                id=conclusion.id,
                statement=conclusion.statement,
                status=conclusion.status,
                claim_links=[
                    ConclusionClaimContext(
                        claim_id=link.claim_id,
                        relation=link.relation,
                        claim_validation_state=claim_state_by_id.get(
                            link.claim_id,
                            ClaimValidationState.UNASSESSED,
                        ),
                    )
                    for link in sorted(conclusion.claim_links, key=lambda item: item.created_at)
                    if link.claim_id in claim_state_by_id
                ],
                warnings=[] if conclusion.claim_links else ["conclusion_has_no_claim_links"],
            )
            for conclusion in conclusions
        ]
        evidence_gaps = self._evidence_gaps(plan_items, claim_context)
        unresolved = [
            claim.id
            for claim in claim_context
            if claim.validation_state in {ClaimValidationState.CONTESTED, ClaimValidationState.CONTRADICTED}
        ]
        human_review_states = [
            claim.id
            for claim in claim_context
            if claim.human_review_requested or claim.human_validation_present
        ]
        completion = self._completion_assessment(claim_context, evidence_gaps, unresolved)
        latest_synthesis = self.session.scalars(
            select(ResearchSynthesisRecord)
            .where(ResearchSynthesisRecord.research_run_id == run.id)
            .order_by(ResearchSynthesisRecord.created_at.desc())
        ).first()
        warnings = []
        warnings.extend(evidence_warnings)
        if len(selected_claims) < len(claim_views):
            warnings.append("claim_selection_bounded")
        if evidence_gaps:
            warnings.append("evidence_gaps_present")
        if unresolved:
            warnings.append("unresolved_contradictions_present")
        if human_review_states:
            warnings.append("human_review_state_present")

        return SynthesisContext(
            research_run_id=run.id,
            public_id=run.public_id,
            research_question=run.title,
            run_status=run.status,
            research_method_version=run.research_method_version,
            darwin_version=run.darwin_version,
            objective=framing.objective if framing is not None else f"Answer the research question: {run.title}",
            scope=framing.scope if framing is not None else "",
            exclusions=framing.exclusions if framing is not None else [],
            assumptions=framing.assumptions if framing is not None else [],
            framing=(
                FramingContext(
                    original_question=framing.original_question,
                    normalized_question=framing.normalized_question,
                    objective=framing.objective,
                    scope=framing.scope,
                    exclusions=framing.exclusions,
                    assumptions=framing.assumptions,
                    required_evidence_categories=framing.required_evidence_categories,
                    completion_criteria=framing.completion_criteria,
                )
                if framing is not None
                else None
            ),
            plan_items=[
                PlanItemContext(
                    id=item.id,
                    item_key=item.item_key,
                    requirement=item.requirement,
                    category=item.category,
                    priority=item.priority,
                    is_required=item.is_required,
                    status=item.status,
                    expected_source_type=item.expected_source_type,
                    notes=item.notes,
                )
                for item in plan_items
            ],
            claims=claim_context,
            evidence=evidence_context,
            sources=source_context,
            conclusions=conclusion_context,
            evidence_gaps=evidence_gaps,
            unresolved_contradictions=unresolved,
            human_review_states=human_review_states,
            completion_assessment=completion,
            latest_structured_synthesis_record_id=(
                latest_synthesis.id if latest_synthesis is not None else None
            ),
            latest_structured_synthesis_created_at=(
                latest_synthesis.created_at if latest_synthesis is not None else None
            ),
            method_version=self.settings.narrative_synthesis_method_version,
            schema_version=self.settings.narrative_synthesis_schema_version,
            warnings=sorted(set(warnings)),
            created_at=utc_now(),
        )

    def _select_claims(self, claim_views, conclusion_claim_ids: set[uuid.UUID], limits: NarrativeSynthesisLimits):
        contested = [
            claim
            for claim in claim_views
            if claim.validation_state in {ClaimValidationState.CONTESTED, ClaimValidationState.CONTRADICTED}
        ]
        if len(contested) > limits.max_claims:
            raise NarrativeSynthesisContextOverflow("critical contradictions exceed max Claims")
        if len(claim_views) <= limits.max_claims:
            return claim_views

        ordered = sorted(
            enumerate(claim_views),
            key=lambda item: (
                self._claim_priority(item[1], conclusion_claim_ids),
                item[0],
            ),
        )
        selected = [claim for _, claim in ordered[: limits.max_claims]]
        missing_contested = {claim.claim_id for claim in contested}.difference(
            {claim.claim_id for claim in selected}
        )
        if missing_contested:
            raise NarrativeSynthesisContextOverflow("bounded selection would omit a contradiction")
        return selected

    def _claim_priority(self, claim, conclusion_claim_ids: set[uuid.UUID]) -> int:
        if claim.claim_id in conclusion_claim_ids:
            return 0
        if claim.validation_state is ClaimValidationState.CORROBORATED:
            return 1
        if claim.validation_state in {ClaimValidationState.CONTESTED, ClaimValidationState.CONTRADICTED}:
            return 2
        if claim.validation_state is ClaimValidationState.SUPPORTED:
            return 3
        if claim.human_review_requested:
            return 5
        return 7

    def _evidence_context(
        self,
        evidence_ids: list[uuid.UUID],
        evidence_by_id: dict[uuid.UUID, Evidence],
        limits: NarrativeSynthesisLimits,
    ) -> tuple[list[EvidenceContext], list[str]]:
        remaining_chars = limits.max_evidence_chars
        warnings: list[str] = []
        rows: list[EvidenceContext] = []
        for evidence_id in evidence_ids:
            evidence = evidence_by_id[evidence_id]
            statement = evidence.statement
            if len(statement) > remaining_chars:
                if remaining_chars <= 0:
                    statement = ""
                else:
                    statement = statement[: max(0, remaining_chars - 20)].rstrip() + " [truncated]"
                warnings.append("evidence_excerpt_truncated")
            remaining_chars -= len(statement)
            metadata = evidence.evidence_metadata or {}
            rows.append(
                EvidenceContext(
                    id=evidence.id,
                    evidence_type=evidence.evidence_type,
                    statement=statement,
                    source_id=evidence.source_id,
                    source_locator=evidence.source_locator,
                    captured_at=evidence.captured_at,
                    snapshot_id=_optional_uuid(metadata.get("content_snapshot_id")),
                    segment_id=_optional_uuid(metadata.get("source_content_segment_id")),
                    metadata=sanitize_metadata(metadata),
                )
            )
        return rows, sorted(set(warnings))

    def _evidence_gaps(self, plan_items: list[ResearchPlanItem], claims: list[ClaimContext]) -> list[str]:
        gaps = [
            item.item_key
            for item in plan_items
            if item.is_required and item.status is ResearchPlanItemStatus.PENDING
        ]
        gaps.extend(
            str(claim.id)
            for claim in claims
            if claim.validation_state is ClaimValidationState.INSUFFICIENT_EVIDENCE
        )
        return sorted(set(gaps))

    def _completion_assessment(
        self,
        claims: list[ClaimContext],
        evidence_gaps: list[str],
        unresolved_contradictions: list[uuid.UUID],
    ) -> ResearchCompletionAssessment:
        if any(claim.human_review_requested for claim in claims):
            return ResearchCompletionAssessment.HUMAN_REVIEW_REQUIRED
        if unresolved_contradictions:
            return ResearchCompletionAssessment.UNRESOLVED_CONTRADICTION
        if evidence_gaps:
            return ResearchCompletionAssessment.NEEDS_EVIDENCE
        if not claims:
            return ResearchCompletionAssessment.INCOMPLETE
        return ResearchCompletionAssessment.COMPLETE

    def _coerce_provider_proposal(
        self,
        provider_result: ProviderNarrativeSynthesisResult,
        limits: NarrativeSynthesisLimits,
    ) -> NarrativeProposal:
        proposal = (
            provider_result.proposal
            if isinstance(provider_result.proposal, NarrativeProposal)
            else NarrativeProposal.model_validate(provider_result.proposal)
        )
        if len(proposal.all_findings()) > limits.max_findings * 4:
            raise NarrativeSynthesisValidationError("proposal exceeds max findings")
        if len(proposal.assumptions) > limits.max_assumptions:
            raise NarrativeSynthesisValidationError("proposal exceeds max assumptions")
        if len(proposal.limitations) > limits.max_limitations:
            raise NarrativeSynthesisValidationError("proposal exceeds max limitations")
        return proposal

    def _validate_proposal(
        self,
        proposal: NarrativeProposal,
        context: SynthesisContext,
        limits: NarrativeSynthesisLimits,
    ) -> dict[str, object]:
        allowed_claim_ids = {claim.id for claim in context.claims}
        allowed_conclusion_ids = {conclusion.id for conclusion in context.conclusions}
        allowed_evidence_ids = {evidence.id for evidence in context.evidence}
        referenced_claim_ids: set[uuid.UUID] = set(proposal.executive_summary_claim_ids)
        referenced_conclusion_ids: set[uuid.UUID] = set(proposal.executive_summary_conclusion_ids)
        referenced_evidence_ids: set[uuid.UUID] = set()

        errors: list[str] = []
        if proposal.completion_assessment is not context.completion_assessment:
            errors.append("proposal changed completion assessment")
        if not set(proposal.executive_summary_claim_ids).issubset(allowed_claim_ids):
            errors.append("executive summary references unknown Claim")
        if not set(proposal.executive_summary_conclusion_ids).issubset(allowed_conclusion_ids):
            errors.append("executive summary references unknown Conclusion")

        claim_state = {claim.id: claim.validation_state for claim in context.claims}
        for section, finding in proposal.all_findings():
            finding_claims = set(finding.claim_ids)
            finding_conclusions = set(finding.conclusion_ids)
            finding_evidence = set(finding.evidence_ids)
            referenced_claim_ids.update(finding_claims)
            referenced_conclusion_ids.update(finding_conclusions)
            referenced_evidence_ids.update(finding_evidence)
            if not finding_claims.issubset(allowed_claim_ids):
                errors.append(f"{section}:{finding.finding_key} references unknown Claim")
            if not finding_conclusions.issubset(allowed_conclusion_ids):
                errors.append(f"{section}:{finding.finding_key} references unknown Conclusion")
            if not finding_evidence.issubset(allowed_evidence_ids):
                errors.append(f"{section}:{finding.finding_key} references unknown Evidence")
            for claim_id in finding.claim_ids:
                state = claim_state.get(claim_id)
                if state is not None and state.value not in finding.validation_summary:
                    errors.append(
                        f"{section}:{finding.finding_key} omits validation state {state.value}"
                    )
                if state in {
                    ClaimValidationState.UNASSESSED,
                    ClaimValidationState.INSUFFICIENT_EVIDENCE,
                    ClaimValidationState.CONTESTED,
                    ClaimValidationState.CONTRADICTED,
                    ClaimValidationState.HUMAN_REVIEW_PENDING,
                } and _contains_certainty_upgrade(finding.text):
                    errors.append(f"{section}:{finding.finding_key} upgrades validation certainty")
            if section != "contradictions" and _contains_recommendation_language(finding.text):
                errors.append(f"{section}:{finding.finding_key} contains recommendation language")

        contradiction_claim_ids = {
            claim.id
            for claim in context.claims
            if claim.validation_state in {ClaimValidationState.CONTESTED, ClaimValidationState.CONTRADICTED}
        }
        proposal_contradiction_ids = {
            claim_id for finding in proposal.contradictions for claim_id in finding.claim_ids
        }
        if not contradiction_claim_ids.issubset(proposal_contradiction_ids):
            errors.append("proposal omits required contradiction section material")
        if context.evidence_gaps and not proposal.evidence_gaps:
            errors.append("proposal omits evidence gaps")
        if proposal.completion_assessment is ResearchCompletionAssessment.UNRESOLVED_CONTRADICTION and not proposal.contradictions:
            errors.append("unresolved contradiction completion assessment lacks contradiction details")
        if proposal.completion_assessment is ResearchCompletionAssessment.NEEDS_EVIDENCE and not proposal.evidence_gaps:
            errors.append("needs-evidence completion assessment lacks evidence gaps")
        if len(render_markdown_report(proposal, context)) > limits.max_report_chars:
            errors.append("rendered report exceeds max report length")
        if errors:
            raise NarrativeSynthesisValidationError("; ".join(errors))
        return {
            "valid": True,
            "checks": [
                "canonical_claim_ids",
                "canonical_conclusion_ids",
                "canonical_evidence_ids",
                "material_findings_grounded",
                "validation_state_fidelity",
                "contradiction_preservation",
                "evidence_gap_preservation",
                "completion_assessment_fidelity",
                "no_recommendation_findings",
            ],
            "referenced_claim_ids": sorted(str(item) for item in referenced_claim_ids),
            "referenced_conclusion_ids": sorted(str(item) for item in referenced_conclusion_ids),
            "referenced_evidence_ids": sorted(str(item) for item in referenced_evidence_ids),
        }

    def _persist_request(
        self,
        request: NarrativeSynthesisRequest,
        context: SynthesisContext,
        *,
        status: NarrativeSynthesisRequestStatus,
        provider_id: str,
        provider_model: str | None = None,
        provider_response_id: str | None = None,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
        provider_metadata: dict[str, object] | None = None,
        usage_metadata: dict[str, object] | None = None,
        cost_metadata: dict[str, object] | None = None,
    ) -> NarrativeSynthesisRequestRecord:
        record = NarrativeSynthesisRequestRecord(
            research_run_id=context.research_run_id,
            report_purpose=request.report_purpose,
            intended_audience=request.intended_audience,
            requested_report_format=request.requested_report_format,
            focus_areas=request.focus_areas,
            maximum_length=request.maximum_length,
            include_sections=request.include_sections,
            exclude_sections=request.exclude_sections,
            tone_style=sanitize_metadata(request.tone_style),
            temporal_framing=request.temporal_framing,
            provider_id=provider_id,
            provider_model=provider_model,
            provider_response_id=provider_response_id,
            synthesis_method_version=self.settings.narrative_synthesis_method_version,
            prompt_version=self.settings.narrative_synthesis_prompt_version,
            schema_version=self.settings.narrative_synthesis_schema_version,
            status=status,
            warning_count=len(warnings or []),
            error_count=len(errors or []),
            warnings=warnings or [],
            errors=errors or [],
            request_payload=request.model_dump(mode="json"),
            context_payload=context.model_dump(mode="json"),
            validation_result={"valid": status is NarrativeSynthesisRequestStatus.COMPLETED},
            provider_metadata=sanitize_metadata(provider_metadata or {}),
            usage_metadata=sanitize_metadata(usage_metadata or {}),
            cost_metadata=sanitize_metadata(cost_metadata or {}),
            request_metadata=sanitize_metadata(request.metadata),
            completed_at=utc_now() if status is NarrativeSynthesisRequestStatus.FAILED else None,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def _persist_proposal(
        self,
        request_record: NarrativeSynthesisRequestRecord,
        provider_result: ProviderNarrativeSynthesisResult,
        proposal: NarrativeProposal,
        *,
        status: NarrativeSynthesisProposalStatus,
        validation_result: dict[str, object],
        errors: list[str],
    ) -> NarrativeSynthesisProposalRecord:
        referenced_claim_ids = validation_result.get("referenced_claim_ids") or [
            str(item) for item in _proposal_claim_ids(proposal)
        ]
        referenced_conclusion_ids = validation_result.get("referenced_conclusion_ids") or [
            str(item) for item in _proposal_conclusion_ids(proposal)
        ]
        referenced_evidence_ids = validation_result.get("referenced_evidence_ids") or [
            str(item) for item in _proposal_evidence_ids(proposal)
        ]
        record = NarrativeSynthesisProposalRecord(
            request=request_record,
            research_run_id=request_record.research_run_id,
            provider_id=provider_result.provider_id,
            provider_model=provider_result.provider_model,
            provider_response_id=provider_result.provider_response_id,
            synthesis_method_version=self.settings.narrative_synthesis_method_version,
            prompt_version=self.settings.narrative_synthesis_prompt_version,
            schema_version=self.settings.narrative_synthesis_schema_version,
            status=status,
            proposal_payload=proposal.model_dump(mode="json"),
            referenced_claim_ids=referenced_claim_ids,
            referenced_conclusion_ids=referenced_conclusion_ids,
            referenced_evidence_ids=referenced_evidence_ids,
            validation_result=validation_result,
            warning_count=len(proposal.warnings) + len(provider_result.warnings),
            error_count=len(errors),
            warnings=sorted(set(proposal.warnings + provider_result.warnings)),
            errors=errors,
            provider_metadata=sanitize_metadata(provider_result.provider_metadata),
        )
        if status is NarrativeSynthesisProposalStatus.REJECTED_INVALID_GROUNDING:
            record.rejected_at = utc_now()
            record.rejection_reason = errors[0] if errors else "invalid grounding"
        self.session.add(record)
        self.session.flush()
        for section, finding in proposal.all_findings():
            self.session.add(
                NarrativeSynthesisFindingRecord(
                    proposal=record,
                    research_run_id=record.research_run_id,
                    finding_key=finding.finding_key,
                    section=section,
                    text=finding.text,
                    claim_ids=[str(item) for item in finding.claim_ids],
                    conclusion_ids=[str(item) for item in finding.conclusion_ids],
                    evidence_ids=[str(item) for item in finding.evidence_ids],
                    validation_summary=finding.validation_summary,
                    warnings=finding.warnings,
                )
            )
        self.session.flush()
        return record

    def _get_proposal_record(self, proposal_id: uuid.UUID | str) -> NarrativeSynthesisProposalRecord:
        proposal = self.session.execute(
            select(NarrativeSynthesisProposalRecord)
            .where(NarrativeSynthesisProposalRecord.id == uuid.UUID(str(proposal_id)))
            .options(
                selectinload(NarrativeSynthesisProposalRecord.findings),
                selectinload(NarrativeSynthesisProposalRecord.report),
            )
        ).scalar_one_or_none()
        if proposal is None:
            raise NarrativeSynthesisValidationError(f"Narrative synthesis proposal not found: {proposal_id}")
        return proposal

    def _report_for_proposal(self, proposal_id: uuid.UUID) -> NarrativeResearchReport | None:
        return self.session.execute(
            select(NarrativeResearchReport).where(NarrativeResearchReport.proposal_id == proposal_id)
        ).scalar_one_or_none()

    def _proposal_read(self, proposal: NarrativeSynthesisProposalRecord) -> NarrativeProposalRead:
        return NarrativeProposalRead(
            id=proposal.id,
            synthesis_request_id=proposal.synthesis_request_id,
            research_run_id=proposal.research_run_id,
            provider_id=proposal.provider_id,
            provider_model=proposal.provider_model,
            status=proposal.status,
            proposal=NarrativeProposal.model_validate(proposal.proposal_payload),
            referenced_claim_ids=[uuid.UUID(value) for value in proposal.referenced_claim_ids],
            referenced_conclusion_ids=[uuid.UUID(value) for value in proposal.referenced_conclusion_ids],
            referenced_evidence_ids=[uuid.UUID(value) for value in proposal.referenced_evidence_ids],
            validation_result=proposal.validation_result,
            warnings=proposal.warnings,
            errors=proposal.errors,
            rejection_reason=proposal.rejection_reason,
            published_at=proposal.published_at,
            created_at=proposal.created_at,
        )

    def _publication_result(
        self,
        proposal: NarrativeSynthesisProposalRecord,
        report: NarrativeResearchReport,
    ) -> NarrativePublicationResult:
        return NarrativePublicationResult(
            proposal_id=proposal.id,
            report_id=report.id,
            status=proposal.status,
            artifact_path=report.artifact_path,
            artifact_sha256=report.artifact_sha256,
            artifact_size_bytes=report.artifact_size_bytes,
        )

    def _limits(self) -> NarrativeSynthesisLimits:
        return NarrativeSynthesisLimits(
            max_claims=self.settings.narrative_synthesis_max_claims,
            max_evidence_items=self.settings.narrative_synthesis_max_evidence_items,
            max_evidence_chars=self.settings.narrative_synthesis_max_evidence_chars,
            max_findings=self.settings.narrative_synthesis_max_findings,
            max_report_chars=self.settings.narrative_synthesis_max_report_chars,
            max_assumptions=self.settings.narrative_synthesis_max_assumptions,
            max_limitations=self.settings.narrative_synthesis_max_limitations,
        )


def render_markdown_report(proposal: NarrativeProposal, context: SynthesisContext) -> str:
    """Render a deterministic Markdown report from a validated structured proposal."""

    lines: list[str] = [
        f"# {_text(proposal.title)}",
        "",
        "## Executive Summary",
        _with_refs(
            proposal.executive_summary,
            proposal.executive_summary_claim_ids,
            proposal.executive_summary_conclusion_ids,
        ),
        "",
        "## Research Question",
        _text(proposal.research_question),
        "",
        "## Scope",
        _text(context.scope or "Not specified."),
        "",
        "## Method",
        _text(proposal.scope_method),
        "",
        "## Key Findings",
    ]
    lines.extend(_finding_lines(proposal.key_findings))
    lines.extend(["", "## Supporting Findings"])
    lines.extend(_finding_lines(proposal.claim_based_findings))
    if proposal.contradictions:
        lines.extend(["", "## Contested / Contradicted Findings"])
        lines.extend(_finding_lines(proposal.contradictions))
    if proposal.evidence_gaps:
        lines.extend(["", "## Evidence Gaps"])
        lines.extend(f"- {_text(gap)}" for gap in proposal.evidence_gaps)
    if proposal.assumptions:
        lines.extend(["", "## Assumptions"])
        lines.extend(f"- {_text(item)}" for item in proposal.assumptions)
    lines.extend(["", "## Limitations"])
    limitations = proposal.limitations or ["No additional narrative limitations supplied."]
    lines.extend(f"- {_text(item)}" for item in limitations)
    if proposal.conclusions:
        lines.extend(["", "## Conclusions"])
        lines.extend(_finding_lines(proposal.conclusions))
    lines.extend(
        [
            "",
            "## Completion Status",
            f"- Assessment: `{proposal.completion_assessment.value}`",
        ]
    )
    if context.warnings:
        lines.append("- Warnings: " + ", ".join(f"`{warning}`" for warning in context.warnings))
    lines.extend(["", "## Traceability / References"])
    lines.extend(_traceability_lines(context))
    lines.extend(
        [
            "",
            "## Research Metadata",
            f"- Research run: `{context.research_run_id}`",
            f"- Public id: `{context.public_id}`",
            f"- Research method: `{context.research_method_version}`",
            f"- Narrative method: `{context.method_version}`",
            f"- Schema: `{context.schema_version}`",
            f"- Context built at: `{context.created_at.isoformat()}`",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _finding_lines(findings: list[NarrativeFinding]) -> list[str]:
    if not findings:
        return ["- None recorded."]
    return [
        "- "
        + _with_refs(
            finding.text,
            finding.claim_ids,
            finding.conclusion_ids,
            finding.evidence_ids,
            finding.validation_summary,
        )
        for finding in findings
    ]


def _traceability_lines(context: SynthesisContext) -> list[str]:
    evidence_by_id = {evidence.id: evidence for evidence in context.evidence}
    source_by_id = {source.id: source for source in context.sources}
    lines: list[str] = []
    for claim in context.claims:
        lines.append(f"- [Claim: {claim.id}] `{claim.validation_state.value}` {_text(claim.statement)}")
        for link in claim.evidence:
            evidence = evidence_by_id.get(link.evidence_id)
            if evidence is None:
                continue
            source = source_by_id.get(evidence.source_id)
            source_label = source.canonical_locator if source is not None else str(evidence.source_id)
            lines.append(
                f"  - {link.relation.value} [Evidence: {evidence.id}] "
                f"[Source: {evidence.source_id}] {_text(source_label)}"
            )
    return lines or ["- No traceability rows recorded."]


def _with_refs(
    text: str,
    claim_ids: list[uuid.UUID],
    conclusion_ids: list[uuid.UUID],
    evidence_ids: list[uuid.UUID] | None = None,
    validation_summary: str | None = None,
) -> str:
    refs = [f"[Claim: {item}]" for item in claim_ids]
    refs.extend(f"[Conclusion: {item}]" for item in conclusion_ids)
    refs.extend(f"[Evidence: {item}]" for item in evidence_ids or [])
    if validation_summary:
        refs.append(f"(validation: {validation_summary})")
    return " ".join([_text(text), *refs])


def _write_report_artifact(
    *,
    root: Path,
    research_run_id: uuid.UUID,
    report_id: uuid.UUID,
    content: bytes,
) -> str:
    relative_path = Path("research-reports") / str(research_run_id) / str(report_id) / "report.md"
    target = _safe_path(root, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise NarrativeSynthesisPublicationError(
            f"Report artifact write failed: {exc.__class__.__name__}"
        ) from exc
    return relative_path.as_posix()


def _safe_path(root: Path, relative_path: Path) -> Path:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise NarrativeSynthesisPublicationError("Report artifact path must stay inside artifact root")
    resolved_root = root.resolve()
    candidate = (resolved_root / relative_path).resolve()
    if resolved_root != candidate and resolved_root not in candidate.parents:
        raise NarrativeSynthesisPublicationError("Report artifact path escaped artifact root")
    return candidate


def _proposal_claim_ids(proposal: NarrativeProposal) -> set[uuid.UUID]:
    ids = set(proposal.executive_summary_claim_ids)
    for _section, finding in proposal.all_findings():
        ids.update(finding.claim_ids)
    return ids


def _proposal_conclusion_ids(proposal: NarrativeProposal) -> set[uuid.UUID]:
    ids = set(proposal.executive_summary_conclusion_ids)
    for _section, finding in proposal.all_findings():
        ids.update(finding.conclusion_ids)
    return ids


def _proposal_evidence_ids(proposal: NarrativeProposal) -> set[uuid.UUID]:
    ids: set[uuid.UUID] = set()
    for _section, finding in proposal.all_findings():
        ids.update(finding.evidence_ids)
    return ids


def _ordered_unique(values) -> list:
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _optional_uuid(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _contains_certainty_upgrade(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ["established", "proven", "confirmed", "settled"])


def _contains_recommendation_language(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ["buy ", "sell ", "trade ", "recommend", "should "])


def _text(value: object) -> str:
    text = " ".join(str(value).replace("\r", " ").split())
    return text.replace("<", "&lt;").replace(">", "&gt;")
