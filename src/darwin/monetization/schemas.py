"""Schemas for evidence-aware monetization opportunity prioritization."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class OpportunityEvidenceQuality(StrEnum):
    INSUFFICIENT = "INSUFFICIENT"
    HYPOTHESIS = "HYPOTHESIS"
    PRELIMINARY = "PRELIMINARY"
    VALIDATED = "VALIDATED"
    OPERATING = "OPERATING"


class OpportunityStatus(StrEnum):
    ACTIONABLE = "ACTIONABLE"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    BLOCKED = "BLOCKED"


class OpportunityRange(BaseModel):
    low: float
    high: float
    unit: str
    confidence: float = Field(ge=0, le=1)
    rationale: str

    @model_validator(mode="after")
    def high_not_below_low(self) -> "OpportunityRange":
        if self.high < self.low:
            raise ValueError("range high must be greater than or equal to low")
        return self


class MonetizationOpportunity(BaseModel):
    opportunity_id: str
    title: str
    thesis: str

    evidence_quality: OpportunityEvidenceQuality
    evidence_refs: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)

    time_to_first_dollar_days: OpportunityRange
    expected_30_day_net_revenue_usd: OpportunityRange
    expected_90_day_net_revenue_usd: OpportunityRange
    expected_180_day_net_revenue_usd: OpportunityRange

    upfront_capital_usd: OpportunityRange
    capital_at_risk_usd: OpportunityRange
    daniel_hours_first_30_days: OpportunityRange

    gross_margin_pct: OpportunityRange | None = None
    recurring_revenue_pct: OpportunityRange | None = None

    probability_of_success: float | None = Field(default=None, ge=0, le=1)
    automation_potential: int | None = Field(default=None, ge=1, le=5)
    dfg_capability_reuse: int | None = Field(default=None, ge=1, le=5)

    legal_compliance_risk: int | None = Field(default=None, ge=1, le=5)
    platform_dependency_risk: int | None = Field(default=None, ge=1, le=5)
    operational_complexity: int | None = Field(default=None, ge=1, le=5)

    @field_validator("opportunity_id", "title", "thesis")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be blank")
        return value


class MonetizationPortfolioRequest(BaseModel):
    objective: str
    opportunities: list[MonetizationOpportunity]

    @field_validator("objective")
    @classmethod
    def objective_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("objective cannot be blank")
        return value

    @model_validator(mode="after")
    def opportunities_present(self) -> "MonetizationPortfolioRequest":
        if not self.opportunities:
            raise ValueError("at least one monetization opportunity is required")
        ids = [item.opportunity_id for item in self.opportunities]
        if len(ids) != len(set(ids)):
            raise ValueError("opportunity_id values must be unique")
        return self


class RankedMonetizationOpportunity(BaseModel):
    rank: int
    opportunity_id: str
    title: str
    status: OpportunityStatus

    score: float | None
    expected_value_90_day_usd: float | None
    revenue_per_daniel_hour_90_day: float | None

    evidence_quality: OpportunityEvidenceQuality
    rationale: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


class MonetizationPortfolioResult(BaseModel):
    schema_version: str = "darwin-monetization-portfolio.v1"

    actionable_opportunity_ids: list[str]
    needs_evidence_opportunity_ids: list[str]
    blocked_opportunity_ids: list[str]

    ranked_opportunities: list[RankedMonetizationOpportunity]

    highest_value_research_targets: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
