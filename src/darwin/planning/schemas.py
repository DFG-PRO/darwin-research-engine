"""Pydantic contracts for controlled research planning."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from darwin.db.models import (
    ResearchPlanApprovalMode,
    ResearchPlanItemStatus,
    ResearchPlanPriority,
    ResearchPlanProposalStatus,
    SourceType,
)


class ResearchPlanningLimits(BaseModel):
    """Bounded planning limits used to reject runaway proposals."""

    max_plan_items: int = Field(default=8, ge=1)
    max_required_plan_items: int = Field(default=6, ge=1)
    max_categories: int = Field(default=6, ge=1)
    max_breadth: int = Field(default=5, ge=1)
    max_depth: int = Field(default=3, ge=1)


class ResearchPlanningRequest(BaseModel):
    """Caller-supplied planning request. It does not launch research."""

    research_question: str = Field(min_length=1)
    objective: str | None = None
    scope: str | None = None
    exclusions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    desired_source_types: list[SourceType] = Field(default_factory=list)
    freshness_start: date | None = None
    freshness_end: date | None = None
    domain_constraints: list[str] = Field(default_factory=list)
    max_research_breadth: int | None = Field(default=None, ge=1)
    max_research_depth: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "research_question",
        "objective",
        "scope",
        mode="before",
    )
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("exclusions", "assumptions", "domain_constraints", mode="before")
    @classmethod
    def _strip_list(cls, value: list[str] | None) -> list[str]:
        return _clean_string_list(value or [])

    @model_validator(mode="after")
    def _validate_request(self) -> ResearchPlanningRequest:
        if not self.research_question:
            raise ValueError("research_question cannot be empty")
        if self.freshness_start and self.freshness_end and self.freshness_start > self.freshness_end:
            raise ValueError("freshness_start cannot be after freshness_end")
        return self


class ResearchPlanItemProposal(BaseModel):
    """One proposed task in a planning proposal."""

    model_config = ConfigDict(extra="forbid")

    item_key: str = Field(min_length=1, max_length=64)
    requirement: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=128)
    priority: ResearchPlanPriority = ResearchPlanPriority.MEDIUM
    required: bool = True
    status: ResearchPlanItemStatus = ResearchPlanItemStatus.PENDING
    expected_source_type: SourceType | None = None
    expected_evidence_types: list[str] = Field(default_factory=list)
    suggested_source_types: list[SourceType] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("item_key", "requirement", "category", "notes", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("expected_evidence_types", "completion_criteria", mode="before")
    @classmethod
    def _clean_lists(cls, value: list[str] | None) -> list[str]:
        return _clean_string_list(value or [])

    @model_validator(mode="after")
    def _validate_item(self) -> ResearchPlanItemProposal:
        if self.status is not ResearchPlanItemStatus.PENDING:
            raise ValueError("proposal items cannot be completed before execution")
        if not self.completion_criteria:
            raise ValueError("proposal items require explicit completion criteria")
        if not (self.expected_source_type or self.suggested_source_types):
            raise ValueError("proposal items require at least one source-type requirement")
        if not self.expected_evidence_types:
            raise ValueError("proposal items require expected evidence types")
        return self


class ProviderPlanProposal(BaseModel):
    """Strict structured output accepted from a planning provider."""

    model_config = ConfigDict(extra="forbid")

    normalized_research_question: str = Field(min_length=1)
    proposed_objective: str = Field(min_length=1)
    proposed_scope: str = Field(min_length=1)
    proposed_exclusions: list[str] = Field(default_factory=list)
    proposed_assumptions: list[str] = Field(default_factory=list)
    proposed_research_categories: list[str] = Field(min_length=1)
    expected_evidence_types: list[str] = Field(default_factory=list)
    suggested_source_types: list[SourceType] = Field(default_factory=list)
    tasks: list[ResearchPlanItemProposal] = Field(min_length=1)
    planner_warnings: list[str] = Field(default_factory=list)
    method_version: str = Field(min_length=1)
    prompt_version: str | None = None
    schema_version: str = Field(min_length=1)
    planning_provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "normalized_research_question",
        "proposed_objective",
        "proposed_scope",
        "method_version",
        "prompt_version",
        "schema_version",
        mode="before",
    )
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator(
        "proposed_exclusions",
        "proposed_assumptions",
        "proposed_research_categories",
        "expected_evidence_types",
        "planner_warnings",
        mode="before",
    )
    @classmethod
    def _clean_string_lists(cls, value: list[str] | None) -> list[str]:
        return _clean_string_list(value or [])

    def validate_structure(self, limits: ResearchPlanningLimits) -> None:
        """Apply deterministic plan-quality checks that are separate from provider output."""

        if len(self.tasks) > limits.max_plan_items:
            raise ValueError("proposal exceeds max_plan_items")
        required_count = len([item for item in self.tasks if item.required])
        if required_count == 0:
            raise ValueError("proposal must contain at least one required task")
        if required_count > limits.max_required_plan_items:
            raise ValueError("proposal exceeds max_required_plan_items")
        if len(self.proposed_research_categories) > limits.max_categories:
            raise ValueError("proposal exceeds max_categories")
        keys = [item.item_key for item in self.tasks]
        if len(keys) != len(set(keys)):
            raise ValueError("proposal contains duplicate task keys")
        for item in self.tasks:
            if item.category not in self.proposed_research_categories:
                raise ValueError(f"task category is not declared: {item.category}")
        if not self.expected_evidence_types:
            raise ValueError("proposal requires expected_evidence_types")
        if not self.suggested_source_types:
            raise ValueError("proposal requires suggested_source_types")


class PlanningProviderResult(BaseModel):
    """Provider envelope around a structured planning proposal."""

    provider_id: str
    provider_model: str | None = None
    provider_response_id: str | None = None
    proposal: ProviderPlanProposal | dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    usage_metadata: dict[str, Any] = Field(default_factory=dict)
    cost_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ResearchPlanProposalRead(BaseModel):
    """Read model for persisted planning proposals."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    research_run_id: uuid.UUID | None
    original_question: str
    normalized_question: str
    objective: str
    scope: str
    exclusions: list[str]
    assumptions: list[str]
    research_categories: list[str]
    expected_evidence_types: list[str]
    suggested_source_types: list[str]
    status: ResearchPlanProposalStatus
    approval_mode: ResearchPlanApprovalMode | None
    approved_at: datetime | None
    provider_id: str
    provider_model: str | None
    planner_method_version: str
    prompt_version: str | None
    schema_version: str
    warnings: list[str]
    errors: list[str]
    created_at: datetime


class ResearchPlanApprovalResult(BaseModel):
    """Result returned when a proposal is approved into Phase 1.8 records."""

    proposal_id: uuid.UUID
    research_run_id: uuid.UUID
    public_id: str
    approval_mode: ResearchPlanApprovalMode
    plan_item_count: int


def _clean_string_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            cleaned.append(text)
    return cleaned
