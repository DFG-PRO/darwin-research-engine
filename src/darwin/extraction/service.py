"""Controlled assisted evidence extraction service."""

from __future__ import annotations

import uuid

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from darwin.acquisition.normalization import sanitize_metadata
from darwin.config import Settings
from darwin.content.hashing import sha256_text
from darwin.db.models import (
    AssistedEvidenceExtractionRequest as AssistedExtractionRequestRecord,
    AssistedExtractionRequestStatus,
    Evidence,
    EvidenceCandidateAcceptanceMode,
    EvidenceCandidateProposal as EvidenceCandidateRecord,
    EvidenceCandidateStatus,
    EvidenceExtractionRecord,
    EvidenceExtractionStatus,
    ResearchPlanItem,
    ResearchPlanItemStatus,
    ResearchRun,
    Source,
    SourceContentSegment,
    SourceContentSnapshot,
    utc_now,
)
from darwin.extraction.errors import (
    EvidenceCandidateAcceptanceError,
    EvidenceCandidateRejectionError,
    ExtractionProviderError,
    ExtractionProviderTimeout,
    ExtractionValidationError,
)
from darwin.extraction.providers import (
    EvidenceExtractionProvider,
    build_evidence_extraction_provider,
)
from darwin.extraction.schemas import (
    AssistedEvidenceExtractionRequest,
    AssistedExtractionLimits,
    AssistedExtractionResult,
    EvidenceCandidateAcceptanceResult,
    EvidenceCandidateProposal,
    EvidenceCandidateRead,
    EvidenceCandidateRejectionResult,
    ProviderEvidenceExtractionResult,
    SegmentForExtraction,
)
from darwin.research import ResearchService


class AssistedEvidenceExtractionService:
    """Propose, persist, accept, and reject grounded evidence candidates."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
        provider: EvidenceExtractionProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider = provider or build_evidence_extraction_provider(settings)
        self.research_service = ResearchService(session)

    def propose_evidence(
        self,
        request: AssistedEvidenceExtractionRequest,
    ) -> AssistedExtractionResult:
        """Persist provider evidence candidates; never create canonical Evidence."""

        limits = self._limits()
        self._validate_request_limits(request, limits)
        run, plan_item, source, snapshot, segments = self._load_and_validate_context(request, limits)
        provider_segments = [
            SegmentForExtraction(
                id=segment.id,
                segment_identifier=segment.segment_identifier,
                segment_order=segment.segment_order,
                text=segment.text,
                locator=segment.locator,
            )
            for segment in segments
        ]

        try:
            provider_result = self.provider.propose_candidates(request, provider_segments, limits)
            candidates = self._validate_provider_candidates(provider_result, request, segments, limits)
        except ExtractionProviderTimeout as exc:
            record = self._persist_request(
                request,
                run,
                plan_item,
                source,
                snapshot,
                segments,
                status=AssistedExtractionRequestStatus.FAILED,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc) or "evidence extraction provider timed out"],
            )
            raise ExtractionProviderTimeout(record.errors[0]) from exc
        except ExtractionProviderError as exc:
            record = self._persist_request(
                request,
                run,
                plan_item,
                source,
                snapshot,
                segments,
                status=AssistedExtractionRequestStatus.FAILED,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc) or "evidence extraction provider failed"],
            )
            raise ExtractionProviderError(record.errors[0]) from exc
        except (ValidationError, ValueError) as exc:
            record = self._persist_request(
                request,
                run,
                plan_item,
                source,
                snapshot,
                segments,
                status=AssistedExtractionRequestStatus.FAILED,
                provider_id=getattr(self.provider, "identifier", "unknown"),
                errors=[str(exc)],
            )
            raise ExtractionValidationError(record.errors[0]) from exc

        record = self._persist_request(
            request,
            run,
            plan_item,
            source,
            snapshot,
            segments,
            status=AssistedExtractionRequestStatus.COMPLETED,
            provider_id=provider_result.provider_id,
            provider_model=provider_result.provider_model,
            provider_response_id=provider_result.provider_response_id,
            warnings=provider_result.warnings,
            provider_metadata=provider_result.provider_metadata,
            usage_metadata=provider_result.usage_metadata,
            cost_metadata=provider_result.cost_metadata,
        )
        persisted = self._persist_candidates(record, candidates, segments, provider_result)
        record.candidate_count = len(persisted)
        record.warning_count = len(record.warnings)
        record.completed_at = utc_now()
        self.session.flush()
        return self._result(record, persisted)

    def list_candidates(
        self,
        extraction_request_id: uuid.UUID | str | None = None,
    ) -> list[EvidenceCandidateRead]:
        statement = select(EvidenceCandidateRecord).order_by(EvidenceCandidateRecord.created_at)
        if extraction_request_id is not None:
            statement = statement.where(
                EvidenceCandidateRecord.extraction_request_id == uuid.UUID(str(extraction_request_id))
            )
        candidates = self.session.scalars(statement).all()
        return [EvidenceCandidateRead.model_validate(candidate) for candidate in candidates]

    def accept_candidate(
        self,
        candidate_id: uuid.UUID | str,
        *,
        acceptance_mode: EvidenceCandidateAcceptanceMode = EvidenceCandidateAcceptanceMode.MANUAL,
    ) -> EvidenceCandidateAcceptanceResult:
        candidate = self._get_candidate(candidate_id)
        if candidate.status is EvidenceCandidateStatus.ACCEPTED:
            if candidate.evidence_id is None:
                raise EvidenceCandidateAcceptanceError("Accepted candidate is missing Evidence linkage")
            return EvidenceCandidateAcceptanceResult(
                candidate_id=candidate.id,
                evidence_id=candidate.evidence_id,
                acceptance_mode=candidate.acceptance_mode or acceptance_mode,
                status=candidate.status,
            )
        if candidate.status is not EvidenceCandidateStatus.VALIDATED:
            raise EvidenceCandidateAcceptanceError(
                f"Candidate {candidate.id} is not eligible for acceptance from {candidate.status.value}"
            )

        try:
            with self.session.begin_nested():
                segment = self._revalidate_candidate_grounding(candidate)
                duplicate = self._find_accepted_duplicate(candidate)
                if duplicate is not None:
                    raise EvidenceCandidateAcceptanceError(
                        f"Matching candidate already accepted as Evidence {duplicate.evidence_id}"
                    )
                evidence = self.research_service.register_evidence(
                    research_run_id=candidate.research_run_id,
                    source_id=candidate.source_id,
                    evidence_type=candidate.proposed_evidence_type,
                    statement=candidate.exact_excerpt,
                    source_locator=self._selection_locator(segment, candidate),
                    metadata={
                        "assisted_extraction_candidate_id": str(candidate.id),
                        "assisted_extraction_request_id": str(candidate.extraction_request_id),
                        "research_plan_item_id": str(candidate.research_plan_item_id),
                        "content_snapshot_id": str(candidate.snapshot_id),
                        "source_content_segment_id": str(candidate.source_content_segment_id),
                        "selection": {
                            "relative_char_start": candidate.start_offset,
                            "relative_char_end": candidate.end_offset,
                            "absolute_char_start": segment.char_start + candidate.start_offset,
                            "absolute_char_end": segment.char_start + candidate.end_offset,
                        },
                        "extraction_method_version": candidate.request.extraction_method_version,
                    },
                )
                extraction_record = EvidenceExtractionRecord(
                    research_run_id=candidate.research_run_id,
                    source_id=candidate.source_id,
                    snapshot_id=candidate.snapshot_id,
                    segment_id=candidate.source_content_segment_id,
                    evidence_id=evidence.id,
                    extraction_status=EvidenceExtractionStatus.EXTRACTED,
                    extraction_method_version=candidate.request.extraction_method_version,
                    selected_text=candidate.exact_excerpt,
                    selected_text_fingerprint=sha256_text(candidate.exact_excerpt),
                    selection_locator=self._selection_locator(segment, candidate),
                    char_start=segment.char_start + candidate.start_offset,
                    char_end=segment.char_start + candidate.end_offset,
                    extraction_metadata={
                        "assisted": True,
                        "candidate_id": str(candidate.id),
                        "research_plan_item_id": str(candidate.research_plan_item_id),
                    },
                )
                self.session.add(extraction_record)
                candidate.evidence = evidence
                candidate.status = EvidenceCandidateStatus.ACCEPTED
                candidate.acceptance_mode = acceptance_mode
                candidate.accepted_at = utc_now()
                candidate.request.accepted_candidate_count += 1
                self.session.flush()
        except IntegrityError as exc:
            raise EvidenceCandidateAcceptanceError("Duplicate canonical evidence acceptance") from exc
        except EvidenceCandidateAcceptanceError as exc:
            if "exactly grounded" in str(exc):
                candidate.status = EvidenceCandidateStatus.REJECTED_INVALID_GROUNDING
                candidate.rejected_at = utc_now()
                candidate.rejection_reason = "grounding revalidation failed at acceptance"
                self.session.flush()
            raise
        except Exception as exc:
            raise EvidenceCandidateAcceptanceError(str(exc)) from exc

        return EvidenceCandidateAcceptanceResult(
            candidate_id=candidate.id,
            evidence_id=candidate.evidence_id,
            acceptance_mode=acceptance_mode,
            status=candidate.status,
        )

    def _find_accepted_duplicate(
        self,
        candidate: EvidenceCandidateRecord,
    ) -> EvidenceCandidateRecord | None:
        return self.session.execute(
            select(EvidenceCandidateRecord).where(
                EvidenceCandidateRecord.id != candidate.id,
                EvidenceCandidateRecord.research_run_id == candidate.research_run_id,
                EvidenceCandidateRecord.source_id == candidate.source_id,
                EvidenceCandidateRecord.snapshot_id == candidate.snapshot_id,
                EvidenceCandidateRecord.source_content_segment_id
                == candidate.source_content_segment_id,
                EvidenceCandidateRecord.start_offset == candidate.start_offset,
                EvidenceCandidateRecord.end_offset == candidate.end_offset,
                EvidenceCandidateRecord.exact_excerpt == candidate.exact_excerpt,
                EvidenceCandidateRecord.status == EvidenceCandidateStatus.ACCEPTED,
                EvidenceCandidateRecord.evidence_id.is_not(None),
            )
        ).scalar_one_or_none()

    def reject_candidate(
        self,
        candidate_id: uuid.UUID | str,
        *,
        reason: str,
    ) -> EvidenceCandidateRejectionResult:
        candidate = self._get_candidate(candidate_id)
        reason = reason.strip()
        if not reason:
            raise EvidenceCandidateRejectionError("Rejection reason is required")
        if candidate.status is EvidenceCandidateStatus.ACCEPTED:
            raise EvidenceCandidateRejectionError("Accepted candidates cannot be rejected")
        if candidate.status is EvidenceCandidateStatus.REJECTED:
            return EvidenceCandidateRejectionResult(
                candidate_id=candidate.id,
                status=candidate.status,
                rejection_reason=candidate.rejection_reason or reason,
            )
        candidate.status = EvidenceCandidateStatus.REJECTED
        candidate.rejection_reason = reason
        candidate.rejected_at = utc_now()
        self.session.flush()
        return EvidenceCandidateRejectionResult(
            candidate_id=candidate.id,
            status=candidate.status,
            rejection_reason=reason,
        )

    def _validate_request_limits(
        self,
        request: AssistedEvidenceExtractionRequest,
        limits: AssistedExtractionLimits,
    ) -> None:
        if request.max_candidate_count > limits.max_candidates:
            raise ExtractionValidationError("request exceeds max candidate count")

    def _load_and_validate_context(
        self,
        request: AssistedEvidenceExtractionRequest,
        limits: AssistedExtractionLimits,
    ) -> tuple[ResearchRun, ResearchPlanItem, Source, SourceContentSnapshot, list[SourceContentSegment]]:
        run = self.session.get(ResearchRun, request.research_run_id)
        if run is None:
            raise ExtractionValidationError(f"ResearchRun not found: {request.research_run_id}")
        plan_item = self.session.get(ResearchPlanItem, request.research_plan_item_id)
        if plan_item is None:
            raise ExtractionValidationError(f"ResearchPlanItem not found: {request.research_plan_item_id}")
        if plan_item.research_run_id != run.id:
            raise ExtractionValidationError("ResearchPlanItem belongs to a different research run")
        source = self.session.get(Source, request.source_id)
        if source is None:
            raise ExtractionValidationError(f"Source not found: {request.source_id}")
        snapshot = self.session.get(SourceContentSnapshot, request.snapshot_id)
        if snapshot is None:
            raise ExtractionValidationError(f"SourceContentSnapshot not found: {request.snapshot_id}")
        if snapshot.research_run_id != run.id or snapshot.source_id != source.id:
            raise ExtractionValidationError("SourceContentSnapshot provenance does not match request")

        segments = self._load_segments(request, snapshot)
        if not segments:
            raise ExtractionValidationError("No source content segments selected")
        if len(segments) > limits.max_segments:
            raise ExtractionValidationError("request exceeds max segments")
        total_chars = sum(len(segment.text) for segment in segments)
        if total_chars > limits.max_total_request_chars:
            raise ExtractionValidationError("request exceeds max total segment characters")
        for segment in segments:
            if segment.snapshot_id != snapshot.id or segment.source_id != source.id:
                raise ExtractionValidationError("SourceContentSegment provenance does not match request")
            if len(segment.text) > limits.max_segment_chars:
                raise ExtractionValidationError("request includes segment exceeding max segment characters")
        return run, plan_item, source, snapshot, segments

    def _load_segments(
        self,
        request: AssistedEvidenceExtractionRequest,
        snapshot: SourceContentSnapshot,
    ) -> list[SourceContentSegment]:
        if request.segment_ids:
            segments = self.session.scalars(
                select(SourceContentSegment)
                .where(SourceContentSegment.id.in_(request.segment_ids))
                .order_by(SourceContentSegment.segment_order)
            ).all()
            if len(segments) != len(set(request.segment_ids)):
                raise ExtractionValidationError("One or more source content segments were not found")
            return segments
        return self.session.scalars(
            select(SourceContentSegment)
            .where(
                SourceContentSegment.snapshot_id == snapshot.id,
                SourceContentSegment.segment_order >= request.segment_order_start,
                SourceContentSegment.segment_order <= request.segment_order_end,
            )
            .order_by(SourceContentSegment.segment_order)
        ).all()

    def _validate_provider_candidates(
        self,
        provider_result: ProviderEvidenceExtractionResult,
        request: AssistedEvidenceExtractionRequest,
        segments: list[SourceContentSegment],
        limits: AssistedExtractionLimits,
    ) -> list[tuple[EvidenceCandidateProposal, EvidenceCandidateStatus, dict[str, object]]]:
        if len(provider_result.candidates) > request.max_candidate_count:
            raise ValueError("provider returned more candidates than requested")
        if len(provider_result.candidates) > limits.max_candidates:
            raise ValueError("provider returned more candidates than configured maximum")
        validated: list[tuple[EvidenceCandidateProposal, EvidenceCandidateStatus, dict[str, object]]] = []
        keys: set[str] = set()
        segments_by_id = {segment.id: segment for segment in segments}
        for raw in provider_result.candidates:
            candidate = (
                raw
                if isinstance(raw, EvidenceCandidateProposal)
                else EvidenceCandidateProposal.model_validate(raw)
            )
            if candidate.candidate_key in keys:
                raise ValueError("provider returned duplicate candidate keys")
            keys.add(candidate.candidate_key)
            if candidate.source_content_segment_id not in segments_by_id:
                raise ValueError("candidate references a segment outside the extraction request")
            segment = segments_by_id[candidate.source_content_segment_id]
            grounding = _grounding_result(candidate, segment)
            status = (
                EvidenceCandidateStatus.VALIDATED
                if grounding["valid"]
                else EvidenceCandidateStatus.REJECTED_INVALID_GROUNDING
            )
            validated.append((candidate, status, grounding))
        return validated

    def _persist_request(
        self,
        request: AssistedEvidenceExtractionRequest,
        run: ResearchRun,
        plan_item: ResearchPlanItem,
        source: Source,
        snapshot: SourceContentSnapshot,
        segments: list[SourceContentSegment],
        *,
        status: AssistedExtractionRequestStatus,
        provider_id: str,
        provider_model: str | None = None,
        provider_response_id: str | None = None,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
        provider_metadata: dict[str, object] | None = None,
        usage_metadata: dict[str, object] | None = None,
        cost_metadata: dict[str, object] | None = None,
    ) -> AssistedExtractionRequestRecord:
        record = AssistedExtractionRequestRecord(
            research_run=run,
            research_plan_item=plan_item,
            source=source,
            snapshot=snapshot,
            segment_ids=[str(segment.id) for segment in segments],
            research_objective=request.research_objective,
            evidence_requirement=request.evidence_requirement,
            expected_evidence_type=request.expected_evidence_type,
            extraction_instructions=request.extraction_instructions,
            freshness_start=request.freshness_start,
            freshness_end=request.freshness_end,
            max_candidate_count=request.max_candidate_count,
            provider_id=provider_id,
            provider_model=provider_model,
            provider_response_id=provider_response_id,
            extraction_method_version=self.settings.assisted_evidence_extraction_method_version,
            prompt_version=self.settings.assisted_evidence_extraction_prompt_version,
            schema_version=self.settings.assisted_evidence_extraction_schema_version,
            status=status,
            warning_count=len(warnings or []),
            error_count=len(errors or []),
            warnings=warnings or [],
            errors=errors or [],
            request_payload=request.model_dump(mode="json"),
            validation_result={"valid": status is AssistedExtractionRequestStatus.COMPLETED},
            provider_metadata=sanitize_metadata(provider_metadata or {}),
            usage_metadata=sanitize_metadata(usage_metadata or {}),
            cost_metadata=sanitize_metadata(cost_metadata or {}),
            request_metadata=sanitize_metadata(request.metadata),
            completed_at=utc_now() if status is AssistedExtractionRequestStatus.FAILED else None,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def _persist_candidates(
        self,
        record: AssistedExtractionRequestRecord,
        candidates: list[tuple[EvidenceCandidateProposal, EvidenceCandidateStatus, dict[str, object]]],
        segments: list[SourceContentSegment],
        provider_result: ProviderEvidenceExtractionResult,
    ) -> list[EvidenceCandidateRecord]:
        segments_by_id = {segment.id: segment for segment in segments}
        persisted: list[EvidenceCandidateRecord] = []
        for candidate, status, grounding in candidates:
            segment = segments_by_id[candidate.source_content_segment_id]
            model = EvidenceCandidateRecord(
                request=record,
                research_run_id=record.research_run_id,
                research_plan_item_id=record.research_plan_item_id,
                source_id=record.source_id,
                snapshot_id=record.snapshot_id,
                source_content_segment_id=segment.id,
                candidate_key=candidate.candidate_key,
                exact_excerpt=candidate.exact_excerpt,
                start_offset=candidate.start_offset,
                end_offset=candidate.end_offset,
                proposed_evidence_type=candidate.proposed_evidence_type,
                relevance_explanation=candidate.relevance_explanation,
                supports_research_task=candidate.supports_research_task,
                temporal_applicability=candidate.temporal_applicability,
                status=status,
                rejected_at=utc_now()
                if status is EvidenceCandidateStatus.REJECTED_INVALID_GROUNDING
                else None,
                rejection_reason="exact excerpt does not match canonical segment offsets"
                if status is EvidenceCandidateStatus.REJECTED_INVALID_GROUNDING
                else None,
                provider_warnings=candidate.provider_warnings,
                structural_validation={"valid": True},
                grounding_validation=grounding,
                provider_metadata=sanitize_metadata(provider_result.provider_metadata),
            )
            self.session.add(model)
            persisted.append(model)
        self.session.flush()
        return persisted

    def _get_candidate(self, candidate_id: uuid.UUID | str) -> EvidenceCandidateRecord:
        candidate = self.session.execute(
            select(EvidenceCandidateRecord)
            .where(EvidenceCandidateRecord.id == uuid.UUID(str(candidate_id)))
            .options(selectinload(EvidenceCandidateRecord.request))
        ).scalar_one_or_none()
        if candidate is None:
            raise EvidenceCandidateAcceptanceError(f"Evidence candidate not found: {candidate_id}")
        return candidate

    def _revalidate_candidate_grounding(
        self,
        candidate: EvidenceCandidateRecord,
    ) -> SourceContentSegment:
        segment = self.session.get(SourceContentSegment, candidate.source_content_segment_id)
        if segment is None:
            raise EvidenceCandidateAcceptanceError("Candidate segment no longer exists")
        if segment.snapshot_id != candidate.snapshot_id or segment.source_id != candidate.source_id:
            raise EvidenceCandidateAcceptanceError("Candidate segment provenance no longer matches")
        if candidate.snapshot.research_run_id != candidate.research_run_id:
            raise EvidenceCandidateAcceptanceError("Candidate snapshot provenance no longer matches")
        grounding = _grounding_result(candidate, segment)
        candidate.grounding_validation = grounding
        if not grounding["valid"]:
            raise EvidenceCandidateAcceptanceError("Candidate excerpt is not exactly grounded")
        return segment

    def _selection_locator(
        self,
        segment: SourceContentSegment,
        candidate: EvidenceCandidateRecord,
    ) -> str:
        return f"{segment.locator}:chars={candidate.start_offset}-{candidate.end_offset}"

    def _result(
        self,
        record: AssistedExtractionRequestRecord,
        candidates: list[EvidenceCandidateRecord],
    ) -> AssistedExtractionResult:
        return AssistedExtractionResult(
            extraction_request_id=record.id,
            provider_id=record.provider_id,
            provider_model=record.provider_model,
            candidate_count=len(candidates),
            warnings=record.warnings,
            errors=record.errors,
            candidates=[EvidenceCandidateRead.model_validate(candidate) for candidate in candidates],
        )

    def _limits(self) -> AssistedExtractionLimits:
        return AssistedExtractionLimits(
            max_segments=self.settings.assisted_evidence_extraction_max_segments,
            max_candidates=self.settings.assisted_evidence_extraction_max_candidates,
            max_segment_chars=self.settings.assisted_evidence_extraction_max_segment_chars,
            max_total_request_chars=self.settings.assisted_evidence_extraction_max_total_request_chars,
        )


def _grounding_result(candidate, segment: SourceContentSegment) -> dict[str, object]:
    if candidate.end_offset > len(segment.text):
        return {
            "valid": False,
            "reason": "offsets exceed segment length",
            "segment_length": len(segment.text),
        }
    selected = segment.text[candidate.start_offset : candidate.end_offset]
    valid = selected == candidate.exact_excerpt
    return {
        "valid": valid,
        "reason": "exact_match" if valid else "excerpt_mismatch",
        "selected_fingerprint": sha256_text(selected) if selected else None,
        "excerpt_fingerprint": sha256_text(candidate.exact_excerpt),
    }
