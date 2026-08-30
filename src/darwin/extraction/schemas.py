"""Pydantic contracts for assisted evidence extraction."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from darwin.db.models import (
    EvidenceCandidateAcceptanceMode,
    EvidenceCandidateStatus,
    EvidenceType,
)


class AssistedExtractionLimits(BaseModel):
    """Bounded controls for assisted extraction."""

    max_segments: int = Field(default=5, ge=1)
    max_candidates: int = Field(default=5, ge=1)
    max_segment_chars: int = Field(default=4000, ge=1)
    max_total_request_chars: int = Field(default=12000, ge=1)


class AssistedEvidenceExtractionRequest(BaseModel):
    """Caller-controlled request for evidence candidate proposals."""

    model_config = ConfigDict(str_strip_whitespace=True)

    research_run_id: uuid.UUID
    research_plan_item_id: uuid.UUID
    source_id: uuid.UUID
    snapshot_id: uuid.UUID
    segment_ids: list[uuid.UUID] = Field(default_factory=list)
    segment_order_start: int | None = Field(default=None, ge=0)
    segment_order_end: int | None = Field(default=None, ge=0)
    research_objective: str = Field(min_length=1)
    evidence_requirement: str = Field(min_length=1)
    freshness_start: date | None = None
    freshness_end: date | None = None
    expected_evidence_type: EvidenceType | None = None
    extraction_instructions: str | None = None
    max_candidate_count: int = Field(default=3, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_selection(self) -> AssistedEvidenceExtractionRequest:
        has_segments = bool(self.segment_ids)
        has_range = self.segment_order_start is not None or self.segment_order_end is not None
        if has_segments == has_range:
            raise ValueError("supply either segment_ids or segment_order_start/segment_order_end")
        if has_range:
            if self.segment_order_start is None or self.segment_order_end is None:
                raise ValueError("segment_order_start and segment_order_end must be supplied together")
            if self.segment_order_start > self.segment_order_end:
                raise ValueError("segment_order_start cannot be after segment_order_end")
        if self.freshness_start and self.freshness_end and self.freshness_start > self.freshness_end:
            raise ValueError("freshness_start cannot be after freshness_end")
        return self


class SegmentForExtraction(BaseModel):
    """Provider-safe source segment payload."""

    id: uuid.UUID
    segment_identifier: str
    segment_order: int
    text: str
    locator: str | None = None


class EvidenceCandidateProposal(BaseModel):
    """Strict provider candidate schema before persistence."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_key: str = Field(min_length=1, max_length=64)
    source_content_segment_id: uuid.UUID
    exact_excerpt: str = Field(min_length=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=1)
    proposed_evidence_type: EvidenceType = EvidenceType.EXCERPT
    relevance_explanation: str = Field(min_length=1)
    supports_research_task: bool = True
    temporal_applicability: str | None = None
    provider_warnings: list[str] = Field(default_factory=list)
    extraction_method_version: str = Field(min_length=1)

    @field_validator("provider_warnings", mode="before")
    @classmethod
    def clean_warnings(cls, value: list[str] | None) -> list[str]:
        return [str(item).strip() for item in value or [] if str(item).strip()]

    @model_validator(mode="after")
    def validate_span(self) -> EvidenceCandidateProposal:
        if self.start_offset >= self.end_offset:
            raise ValueError("start_offset must be before end_offset")
        return self


class ProviderEvidenceExtractionResult(BaseModel):
    """Provider envelope around evidence candidates."""

    provider_id: str
    provider_model: str | None = None
    provider_response_id: str | None = None
    candidates: list[EvidenceCandidateProposal] | list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    usage_metadata: dict[str, Any] = Field(default_factory=dict)
    cost_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class EvidenceCandidateRead(BaseModel):
    """Read model for persisted evidence candidates."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extraction_request_id: uuid.UUID
    research_run_id: uuid.UUID
    research_plan_item_id: uuid.UUID
    source_id: uuid.UUID
    snapshot_id: uuid.UUID
    source_content_segment_id: uuid.UUID
    evidence_id: uuid.UUID | None
    candidate_key: str
    exact_excerpt: str
    start_offset: int
    end_offset: int
    proposed_evidence_type: EvidenceType
    relevance_explanation: str
    supports_research_task: bool
    temporal_applicability: str | None
    status: EvidenceCandidateStatus
    acceptance_mode: EvidenceCandidateAcceptanceMode | None
    accepted_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    provider_warnings: list[str]
    structural_validation: dict[str, Any]
    grounding_validation: dict[str, Any]
    created_at: datetime


class AssistedExtractionResult(BaseModel):
    """Result returned after candidate proposal persistence."""

    extraction_request_id: uuid.UUID
    provider_id: str
    provider_model: str | None
    candidate_count: int
    warnings: list[str]
    errors: list[str]
    candidates: list[EvidenceCandidateRead]


class EvidenceCandidateAcceptanceResult(BaseModel):
    """Result returned after explicit candidate acceptance."""

    candidate_id: uuid.UUID
    evidence_id: uuid.UUID
    acceptance_mode: EvidenceCandidateAcceptanceMode
    status: EvidenceCandidateStatus


class EvidenceCandidateRejectionResult(BaseModel):
    """Result returned after explicit candidate rejection."""

    candidate_id: uuid.UUID
    status: EvidenceCandidateStatus
    rejection_reason: str
