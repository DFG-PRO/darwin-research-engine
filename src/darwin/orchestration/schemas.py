"""Pydantic contracts for manual research orchestration."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from darwin.db.models import (
    ClaimEvidenceRelation,
    ClaimStatus,
    ClaimType,
    ClaimValidationReasonCode,
    ClaimValidationState,
    ConclusionStatus,
    EvidenceType,
    ResearchCompletionAssessment,
    ResearchPlanItemStatus,
    ResearchPlanPriority,
    ResearchRunStatus,
    SourceLineageType,
    SourceType,
)


class FramingInput(BaseModel):
    original_question: str | None = None
    normalized_question: str | None = None
    objective: str | None = None
    scope: str = "Supplied research material only."
    exclusions: list[str] = Field(default_factory=list)
    key_decision_criteria: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    required_evidence_categories: list[str] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanItemInput(BaseModel):
    item_key: str
    requirement: str
    category: str
    priority: ResearchPlanPriority = ResearchPlanPriority.MEDIUM
    required: bool = True
    expected_source_type: SourceType | None = None
    notes: str | None = None


class SourceInput(BaseModel):
    source_key: str
    source_type: SourceType
    canonical_locator: str
    title: str | None = None
    publisher: str | None = None
    publication_date: date | None = None
    origin_source_key: str | None = None
    source_lineage_type: SourceLineageType | None = None
    content_fingerprint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceInput(BaseModel):
    evidence_key: str
    source_key: str
    evidence_type: EvidenceType
    statement: str
    source_locator: str | None = None
    plan_item_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimEvidenceInput(BaseModel):
    evidence_key: str
    relation: ClaimEvidenceRelation


class ClaimInput(BaseModel):
    claim_key: str
    statement: str
    claim_type: ClaimType = ClaimType.PROPOSITION
    status: ClaimStatus = ClaimStatus.PROPOSED
    confidence: Decimal | float | None = None
    evidence: list[ClaimEvidenceInput] = Field(default_factory=list)


class ConclusionInput(BaseModel):
    statement: str
    status: ConclusionStatus = ConclusionStatus.DRAFT
    confidence: Decimal | float | None = None


class ManualResearchInput(BaseModel):
    research_question: str
    public_id: str | None = None
    framing: FramingInput | None = None
    plan_items: list[PlanItemInput] = Field(default_factory=list)
    sources: list[SourceInput] = Field(default_factory=list)
    evidence: list[EvidenceInput] = Field(default_factory=list)
    claims: list[ClaimInput] = Field(default_factory=list)
    conclusions: list[ConclusionInput] = Field(default_factory=list)
    human_review_claim_keys: list[str] = Field(default_factory=list)


class FramingResult(BaseModel):
    original_question: str
    normalized_question: str
    objective: str
    scope: str
    exclusions: list[str]
    key_decision_criteria: list[str]
    assumptions: list[str]
    required_evidence_categories: list[str]
    completion_criteria: list[str]


class PlanItemResult(BaseModel):
    item_key: str
    requirement: str
    category: str
    required: bool
    status: ResearchPlanItemStatus


class ClaimResult(BaseModel):
    claim_id: uuid.UUID
    claim_key: str
    statement: str
    validation_state: ClaimValidationState
    reason_codes: list[ClaimValidationReasonCode]
    supporting_evidence_count: int
    contradicting_evidence_count: int
    contextual_evidence_count: int


class ConclusionResult(BaseModel):
    id: uuid.UUID
    statement: str
    status: ConclusionStatus


class ResearchOrchestrationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    research_run_id: uuid.UUID
    public_id: str
    research_question: str
    research_method_version: str
    run_status: ResearchRunStatus
    framing: FramingResult
    plan_items: list[PlanItemResult]
    plan_completion: dict[str, int]
    source_count: int
    evidence_count: int
    claim_results: list[ClaimResult]
    unresolved_contradictions: list[str]
    evidence_gaps: list[str]
    assumptions: list[str]
    conclusions: list[ConclusionResult]
    warnings: list[str]
    completion_assessment: ResearchCompletionAssessment
    synthesis_record_id: uuid.UUID
    created_at: datetime
    completed_at: datetime | None
