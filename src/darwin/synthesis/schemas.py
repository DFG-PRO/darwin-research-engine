"""Pydantic contracts for deterministic structured synthesis."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from darwin.construction import ClaimProvenanceRead
from darwin.db.models import (
    ConclusionClaimRelation,
    ConclusionStatus,
    ResearchCompletionAssessment,
)


class ConclusionClaimLinkRequest(BaseModel):
    """Explicit caller-supplied relationship between a conclusion and a claim."""

    conclusion_id: uuid.UUID
    claim_id: uuid.UUID
    relation: ConclusionClaimRelation
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConclusionClaimRead(BaseModel):
    """Inspectable conclusion-to-claim dependency."""

    conclusion_id: uuid.UUID
    claim_id: uuid.UUID
    relation: ConclusionClaimRelation
    claim_validation_state: str
    warnings: list[str]


class ConclusionSynthesisRead(BaseModel):
    """Conclusion plus explicit claim dependencies."""

    conclusion_id: uuid.UUID
    statement: str
    status: ConclusionStatus
    claim_links: list[ConclusionClaimRead]
    warnings: list[str]


class StructuredSynthesisResult(BaseModel):
    """Evidence-grounded structured synthesis read model."""

    synthesis_record_id: uuid.UUID
    research_run_id: uuid.UUID
    research_question: str
    research_method_version: str
    synthesis_method_version: str
    completion_assessment: ResearchCompletionAssessment
    source_count: int
    evidence_count: int
    claim_count: int
    conclusion_count: int
    claims: list[ClaimProvenanceRead]
    conclusions: list[ConclusionSynthesisRead]
    evidence_gaps: list[str]
    unresolved_contradictions: list[str]
    warnings: list[str]
    created_at: datetime
