"""Pydantic contracts for explicit evidence-to-claim construction."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from darwin.db.models import (
    ClaimConstructionMethod,
    ClaimEvidenceRelation,
    ClaimType,
    ClaimValidationReasonCode,
    ClaimValidationState,
    SourceLineageType,
)


class ClaimEvidenceSelection(BaseModel):
    """Explicit evidence selection for constructing one claim."""

    evidence_id: uuid.UUID
    relation: ClaimEvidenceRelation


class ClaimConstructionRequest(BaseModel):
    """Explicit request to construct one claim from selected evidence."""

    model_config = ConfigDict(str_strip_whitespace=True)

    research_run_id: uuid.UUID
    statement: str = Field(
        min_length=1,
        validation_alias=AliasChoices("statement", "claim_statement"),
    )
    claim_type: ClaimType = ClaimType.PROPOSITION
    evidence: list[ClaimEvidenceSelection] = Field(min_length=1)
    construction_method: ClaimConstructionMethod = ClaimConstructionMethod.MANUAL_EXPLICIT
    metadata: dict[str, Any] = Field(default_factory=dict)
    auto_validate: bool = True

    @model_validator(mode="after")
    def validate_unique_evidence(self) -> ClaimConstructionRequest:
        evidence_ids = [selection.evidence_id for selection in self.evidence]
        duplicates = {evidence_id for evidence_id in evidence_ids if evidence_ids.count(evidence_id) > 1}
        if duplicates:
            raise ValueError("evidence selections must be unique")
        return self


class EvidenceProvenanceRead(BaseModel):
    """Evidence plus source/snapshot/segment provenance for claim views."""

    evidence_id: uuid.UUID
    relation: ClaimEvidenceRelation
    excerpt: str
    source_id: uuid.UUID
    source_locator: str
    source_title: str | None
    source_lineage_type: SourceLineageType | None
    origin_source_id: uuid.UUID | None
    snapshot_id: uuid.UUID | None
    segment_id: uuid.UUID | None
    evidence_locator: str | None


class ClaimConstructionResult(BaseModel):
    """Result of explicit claim construction and validation."""

    construction_record_id: uuid.UUID
    claim_id: uuid.UUID
    statement: str
    claim_type: ClaimType
    construction_method: ClaimConstructionMethod
    construction_method_version: str
    evidence: list[EvidenceProvenanceRead]
    validation_state: ClaimValidationState | None
    validation_reason_codes: list[ClaimValidationReasonCode]
    warnings: list[str]


class ClaimProvenanceRead(BaseModel):
    """Inspectable claim view grounded in explicit evidence provenance."""

    claim_id: uuid.UUID
    statement: str
    claim_type: ClaimType
    validation_state: ClaimValidationState | None
    validation_reason_codes: list[ClaimValidationReasonCode]
    construction_method: ClaimConstructionMethod | None
    construction_method_version: str | None
    evidence: list[EvidenceProvenanceRead]
    supporting_evidence_count: int
    contradicting_evidence_count: int
    contextual_evidence_count: int
    independent_source_count: int
    unresolved_contradiction: bool
    human_review_requested: bool
    human_validation_present: bool
    warnings: list[str]
