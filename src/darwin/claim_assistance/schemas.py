"""Pydantic contracts for assisted claim construction."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from darwin.db.models import (
    ClaimCandidateAcceptanceMode,
    ClaimCandidateStatus,
    ClaimEvidenceRelation,
    ClaimType,
)


class AssistedClaimConstructionLimits(BaseModel):
    """Bounded controls for assisted claim construction."""

    max_evidence_items: int = Field(default=8, ge=1)
    max_evidence_chars: int = Field(default=12000, ge=1)
    max_candidates: int = Field(default=5, ge=1)
    max_claim_chars: int = Field(default=1000, ge=1)
    max_qualifiers: int = Field(default=6, ge=0)
    max_assumptions: int = Field(default=6, ge=0)


class AssistedClaimConstructionRequest(BaseModel):
    """Caller-controlled request for Claim candidate proposals."""

    model_config = ConfigDict(str_strip_whitespace=True)

    research_run_id: uuid.UUID
    research_plan_item_id: uuid.UUID
    evidence_ids: list[uuid.UUID] = Field(min_length=1)
    research_objective: str = Field(min_length=1)
    construction_instruction: str = Field(min_length=1)
    expected_claim_type: ClaimType | None = None
    temporal_scope: str | None = None
    max_candidate_count: int = Field(default=3, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_unique_evidence(self) -> AssistedClaimConstructionRequest:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids must be unique")
        return self


class EvidenceForClaimConstruction(BaseModel):
    """Provider-safe Evidence payload."""

    id: uuid.UUID
    statement: str
    source_id: uuid.UUID
    source_locator: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimCandidateEvidenceRole(BaseModel):
    """Provider-proposed role for one canonical Evidence item."""

    evidence_id: uuid.UUID
    relation: ClaimEvidenceRelation


class ClaimCandidateProposal(BaseModel):
    """Strict provider claim candidate schema before persistence."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_key: str = Field(min_length=1, max_length=64)
    proposed_claim_text: str = Field(min_length=1)
    proposed_claim_type: ClaimType = ClaimType.PROPOSITION
    supporting_evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    contradicting_evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    contextual_evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    temporal_scope: str | None = None
    qualifiers: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    construction_rationale: str = Field(min_length=1)
    provider_warnings: list[str] = Field(default_factory=list)
    construction_method_version: str = Field(min_length=1)

    @field_validator("qualifiers", "assumptions", "provider_warnings", mode="before")
    @classmethod
    def clean_string_list(cls, value: list[str] | None) -> list[str]:
        return [str(item).strip() for item in value or [] if str(item).strip()]

    @model_validator(mode="after")
    def validate_evidence_links(self) -> ClaimCandidateProposal:
        evidence_ids = (
            self.supporting_evidence_ids
            + self.contradicting_evidence_ids
            + self.contextual_evidence_ids
        )
        if not evidence_ids:
            raise ValueError("claim candidates require at least one Evidence link")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs may appear only once per candidate")
        return self

    def evidence_roles(self) -> list[ClaimCandidateEvidenceRole]:
        roles: list[ClaimCandidateEvidenceRole] = []
        roles.extend(
            ClaimCandidateEvidenceRole(
                evidence_id=evidence_id,
                relation=ClaimEvidenceRelation.SUPPORTS,
            )
            for evidence_id in self.supporting_evidence_ids
        )
        roles.extend(
            ClaimCandidateEvidenceRole(
                evidence_id=evidence_id,
                relation=ClaimEvidenceRelation.CONTRADICTS,
            )
            for evidence_id in self.contradicting_evidence_ids
        )
        roles.extend(
            ClaimCandidateEvidenceRole(
                evidence_id=evidence_id,
                relation=ClaimEvidenceRelation.CONTEXTUALIZES,
            )
            for evidence_id in self.contextual_evidence_ids
        )
        return roles


class ProviderClaimConstructionResult(BaseModel):
    """Provider envelope around Claim candidates."""

    provider_id: str
    provider_model: str | None = None
    provider_response_id: str | None = None
    candidates: list[ClaimCandidateProposal] | list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    usage_metadata: dict[str, Any] = Field(default_factory=dict)
    cost_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ClaimCandidateEvidenceRead(BaseModel):
    """Read model for candidate Evidence roles."""

    model_config = ConfigDict(from_attributes=True)

    evidence_id: uuid.UUID
    relation: ClaimEvidenceRelation


class ClaimCandidateRead(BaseModel):
    """Read model for persisted Claim candidates."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    construction_request_id: uuid.UUID
    research_run_id: uuid.UUID
    research_plan_item_id: uuid.UUID
    claim_id: uuid.UUID | None
    candidate_key: str
    proposed_claim_text: str
    proposed_claim_type: ClaimType
    temporal_scope: str | None
    qualifiers: list[str]
    assumptions: list[str]
    construction_rationale: str
    status: ClaimCandidateStatus
    acceptance_mode: ClaimCandidateAcceptanceMode | None
    accepted_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    provider_warnings: list[str]
    validation_result: dict[str, Any]
    evidence: list[ClaimCandidateEvidenceRead]
    created_at: datetime


class AssistedClaimConstructionResult(BaseModel):
    """Result returned after candidate persistence."""

    construction_request_id: uuid.UUID
    provider_id: str
    provider_model: str | None
    candidate_count: int
    warnings: list[str]
    errors: list[str]
    candidates: list[ClaimCandidateRead]


class ClaimCandidateAcceptanceResult(BaseModel):
    """Result returned after explicit Claim candidate acceptance."""

    candidate_id: uuid.UUID
    claim_id: uuid.UUID
    acceptance_mode: ClaimCandidateAcceptanceMode
    status: ClaimCandidateStatus


class ClaimCandidateRejectionResult(BaseModel):
    """Result returned after explicit Claim candidate rejection."""

    candidate_id: uuid.UUID
    status: ClaimCandidateStatus
    rejection_reason: str
