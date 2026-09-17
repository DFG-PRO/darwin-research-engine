"""Evidence intake contract and adapter for Darwin monetization.

Parses, validates, and normalizes incoming evidence from operator intake, internal
repositories, web research, empirical tests, and external benchmarks into canonical
MetricEvidenceUnits. Enforces epistemic safeguards preventing unsupported claims
from silently becoming FACT and ensures source provenance is strictly preserved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from darwin.content.hashing import sha256_text
from darwin.monetization.readiness import MetricEvidenceUnit
from darwin.research.schemas import ClaimRead, EvidenceRead


class IntakeSourceType(str, Enum):
    """Canonical source channels through which evidence enters Darwin."""

    INTERNAL_REPOSITORY = "INTERNAL_REPOSITORY"
    OPERATOR = "OPERATOR"
    PRIMARY_WEB_SOURCE = "PRIMARY_WEB_SOURCE"
    EMPIRICAL_TEST = "EMPIRICAL_TEST"
    EXTERNAL_MARKET_BENCHMARK = "EXTERNAL_MARKET_BENCHMARK"


class IntakeClaimType(str, Enum):
    """Classification of the evidentiary claim type."""

    BENCHMARK = "BENCHMARK"
    CAPABILITY = "CAPABILITY"
    CONTRACT = "CONTRACT"
    EMPIRICAL_MEASUREMENT = "EMPIRICAL_MEASUREMENT"
    OPERATOR_INTAKE = "OPERATOR_INTAKE"
    PLATFORM_TERMS = "PLATFORM_TERMS"
    REGULATORY_FILING = "REGULATORY_FILING"


class EpistemicClass(str, Enum):
    """Epistemic category for evidence and claims."""

    FACT = "FACT"
    SOURCE_CLAIM = "SOURCE_CLAIM"
    DERIVED_VALUE = "DERIVED_VALUE"
    UNKNOWN = "UNKNOWN"


# Metrics that are strictly non-negative by definition
_NON_NEGATIVE_METRICS: set[str] = {
    "upfront_capital_usd",
    "capital_at_risk_usd",
    "daniel_hours_first_30_days",
    "daniel_hours_first_90_days",
    "time_to_first_dollar_days",
    "gross_margin_pct",
    "recurring_revenue_pct",
    "probability_of_success",
    "operational_complexity",
    "legal_compliance_risk",
    "platform_dependency_risk",
    "automation_potential",
    "dfg_capability_reuse",
}


class EvidenceIntakePayload(BaseModel):
    """Raw structured payload representing incoming evidence from any intake channel."""

    model_config = ConfigDict(str_strip_whitespace=True)

    opportunity_id: str = Field(min_length=1)
    target_metric: str = Field(min_length=1)
    source_type: IntakeSourceType
    source_identifier: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    claim_type: IntakeClaimType | None = None
    epistemic_class: EpistemicClass | None = None
    observation_time: datetime | None = None
    captured_at: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    raw_content: str | None = None
    jurisdiction: str | None = None
    numeric_value: float | None = None
    range_min: float | None = None
    range_max: float | None = None
    unit_of_measure: str | None = None
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def content_fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint of evidence content."""
        if self.raw_content:
            return sha256_text(self.raw_content)
        return sha256_text(self.statement)

    @field_validator("source_identifier", "statement", "opportunity_id", "target_metric", mode="before")
    @classmethod
    def _validate_non_empty_str(cls, value: Any) -> str:
        s = str(value or "").strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace.")
        return s

    @model_validator(mode="after")
    def _validate_payload_integrity(self) -> EvidenceIntakePayload:
        # Validate ranges
        if self.range_min is not None and self.range_max is not None:
            if self.range_min > self.range_max:
                raise ValueError(
                    f"range_min ({self.range_min}) cannot be greater than range_max ({self.range_max})"
                )

        # Validate non-negative constraints
        if self.target_metric in _NON_NEGATIVE_METRICS:
            if self.numeric_value is not None and self.numeric_value < 0:
                raise ValueError(
                    f"Metric '{self.target_metric}' cannot have negative numeric_value: {self.numeric_value}"
                )
            if self.range_min is not None and self.range_min < 0:
                raise ValueError(
                    f"Metric '{self.target_metric}' cannot have negative range_min: {self.range_min}"
                )
            if self.range_max is not None and self.range_max < 0:
                raise ValueError(
                    f"Metric '{self.target_metric}' cannot have negative range_max: {self.range_max}"
                )

        # Epistemic invariant: external market benchmarks cannot claim to be FACT
        if self.source_type == IntakeSourceType.EXTERNAL_MARKET_BENCHMARK:
            if self.epistemic_class == EpistemicClass.FACT:
                raise ValueError(
                    "EXTERNAL_MARKET_BENCHMARK cannot be classified as FACT: "
                    "external market pricing/volume benchmarks are SOURCE_CLAIM or DERIVED_VALUE."
                )

        return self


class EvidenceIntakeAdapter:
    """Adapter to transform and validate raw evidence payloads into canonical MetricEvidenceUnits."""

    def ingest(self, payload: EvidenceIntakePayload) -> MetricEvidenceUnit:
        """Ingest a single EvidenceIntakePayload and return a validated MetricEvidenceUnit."""
        # Determine capture date string
        obs_time = payload.observation_time or datetime.now(timezone.utc)
        captured_at_str = payload.captured_at or obs_time.strftime("%Y-%m-%d")

        # Determine deterministic unit ID
        seed = f"{payload.opportunity_id}:{payload.target_metric}:{payload.source_type.value}:{payload.source_identifier}:{payload.statement}"
        unit_id = f"EV_{sha256_text(seed)[7:23]}"

        # Derive claim type if omitted
        claim_t = payload.claim_type
        if claim_t is None:
            if payload.source_type == IntakeSourceType.EXTERNAL_MARKET_BENCHMARK:
                claim_t = IntakeClaimType.BENCHMARK
            elif payload.source_type == IntakeSourceType.OPERATOR:
                claim_t = IntakeClaimType.OPERATOR_INTAKE
            elif payload.source_type == IntakeSourceType.INTERNAL_REPOSITORY:
                claim_t = IntakeClaimType.CAPABILITY
            elif payload.source_type == IntakeSourceType.EMPIRICAL_TEST:
                claim_t = IntakeClaimType.EMPIRICAL_MEASUREMENT
            elif payload.source_type == IntakeSourceType.PRIMARY_WEB_SOURCE:
                claim_t = IntakeClaimType.PLATFORM_TERMS
            else:
                claim_t = IntakeClaimType.BENCHMARK

        # Derive confidence if omitted
        conf = payload.confidence
        if conf is None:
            if payload.source_type == IntakeSourceType.INTERNAL_REPOSITORY:
                conf = 0.95
            elif payload.source_type == IntakeSourceType.EMPIRICAL_TEST:
                conf = 0.90
            elif payload.source_type == IntakeSourceType.PRIMARY_WEB_SOURCE:
                conf = 0.85
            elif payload.source_type == IntakeSourceType.OPERATOR:
                conf = 0.80
            elif payload.source_type == IntakeSourceType.EXTERNAL_MARKET_BENCHMARK:
                conf = 0.65
            else:
                conf = 0.50

        return MetricEvidenceUnit(
            evidence_id=unit_id,
            source_type=payload.source_type.value,
            claim_type=claim_t.value,
            statement=payload.statement,
            jurisdiction=payload.jurisdiction,
            captured_at=captured_at_str,
            confidence=conf,
        )

    def ingest_batch(
        self,
        payloads: Sequence[EvidenceIntakePayload],
    ) -> list[MetricEvidenceUnit]:
        """Ingest multiple EvidenceIntakePayloads preserving order and provenance."""
        return [self.ingest(p) for p in payloads]

    def from_evidence_and_claim(
        self,
        evidence: EvidenceRead,
        claim: ClaimRead,
        opportunity_id: str,
        target_metric: str,
        source_type: IntakeSourceType | None = None,
        jurisdiction: str | None = None,
        confidence: float | None = None,
    ) -> MetricEvidenceUnit:
        """Convert canonical Darwin EvidenceRead and ClaimRead models into MetricEvidenceUnit."""
        source_identifier = evidence.source_locator or str(evidence.source_id)
        resolved_source_type = source_type or IntakeSourceType.PRIMARY_WEB_SOURCE
        resolved_confidence = confidence or (float(claim.confidence) if claim.confidence is not None else 0.85)

        payload = EvidenceIntakePayload(
            opportunity_id=opportunity_id,
            target_metric=target_metric,
            source_type=resolved_source_type,
            source_identifier=source_identifier,
            statement=claim.statement,
            epistemic_class=EpistemicClass.SOURCE_CLAIM,
            observation_time=evidence.captured_at,
            captured_at=evidence.captured_at.strftime("%Y-%m-%d"),
            confidence=resolved_confidence,
            raw_content=evidence.statement,
            jurisdiction=jurisdiction,
            metadata={
                "evidence_id": str(evidence.id),
                "claim_id": str(claim.id),
                "research_run_id": str(claim.research_run_id),
            },
        )
        return self.ingest(payload)
