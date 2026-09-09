"""Schemas for evidence-aware profitability path comparison."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class CandidatePathType(StrEnum):
    EXISTING_STRATEGY = "EXISTING_STRATEGY"
    ARBITRAGE = "ARBITRAGE"
    OTHER_SYSTEMATIC = "OTHER_SYSTEMATIC"
    HYBRID = "HYBRID"


class EvidenceQuality(StrEnum):
    INSUFFICIENT = "INSUFFICIENT"
    PRELIMINARY = "PRELIMINARY"
    PAPER_VALIDATED = "PAPER_VALIDATED"
    CONTROLLED_LIVE_VALIDATED = "CONTROLLED_LIVE_VALIDATED"


class DecisionStatus(StrEnum):
    DEFENSIBLE = "DEFENSIBLE"
    DEFERRED_FOR_EVIDENCE = "DEFERRED_FOR_EVIDENCE"
    REJECTED = "REJECTED"


class RangeEstimate(BaseModel):
    low: float
    high: float
    unit: str
    confidence: float = Field(ge=0, le=1)
    rationale: str

    @model_validator(mode="after")
    def high_not_below_low(self) -> "RangeEstimate":
        if self.high < self.low:
            raise ValueError("range high must be greater than or equal to low")
        return self


class CapitalScenario(BaseModel):
    capital_usd: float = Field(gt=0)
    max_notional_exposure_usd: float = Field(gt=0)
    risk_per_trade_pct: float = Field(ge=0)
    max_drawdown_pct: RangeEstimate
    liquidation_risk: str
    leverage_note: str

    @model_validator(mode="after")
    def notional_covers_capital(self) -> "CapitalScenario":
        if self.max_notional_exposure_usd < self.capital_usd:
            raise ValueError("max notional exposure cannot be below capital")
        return self


class ProfitabilityPathCandidate(BaseModel):
    path_id: str
    path_type: CandidatePathType
    title: str
    thesis: str
    evidence_quality: EvidenceQuality
    evidence_refs: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    time_to_paper_validation_days: RangeEstimate
    time_to_controlled_live_validation_days: RangeEstimate
    engineering_effort_days: RangeEstimate
    research_confidence: float = Field(ge=0, le=1)
    capital_required_usd: RangeEstimate
    expected_monthly_return_pct: RangeEstimate
    expected_drawdown_pct: RangeEstimate
    tail_risk: str
    operational_complexity: int = Field(ge=1, le=5)
    data_requirements: list[str] = Field(default_factory=list)
    infrastructure_requirements: list[str] = Field(default_factory=list)
    dependency_risk: str

    @field_validator("path_id", "title", "thesis")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be blank")
        return value


class ProfitabilityComparisonRequest(BaseModel):
    objective: str
    capital_scenarios: list[CapitalScenario]
    candidates: list[ProfitabilityPathCandidate]

    @model_validator(mode="after")
    def required_inputs_present(self) -> "ProfitabilityComparisonRequest":
        if not self.candidates:
            raise ValueError("at least one candidate path is required")
        has_two_thousand = any(round(item.capital_usd, 2) == 2000.0 for item in self.capital_scenarios)
        if not has_two_thousand:
            raise ValueError("USD 2000 capital scenario is required")
        return self


class RankedProfitabilityPath(BaseModel):
    rank: int
    path_id: str
    title: str
    path_type: CandidatePathType
    status: DecisionStatus
    score: float
    rationale: list[str]
    evidence_quality: EvidenceQuality
    uncertainty: list[str] = Field(default_factory=list)


class ProfitabilityComparisonResult(BaseModel):
    schema_version: str = "darwin-profitability-comparison.v1"
    fastest_defensible_path: str | None
    secondary_path: str | None
    rejected_or_deferred_paths: list[str]
    ranked_paths: list[RankedProfitabilityPath]
    capital_scenarios: list[CapitalScenario]
    seven_to_ten_percent_monthly_evidence: str
    warnings: list[str] = Field(default_factory=list)
