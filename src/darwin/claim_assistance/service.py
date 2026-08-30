"""Controlled assisted Claim construction service."""

from __future__ import annotations

import uuid

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from darwin.acquisition.normalization import sanitize_metadata
from darwin.claim_assistance.errors import (
    ClaimCandidateAcceptanceError,
    ClaimCandidateRejectionError,
    ClaimCandidateValidationError,
    ClaimConstructionProviderError,
    ClaimConstructionProviderTimeout,
)
from darwin.claim_assistance.providers import (
    ClaimConstructionProvider,
    build_claim_construction_provider,
)
from darwin.claim_assistance.schemas import (
    AssistedClaimConstructionLimits,
    AssistedClaimConstructionRequest,
    AssistedClaimConstructionResult,
    ClaimCandidateAcceptanceResult,
    ClaimCandidateEvidenceRead,
    ClaimCandidateProposal,
    ClaimCandidateRead,
    ClaimCandidateRejectionResult,
    EvidenceForClaimConstruction,
    ProviderClaimConstructionResult,
)
from darwin.config import Settings
from darwin.db.models import (
    AssistedClaimConstructionRequest as AssistedClaimConstructionRecord,
    AssistedClaimConstructionRequestStatus,
    Claim,
    ClaimCandidateAcceptanceMode,
    ClaimCandidateEvidence,
    ClaimCandidateProposal as ClaimCandidateRecord,
    ClaimCandidateStatus,
    ClaimConstructionEvidence,
    ClaimConstructionMethod,
    ClaimConstructionRecord,
    ClaimEvidenceRelation,
    ClaimStatus,
    Evidence,
    ResearchPlanItem,
    ResearchRun,
    utc_now,
)
from darwin.research import ResearchService


class AssistedClaimConstructionService:
    """Propose, persist, accept, and reject Evidence-grounded Claim candidates."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
        provider: ClaimConstructionProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider = provider or build_claim_construction_provider(settings)
        self.research_service = ResearchService(session)

    def propose_claims(
        self,
        request: AssistedClaimConstructionRequest,
    ) -> AssistedClaimConstructionResult:
        """Persist provider Claim candidates without creating canonical Claims."""

        limits = self._limits()
        self._validate_request_limits(request, limits)
        run, plan_item, evidence = self._load_and_validate_context(request, limits)
        provider_evidence = [
            EvidenceForClaimConstruction(
                id=item.id,
                statement=item.statement,
                source_id=item.source_id,
                source_locator=item.source_locator,
                metadata=sanitize_metadata(item.evidence_metadata),
            )
            for item in evidence
        ]
        try:
            provider_result = self.provider.propose_claims(request, provider_evidence, limits)
            candidates = self._validate_provider_candidates(provider_result, request, evidence, limits)
        except ClaimConstructionProviderTimeout as exc:
            record = self._persist_request(
                request,
                run,
                plan_item,
                evidence,
                status=AssistedClaimConstructionRequestStatus.FAILED,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc) or "claim construction provider timed out"],
            )
            raise ClaimConstructionProviderTimeout(record.errors[0]) from exc
        except ClaimConstructionProviderError as exc:
            record = self._persist_request(
                request,
                run,
                plan_item,
                evidence,
                status=AssistedClaimConstructionRequestStatus.FAILED,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc) or "claim construction provider failed"],
            )
            raise ClaimConstructionProviderError(record.errors[0]) from exc
        except (ValidationError, ValueError) as exc:
            record = self._persist_request(
                request,
                run,
                plan_item,
                evidence,
                status=AssistedClaimConstructionRequestStatus.FAILED,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc)],
            )
            raise ClaimCandidateValidationError(record.errors[0]) from exc

        record = self._persist_request(
            request,
            run,
            plan_item,
            evidence,
            status=AssistedClaimConstructionRequestStatus.COMPLETED,
            provider_id=provider_result.provider_id,
            provider_model=provider_result.provider_model,
            provider_response_id=provider_result.provider_response_id,
            warnings=provider_result.warnings,
            provider_metadata=provider_result.provider_metadata,
            usage_metadata=provider_result.usage_metadata,
            cost_metadata=provider_result.cost_metadata,
        )
        persisted = self._persist_candidates(record, candidates, provider_result)
        record.candidate_count = len(persisted)
        record.warning_count = len(record.warnings)
        record.completed_at = utc_now()
        self.session.flush()
        return self._result(record, persisted)

    def list_candidates(self, construction_request_id: uuid.UUID | str | None = None) -> list[ClaimCandidateRead]:
        statement = (
            select(ClaimCandidateRecord)
            .options(selectinload(ClaimCandidateRecord.evidence_links))
            .order_by(ClaimCandidateRecord.created_at)
        )
        if construction_request_id is not None:
            statement = statement.where(
                ClaimCandidateRecord.construction_request_id == uuid.UUID(str(construction_request_id))
            )
        candidates = self.session.scalars(statement).all()
        return [self._candidate_read(candidate) for candidate in candidates]

    def accept_claim_candidate(
        self,
        candidate_id: uuid.UUID | str,
        *,
        acceptance_mode: ClaimCandidateAcceptanceMode = ClaimCandidateAcceptanceMode.MANUAL,
    ) -> ClaimCandidateAcceptanceResult:
        candidate = self._get_candidate(candidate_id)
        if candidate.status is ClaimCandidateStatus.ACCEPTED:
            if candidate.claim_id is None:
                raise ClaimCandidateAcceptanceError("Accepted candidate is missing Claim linkage")
            return ClaimCandidateAcceptanceResult(
                candidate_id=candidate.id,
                claim_id=candidate.claim_id,
                acceptance_mode=candidate.acceptance_mode or acceptance_mode,
                status=candidate.status,
            )
        if candidate.status is not ClaimCandidateStatus.VALIDATED:
            raise ClaimCandidateAcceptanceError(
                f"Candidate {candidate.id} is not eligible for acceptance from {candidate.status.value}"
            )

        try:
            with self.session.begin_nested():
                evidence_roles = self._revalidate_candidate_evidence(candidate)
                duplicate = self._find_accepted_duplicate(candidate, evidence_roles)
                if duplicate is not None:
                    raise ClaimCandidateAcceptanceError(
                        f"Matching candidate already accepted as Claim {duplicate.claim_id}"
                    )
                claim = self.research_service.register_claim(
                    research_run_id=candidate.research_run_id,
                    statement=candidate.proposed_claim_text,
                    claim_type=candidate.proposed_claim_type,
                    status=ClaimStatus.PROPOSED,
                )
                for link in evidence_roles:
                    self.research_service.link_claim_evidence(
                        claim_id=claim.id,
                        evidence_id=link.evidence_id,
                        relation=link.relation,
                    )
                construction_record = ClaimConstructionRecord(
                    research_run_id=candidate.research_run_id,
                    claim_id=claim.id,
                    construction_method=ClaimConstructionMethod.MANUAL_EXPLICIT,
                    construction_method_version=candidate.request.construction_method_version,
                    claim_statement=candidate.proposed_claim_text,
                    evidence_count=len(evidence_roles),
                    warning_count=len(candidate.provider_warnings),
                    warnings=candidate.provider_warnings,
                    construction_metadata={
                        "assisted": True,
                        "claim_candidate_id": str(candidate.id),
                        "construction_request_id": str(candidate.construction_request_id),
                        "research_plan_item_id": str(candidate.research_plan_item_id),
                    },
                )
                self.session.add(construction_record)
                self.session.flush()
                for link in evidence_roles:
                    evidence = self.session.get(Evidence, link.evidence_id)
                    self.session.add(
                        ClaimConstructionEvidence(
                            construction_record=construction_record,
                            evidence=evidence,
                            relation=link.relation,
                        )
                    )
                candidate.claim = claim
                candidate.status = ClaimCandidateStatus.ACCEPTED
                candidate.acceptance_mode = acceptance_mode
                candidate.accepted_at = utc_now()
                candidate.request.accepted_candidate_count += 1
                self.session.flush()
        except ClaimCandidateAcceptanceError:
            raise
        except Exception as exc:
            raise ClaimCandidateAcceptanceError(str(exc)) from exc

        return ClaimCandidateAcceptanceResult(
            candidate_id=candidate.id,
            claim_id=candidate.claim_id,
            acceptance_mode=acceptance_mode,
            status=candidate.status,
        )

    def reject_claim_candidate(
        self,
        candidate_id: uuid.UUID | str,
        *,
        reason: str,
    ) -> ClaimCandidateRejectionResult:
        candidate = self._get_candidate(candidate_id)
        reason = reason.strip()
        if not reason:
            raise ClaimCandidateRejectionError("Rejection reason is required")
        if candidate.status is ClaimCandidateStatus.ACCEPTED:
            raise ClaimCandidateRejectionError("Accepted candidates cannot be rejected")
        if candidate.status is ClaimCandidateStatus.REJECTED:
            return ClaimCandidateRejectionResult(
                candidate_id=candidate.id,
                status=candidate.status,
                rejection_reason=candidate.rejection_reason or reason,
            )
        candidate.status = ClaimCandidateStatus.REJECTED
        candidate.rejection_reason = reason
        candidate.rejected_at = utc_now()
        self.session.flush()
        return ClaimCandidateRejectionResult(
            candidate_id=candidate.id,
            status=candidate.status,
            rejection_reason=reason,
        )

    def _validate_request_limits(
        self,
        request: AssistedClaimConstructionRequest,
        limits: AssistedClaimConstructionLimits,
    ) -> None:
        if request.max_candidate_count > limits.max_candidates:
            raise ClaimCandidateValidationError("request exceeds max candidate count")
        if len(request.evidence_ids) > limits.max_evidence_items:
            raise ClaimCandidateValidationError("request exceeds max evidence items")

    def _load_and_validate_context(
        self,
        request: AssistedClaimConstructionRequest,
        limits: AssistedClaimConstructionLimits,
    ) -> tuple[ResearchRun, ResearchPlanItem, list[Evidence]]:
        run = self.session.get(ResearchRun, request.research_run_id)
        if run is None:
            raise ClaimCandidateValidationError(f"ResearchRun not found: {request.research_run_id}")
        plan_item = self.session.get(ResearchPlanItem, request.research_plan_item_id)
        if plan_item is None:
            raise ClaimCandidateValidationError(f"ResearchPlanItem not found: {request.research_plan_item_id}")
        if plan_item.research_run_id != run.id:
            raise ClaimCandidateValidationError("ResearchPlanItem belongs to a different research run")
        evidence = self.session.scalars(
            select(Evidence)
            .where(Evidence.id.in_(request.evidence_ids))
            .options(selectinload(Evidence.source))
        ).all()
        if len(evidence) != len(request.evidence_ids):
            raise ClaimCandidateValidationError("One or more Evidence records were not found")
        for item in evidence:
            if item.research_run_id != run.id:
                raise ClaimCandidateValidationError("Evidence belongs to a different research run")
            if item.source is None or item.source_id is None:
                raise ClaimCandidateValidationError("Evidence lacks source provenance")
        if sum(len(item.statement) for item in evidence) > limits.max_evidence_chars:
            raise ClaimCandidateValidationError("request exceeds max evidence characters")
        return run, plan_item, evidence

    def _validate_provider_candidates(
        self,
        provider_result: ProviderClaimConstructionResult,
        request: AssistedClaimConstructionRequest,
        evidence: list[Evidence],
        limits: AssistedClaimConstructionLimits,
    ) -> list[ClaimCandidateProposal]:
        if len(provider_result.candidates) > request.max_candidate_count:
            raise ValueError("provider returned more candidates than requested")
        if len(provider_result.candidates) > limits.max_candidates:
            raise ValueError("provider returned more candidates than configured maximum")
        allowed_evidence_ids = {item.id for item in evidence}
        keys: set[str] = set()
        candidates: list[ClaimCandidateProposal] = []
        for raw in provider_result.candidates:
            candidate = raw if isinstance(raw, ClaimCandidateProposal) else ClaimCandidateProposal.model_validate(raw)
            self._validate_candidate_text(candidate, limits)
            if candidate.candidate_key in keys:
                raise ValueError("provider returned duplicate candidate keys")
            keys.add(candidate.candidate_key)
            role_ids = {role.evidence_id for role in candidate.evidence_roles()}
            if not role_ids.issubset(allowed_evidence_ids):
                raise ValueError("candidate references Evidence outside the construction request")
            if len(candidate.qualifiers) > limits.max_qualifiers:
                raise ValueError("candidate exceeds max qualifiers")
            if len(candidate.assumptions) > limits.max_assumptions:
                raise ValueError("candidate exceeds max assumptions")
            candidates.append(candidate)
        return candidates

    def _validate_candidate_text(
        self,
        candidate: ClaimCandidateProposal,
        limits: AssistedClaimConstructionLimits,
    ) -> None:
        text = candidate.proposed_claim_text.strip()
        if not text:
            raise ValueError("candidate claim text cannot be empty")
        if len(text) > min(limits.max_claim_chars, self.settings.claim_statement_max_chars):
            raise ValueError("candidate claim text exceeds configured maximum length")
        if "\n" in text or text.count(";") > 2:
            raise ValueError("candidate claim text is not structurally atomic")
        lowered = text.lower()
        if "recommend" in lowered or "should " in lowered:
            raise ValueError("candidate claim text must not contain recommendation language")

    def _persist_request(
        self,
        request: AssistedClaimConstructionRequest,
        run: ResearchRun,
        plan_item: ResearchPlanItem,
        evidence: list[Evidence],
        *,
        status: AssistedClaimConstructionRequestStatus,
        provider_id: str,
        provider_model: str | None = None,
        provider_response_id: str | None = None,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
        provider_metadata: dict[str, object] | None = None,
        usage_metadata: dict[str, object] | None = None,
        cost_metadata: dict[str, object] | None = None,
    ) -> AssistedClaimConstructionRecord:
        record = AssistedClaimConstructionRecord(
            research_run=run,
            research_plan_item=plan_item,
            evidence_ids=[str(item.id) for item in evidence],
            research_objective=request.research_objective,
            construction_instruction=request.construction_instruction,
            expected_claim_type=request.expected_claim_type,
            temporal_scope=request.temporal_scope,
            max_candidate_count=request.max_candidate_count,
            provider_id=provider_id,
            provider_model=provider_model,
            provider_response_id=provider_response_id,
            construction_method_version=self.settings.assisted_claim_construction_method_version,
            prompt_version=self.settings.assisted_claim_construction_prompt_version,
            schema_version=self.settings.assisted_claim_construction_schema_version,
            status=status,
            warning_count=len(warnings or []),
            error_count=len(errors or []),
            warnings=warnings or [],
            errors=errors or [],
            request_payload=request.model_dump(mode="json"),
            validation_result={"valid": status is AssistedClaimConstructionRequestStatus.COMPLETED},
            provider_metadata=sanitize_metadata(provider_metadata or {}),
            usage_metadata=sanitize_metadata(usage_metadata or {}),
            cost_metadata=sanitize_metadata(cost_metadata or {}),
            request_metadata=sanitize_metadata(request.metadata),
            completed_at=utc_now() if status is AssistedClaimConstructionRequestStatus.FAILED else None,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def _persist_candidates(
        self,
        record: AssistedClaimConstructionRecord,
        candidates: list[ClaimCandidateProposal],
        provider_result: ProviderClaimConstructionResult,
    ) -> list[ClaimCandidateRecord]:
        persisted: list[ClaimCandidateRecord] = []
        for candidate in candidates:
            model = ClaimCandidateRecord(
                request=record,
                research_run_id=record.research_run_id,
                research_plan_item_id=record.research_plan_item_id,
                candidate_key=candidate.candidate_key,
                proposed_claim_text=candidate.proposed_claim_text,
                proposed_claim_type=candidate.proposed_claim_type,
                temporal_scope=candidate.temporal_scope,
                qualifiers=candidate.qualifiers,
                assumptions=candidate.assumptions,
                construction_rationale=candidate.construction_rationale,
                status=ClaimCandidateStatus.VALIDATED,
                provider_warnings=candidate.provider_warnings,
                validation_result={"valid": True, "checks": self._validation_checks()},
                provider_metadata=sanitize_metadata(provider_result.provider_metadata),
            )
            self.session.add(model)
            self.session.flush()
            for role in candidate.evidence_roles():
                self.session.add(
                    ClaimCandidateEvidence(
                        candidate=model,
                        evidence_id=role.evidence_id,
                        relation=role.relation,
                    )
                )
            persisted.append(model)
        self.session.flush()
        return persisted

    def _get_candidate(self, candidate_id: uuid.UUID | str) -> ClaimCandidateRecord:
        candidate = self.session.execute(
            select(ClaimCandidateRecord)
            .where(ClaimCandidateRecord.id == uuid.UUID(str(candidate_id)))
            .options(
                selectinload(ClaimCandidateRecord.request),
                selectinload(ClaimCandidateRecord.evidence_links),
            )
        ).scalar_one_or_none()
        if candidate is None:
            raise ClaimCandidateAcceptanceError(f"Claim candidate not found: {candidate_id}")
        return candidate

    def _revalidate_candidate_evidence(
        self,
        candidate: ClaimCandidateRecord,
    ) -> list[ClaimCandidateEvidence]:
        roles = list(candidate.evidence_links)
        if not roles:
            candidate.status = ClaimCandidateStatus.REJECTED_INVALID_PROVENANCE
            candidate.rejected_at = utc_now()
            candidate.rejection_reason = "candidate has no Evidence linkage"
            self.session.flush()
            raise ClaimCandidateAcceptanceError("Candidate has no Evidence linkage")
        allowed_ids = {uuid.UUID(value) for value in candidate.request.evidence_ids}
        for role in roles:
            evidence = self.session.get(Evidence, role.evidence_id)
            if evidence is None:
                raise ClaimCandidateAcceptanceError(f"Evidence not found: {role.evidence_id}")
            if evidence.research_run_id != candidate.research_run_id:
                raise ClaimCandidateAcceptanceError("Evidence belongs to a different research run")
            if role.evidence_id not in allowed_ids:
                raise ClaimCandidateAcceptanceError("Candidate Evidence was not in original request")
        return roles

    def _find_accepted_duplicate(
        self,
        candidate: ClaimCandidateRecord,
        roles: list[ClaimCandidateEvidence],
    ) -> ClaimCandidateRecord | None:
        candidate_evidence_set = {(role.evidence_id, role.relation) for role in roles}
        possible = self.session.scalars(
            select(ClaimCandidateRecord)
            .where(
                ClaimCandidateRecord.id != candidate.id,
                ClaimCandidateRecord.research_run_id == candidate.research_run_id,
                ClaimCandidateRecord.proposed_claim_text == candidate.proposed_claim_text,
                ClaimCandidateRecord.status == ClaimCandidateStatus.ACCEPTED,
                ClaimCandidateRecord.claim_id.is_not(None),
            )
            .options(selectinload(ClaimCandidateRecord.evidence_links))
        ).all()
        for other in possible:
            other_set = {(role.evidence_id, role.relation) for role in other.evidence_links}
            if other_set == candidate_evidence_set:
                return other
        return None

    def _validation_checks(self) -> list[str]:
        return [
            "canonical_evidence_ids",
            "evidence_belongs_to_research_run",
            "candidate_has_evidence_linkage",
            "bounded_claim_length",
            "no_list_or_newline_claim",
            "no_recommendation_language",
            "bounded_candidate_count",
        ]

    def _candidate_read(self, candidate: ClaimCandidateRecord) -> ClaimCandidateRead:
        return ClaimCandidateRead(
            id=candidate.id,
            construction_request_id=candidate.construction_request_id,
            research_run_id=candidate.research_run_id,
            research_plan_item_id=candidate.research_plan_item_id,
            claim_id=candidate.claim_id,
            candidate_key=candidate.candidate_key,
            proposed_claim_text=candidate.proposed_claim_text,
            proposed_claim_type=candidate.proposed_claim_type,
            temporal_scope=candidate.temporal_scope,
            qualifiers=candidate.qualifiers,
            assumptions=candidate.assumptions,
            construction_rationale=candidate.construction_rationale,
            status=candidate.status,
            acceptance_mode=candidate.acceptance_mode,
            accepted_at=candidate.accepted_at,
            rejected_at=candidate.rejected_at,
            rejection_reason=candidate.rejection_reason,
            provider_warnings=candidate.provider_warnings,
            validation_result=candidate.validation_result,
            evidence=[
                ClaimCandidateEvidenceRead(evidence_id=link.evidence_id, relation=link.relation)
                for link in candidate.evidence_links
            ],
            created_at=candidate.created_at,
        )

    def _result(
        self,
        record: AssistedClaimConstructionRecord,
        candidates: list[ClaimCandidateRecord],
    ) -> AssistedClaimConstructionResult:
        return AssistedClaimConstructionResult(
            construction_request_id=record.id,
            provider_id=record.provider_id,
            provider_model=record.provider_model,
            candidate_count=len(candidates),
            warnings=record.warnings,
            errors=record.errors,
            candidates=[self._candidate_read(candidate) for candidate in candidates],
        )

    def _limits(self) -> AssistedClaimConstructionLimits:
        return AssistedClaimConstructionLimits(
            max_evidence_items=self.settings.assisted_claim_construction_max_evidence_items,
            max_evidence_chars=self.settings.assisted_claim_construction_max_evidence_chars,
            max_candidates=self.settings.assisted_claim_construction_max_candidates,
            max_claim_chars=self.settings.assisted_claim_construction_max_claim_chars,
            max_qualifiers=self.settings.assisted_claim_construction_max_qualifiers,
            max_assumptions=self.settings.assisted_claim_construction_max_assumptions,
        )
