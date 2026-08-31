"""Pydantic contracts for controlled research loop execution."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from darwin.db.models import (
    ResearchCompletionAssessment,
    ResearchLoopExecutionMode,
    ResearchLoopState,
    ResearchLoopStopReason,
    SourceType,
)


class ResearchLoopBudgets(BaseModel):
    """Hard budget counters for one synchronous research loop execution."""

    max_iterations: int = Field(default=1, ge=1)
    max_searches: int = Field(default=1, ge=0)
    max_sources: int = Field(default=3, ge=0)
    max_fetched_sources: int = Field(default=2, ge=0)
    max_segments: int = Field(default=3, ge=0)
    max_evidence_candidates: int = Field(default=3, ge=0)
    max_accepted_evidence: int = Field(default=2, ge=0)
    max_claim_candidates: int = Field(default=2, ge=0)
    max_accepted_claims: int = Field(default=2, ge=0)
    max_provider_calls: int = Field(default=12, ge=0)
    max_runtime_seconds: float = Field(default=30.0, ge=0.1)
    max_tokens: int | None = Field(default=None, ge=0)
    max_cost: float | None = Field(default=None, ge=0)


class ResearchLoopCounters(BaseModel):
    """Consumed counters for a research loop execution."""

    iterations: int = 0
    searches: int = 0
    source_candidates: int = 0
    sources_registered: int = 0
    content_fetches: int = 0
    segments_processed: int = 0
    evidence_proposals: int = 0
    accepted_evidence: int = 0
    claim_proposals: int = 0
    accepted_claims: int = 0
    provider_calls: int = 0
    tokens: int = 0
    cost: float = 0.0


class ResearchLoopRequest(BaseModel):
    """Caller-controlled request for bounded end-to-end research execution."""

    model_config = ConfigDict(str_strip_whitespace=True)

    research_question: str = Field(min_length=1, max_length=1000)
    objective: str | None = None
    scope: str | None = None
    exclusions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    freshness_start: date | None = None
    freshness_end: date | None = None
    desired_source_types: list[SourceType] = Field(default_factory=lambda: [SourceType.WEB_PAGE])
    planning_provider: Literal["fake", "openai"] = "fake"
    acquisition_provider: Literal["fake", "brave"] = "fake"
    evidence_extraction_provider: Literal["fake", "openai"] = "fake"
    claim_construction_provider: Literal["fake", "openai"] = "fake"
    synthesis_provider: Literal["fake", "openai"] = "fake"
    execution_mode: ResearchLoopExecutionMode
    budgets: ResearchLoopBudgets = Field(default_factory=ResearchLoopBudgets)
    publish_report: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("exclusions", "assumptions", mode="before")
    @classmethod
    def clean_string_list(cls, value: list[str] | None) -> list[str]:
        return [str(item).strip() for item in value or [] if str(item).strip()]

    @model_validator(mode="after")
    def validate_freshness_window(self) -> ResearchLoopRequest:
        if (
            self.freshness_start is not None
            and self.freshness_end is not None
            and self.freshness_start > self.freshness_end
        ):
            raise ValueError("freshness_start must be before or equal to freshness_end")
        if not self.desired_source_types:
            raise ValueError("desired_source_types cannot be empty")
        return self


class ResearchLoopEventRead(BaseModel):
    """Read model for append-only loop events."""

    id: uuid.UUID
    execution_id: uuid.UUID
    sequence: int
    stage: ResearchLoopState
    event_type: str
    status: str
    message: str | None
    code: str | None
    linked_object_ids: dict[str, Any]
    counters: dict[str, Any]
    warnings: list[str]
    errors: list[str]
    created_at: datetime


class ResearchLoopResult(BaseModel):
    """Summary returned after loop start/resume/show."""

    execution_id: uuid.UUID
    research_run_id: uuid.UUID | None
    state: ResearchLoopState
    current_stage: str
    stop_reason: ResearchLoopStopReason | None
    completion_assessment: ResearchCompletionAssessment | None
    iteration_count: int
    budgets: ResearchLoopBudgets
    counters: ResearchLoopCounters
    plan_coverage: dict[str, int]
    source_count: int
    accepted_evidence_count: int
    accepted_claim_count: int
    validation_distribution: dict[str, int]
    contradictions: list[str]
    gaps: list[str]
    synthesis_proposal_id: uuid.UUID | None
    report_id: uuid.UUID | None
    report_artifact_path: str | None
    warnings: list[str]
    errors: list[str]
    next_required_action: str | None


TERMINAL_LOOP_STATES = {
    ResearchLoopState.COMPLETED,
    ResearchLoopState.STOPPED_NEEDS_EVIDENCE,
    ResearchLoopState.STOPPED_CONTRADICTION,
    ResearchLoopState.STOPPED_HUMAN_REVIEW,
    ResearchLoopState.STOPPED_BUDGET,
    ResearchLoopState.FAILED,
}

WAITING_LOOP_STATES = {
    ResearchLoopState.WAITING_EVIDENCE_APPROVAL,
    ResearchLoopState.WAITING_CLAIM_APPROVAL,
    ResearchLoopState.WAITING_SYNTHESIS_PUBLICATION,
}

ALLOWED_LOOP_TRANSITIONS = {
    ResearchLoopState.PENDING: {ResearchLoopState.PLANNING, ResearchLoopState.COMPLETED, ResearchLoopState.FAILED},
    ResearchLoopState.PLANNING: {ResearchLoopState.ACQUIRING, ResearchLoopState.COMPLETED, ResearchLoopState.FAILED},
    ResearchLoopState.ACQUIRING: {ResearchLoopState.FETCHING_CONTENT, ResearchLoopState.STOPPED_BUDGET, ResearchLoopState.FAILED},
    ResearchLoopState.FETCHING_CONTENT: {
        ResearchLoopState.EXTRACTING_EVIDENCE,
        ResearchLoopState.STOPPED_BUDGET,
        ResearchLoopState.FAILED,
    },
    ResearchLoopState.EXTRACTING_EVIDENCE: {
        ResearchLoopState.WAITING_EVIDENCE_APPROVAL,
        ResearchLoopState.CONSTRUCTING_CLAIMS,
        ResearchLoopState.STOPPED_BUDGET,
        ResearchLoopState.FAILED,
    },
    ResearchLoopState.WAITING_EVIDENCE_APPROVAL: {
        ResearchLoopState.CONSTRUCTING_CLAIMS,
        ResearchLoopState.STOPPED_NEEDS_EVIDENCE,
        ResearchLoopState.FAILED,
    },
    ResearchLoopState.CONSTRUCTING_CLAIMS: {
        ResearchLoopState.WAITING_CLAIM_APPROVAL,
        ResearchLoopState.VALIDATING,
        ResearchLoopState.STOPPED_BUDGET,
        ResearchLoopState.FAILED,
    },
    ResearchLoopState.WAITING_CLAIM_APPROVAL: {
        ResearchLoopState.VALIDATING,
        ResearchLoopState.STOPPED_NEEDS_EVIDENCE,
        ResearchLoopState.FAILED,
    },
    ResearchLoopState.VALIDATING: {ResearchLoopState.ASSESSING_COMPLETION, ResearchLoopState.FAILED},
    ResearchLoopState.ASSESSING_COMPLETION: {
        ResearchLoopState.ITERATING,
        ResearchLoopState.SYNTHESIZING,
        ResearchLoopState.STOPPED_NEEDS_EVIDENCE,
        ResearchLoopState.STOPPED_CONTRADICTION,
        ResearchLoopState.STOPPED_HUMAN_REVIEW,
        ResearchLoopState.STOPPED_BUDGET,
        ResearchLoopState.FAILED,
    },
    ResearchLoopState.ITERATING: {ResearchLoopState.ACQUIRING, ResearchLoopState.STOPPED_BUDGET},
    ResearchLoopState.SYNTHESIZING: {
        ResearchLoopState.WAITING_SYNTHESIS_PUBLICATION,
        ResearchLoopState.COMPLETED,
        ResearchLoopState.FAILED,
    },
    ResearchLoopState.WAITING_SYNTHESIS_PUBLICATION: {ResearchLoopState.COMPLETED, ResearchLoopState.FAILED},
}
