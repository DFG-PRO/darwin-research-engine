"""Deterministic data contracts for the Darwin Master Research Backlog.

Defines unified representations for research work across MONETIZATION,
BUSINESS_VALIDATION, TECHNOLOGY_SCOUT, and INTELLIGENCE_CAPABILITIES.
Enforces strict epistemic integrity: provenance can be explicitly missing,
priorities represent execution importance rather than attractiveness, and
Technology Scout evaluations follow a normalized decision vocabulary.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class BacklogCategory(StrEnum):
    """Canonical work classes in the Darwin Master Research Backlog."""

    MONETIZATION = "MONETIZATION"
    BUSINESS_VALIDATION = "BUSINESS_VALIDATION"
    TECHNOLOGY_SCOUT = "TECHNOLOGY_SCOUT"
    INTELLIGENCE_CAPABILITIES = "INTELLIGENCE_CAPABILITIES"


class BacklogPriority(StrEnum):
    """DFG execution importance tiers (not attractiveness scores)."""

    P0_NOW = "P0_NOW"
    P0 = "P0"
    P1_HIGH = "P1_HIGH"
    P1 = "P1"
    P1_P2 = "P1_P2"
    P2 = "P2"
    P2_LATER = "P2_LATER"
    PARKED = "PARKED"
    REJECTED = "REJECTED"


class BacklogStatus(StrEnum):
    """Lifecycle status vocabulary for research backlog items."""

    QUEUED = "QUEUED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    NEEDS_OPERATOR_INPUT = "NEEDS_OPERATOR_INPUT"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    PARKED = "PARKED"
    REJECTED = "REJECTED"


class TechScoutDecision(StrEnum):
    """Normalized evaluation outcomes for Technology Scout items."""

    USE = "USE"
    USE_BEHIND_ADAPTER = "USE_BEHIND_ADAPTER"
    FORK_ADAPT = "FORK_ADAPT"
    REIMPLEMENT = "REIMPLEMENT"
    COPY_ARCHITECTURAL_PATTERN = "COPY_ARCHITECTURAL_PATTERN"
    STUDY_ONLY = "STUDY_ONLY"
    REJECT = "REJECT"


class TechScoutAssessment(BaseModel):
    """Structured assessment record for a Technology Scout backlog item."""

    model_config = ConfigDict(str_strip_whitespace=True)

    item_id: str = Field(min_length=1)
    technology_name: str = Field(min_length=1)
    what_it_does: str = Field(min_length=1)
    problem_solved: str = Field(min_length=1)
    maturity: str = Field(min_length=1)
    evidence_it_works: str = Field(min_length=1)
    architecture: str = Field(min_length=1)
    programmatic_access: str = Field(min_length=1)  # API / CLI / Python library
    self_hosting: str = Field(min_length=1)
    license: str = Field(min_length=1)
    cost: str = Field(min_length=1)
    vendor_dependency: str = Field(min_length=1)
    privacy_and_security: str = Field(min_length=1)
    maintenance_burden: str = Field(min_length=1)
    dfg_integration_potential: str = Field(min_length=1)
    existing_overlap: str = Field(min_length=1)
    implementation_effort: str = Field(min_length=1)
    expected_leverage: str = Field(min_length=1)
    decision: TechScoutDecision
    decision_rationale: str = Field(min_length=1)


class ResearchBacklogItem(BaseModel):
    """Canonical backlog entry in the Darwin Master Research Backlog."""

    model_config = ConfigDict(str_strip_whitespace=True)

    item_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: BacklogCategory
    priority: BacklogPriority
    status: BacklogStatus
    objective: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    provenance_refs: list[str] = Field(default_factory=list)
    related_opportunity_id: str | None = None
    related_project: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    research_questions: list[str] = Field(default_factory=list)
    expected_output: str = Field(min_length=1)
    decision_type: str = Field(min_length=1)
    owner_engine: str = "Darwin"
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)
    notes: str | None = None
    tech_scout_decision: TechScoutDecision | None = None

    @property
    def has_provenance(self) -> bool:
        """Indicate whether this item has explicit tracked provenance references."""
        return bool(self.provenance_refs)

    @property
    def is_dispatchable(self) -> bool:
        """Determine if this item can be dispatched for immediate execution.

        Requires status == READY, no active blockers, and not parked/rejected.
        """
        if self.status != BacklogStatus.READY:
            return False
        if bool(self.blocked_by):
            return False
        if self.priority in (BacklogPriority.PARKED, BacklogPriority.REJECTED):
            return False
        return True

    @model_validator(mode="after")
    def _validate_backlog_invariants(self) -> ResearchBacklogItem:
        """Enforce epistemic and lifecycle integrity constraints."""
        # 1. Blocked items cannot have READY status
        if self.blocked_by and self.status == BacklogStatus.READY:
            raise ValueError(
                f"Item '{self.item_id}' has active blockers {self.blocked_by} "
                f"and cannot have status 'READY'."
            )

        # 2. Parked or Rejected priorities cannot have active execution status
        if self.priority in (BacklogPriority.PARKED, BacklogPriority.REJECTED):
            if self.status in (BacklogStatus.READY, BacklogStatus.IN_PROGRESS):
                raise ValueError(
                    f"Item '{self.item_id}' has priority {self.priority.value} "
                    f"and cannot have active status '{self.status.value}'."
                )

        # 3. Status BLOCKED should have blocked_by or explicit dependencies
        if self.status == BacklogStatus.BLOCKED and not self.blocked_by and not self.dependencies:
            raise ValueError(
                f"Item '{self.item_id}' has status 'BLOCKED' but no blocked_by or dependencies recorded."
            )

        return self
