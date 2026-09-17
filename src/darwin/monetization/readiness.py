"""Deterministic metric readiness engine for Darwin monetization opportunities.

Evaluates whether collected claims and evidence units are epistemically sufficient
to populate Portfolio 01 economic and risk fields without inventing values.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Sequence

from pydantic import BaseModel, Field


class MetricReadinessStatus(StrEnum):
    """Epistemic readiness status for a monetization opportunity field."""

    READY_FOR_VALUE = "READY_FOR_VALUE"
    READY_FOR_RANGE = "READY_FOR_RANGE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REQUIRES_OPERATOR_DATA = "REQUIRES_OPERATOR_DATA"
    REQUIRES_EMPIRICAL_TEST = "REQUIRES_EMPIRICAL_TEST"
    BLOCKED_BY_DEPENDENCY = "BLOCKED_BY_DEPENDENCY"


class MetricEvidenceUnit(BaseModel):
    """An evidence unit presented to evaluate metric readiness."""

    evidence_id: str
    source_type: str  # INTERNAL_REPOSITORY, OPERATOR, PRIMARY_WEB_SOURCE, EMPIRICAL_TEST, EXTERNAL_MARKET_BENCHMARK
    claim_type: str  # BENCHMARK, CAPABILITY, CONTRACT, EMPIRICAL_MEASUREMENT, OPERATOR_INTAKE, PLATFORM_TERMS, REGULATORY_FILING
    statement: str
    jurisdiction: str | None = None
    captured_at: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class MetricReadinessAssessment(BaseModel):
    """Deterministic assessment of whether evidence is sufficient to populate a field."""

    opportunity_id: str
    metric: str
    status: MetricReadinessStatus
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    confidence: float | None = None
    jurisdiction: str | None = None
    freshness: str | None = None
    missing_requirements: list[str] = Field(default_factory=list)
    derivation_allowed: bool = False
    reason: str


class MetricReadinessEngine:
    """Service to evaluate epistemic readiness of opportunity fields from evidence."""

    def assess(
        self,
        opportunity_id: str,
        metric: str,
        evidence: Sequence[MetricEvidenceUnit] = (),
        blockers: Sequence[str] = (),
    ) -> MetricReadinessAssessment:
        """Evaluate epistemic readiness deterministically."""
        # 1. Blocker gate
        if blockers:
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.BLOCKED_BY_DEPENDENCY,
                missing_requirements=list(blockers),
                derivation_allowed=False,
                reason=f"Opportunity is blocked by active dependencies: {'; '.join(blockers)}",
            )

        # 2. Absence of evidence gate
        if not evidence:
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
                missing_requirements=["positive_evidence_required"],
                derivation_allowed=False,
                reason="No supporting evidence units were provided.",
            )

        evidence_ids = [e.evidence_id for e in evidence]
        source_types = sorted(set(e.source_type for e in evidence))
        jurisdictions = [e.jurisdiction for e in evidence if e.jurisdiction]
        jurisdiction = jurisdictions[0] if jurisdictions else None

        # Calculate average confidence if present
        confidences = [e.confidence for e in evidence if e.confidence is not None]
        avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else None

        captured_dates = [e.captured_at for e in evidence if e.captured_at]
        freshness = max(captured_dates) if captured_dates else None

        claim_types = set(e.claim_type for e in evidence)

        # 3. Metric-specific evaluation policies

        # Revenue metrics (expected_30_day, expected_90_day, expected_180_day)
        if metric in {
            "expected_30_day_net_revenue_usd",
            "expected_90_day_net_revenue_usd",
            "expected_180_day_net_revenue_usd",
        }:
            has_pricing = any(t in {"BENCHMARK", "CONTRACT", "OPERATOR_INTAKE"} for t in claim_types)
            has_volume_or_conversion = any(t in {"CONTRACT", "EMPIRICAL_MEASUREMENT"} for t in claim_types)
            has_costs = any(t in {"CONTRACT", "PLATFORM_TERMS", "BENCHMARK"} for t in claim_types)

            if "EXTERNAL_MARKET_BENCHMARK" in source_types and not has_volume_or_conversion:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.REQUIRES_EMPIRICAL_TEST,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    confidence=avg_confidence,
                    jurisdiction=jurisdiction,
                    freshness=freshness,
                    missing_requirements=[
                        "contracted_volume_or_empirical_conversion_evidence",
                        "direct_cost_structure_evidence",
                    ],
                    derivation_allowed=False,
                    reason=(
                        "External market benchmarks provide price points but cannot establish "
                        "DFG expected net revenue without empirical conversion, client contracts, or pipeline volume."
                    ),
                )

            if has_pricing and has_volume_or_conversion and has_costs:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.READY_FOR_RANGE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    confidence=avg_confidence,
                    jurisdiction=jurisdiction,
                    freshness=freshness,
                    derivation_allowed=True,
                    reason="Complete pricing, conversion/volume, and cost evidence available.",
                )

            missing: list[str] = []
            if not has_pricing:
                missing.append("pricing_evidence")
            if not has_volume_or_conversion:
                missing.append("conversion_or_volume_evidence")
            if not has_costs:
                missing.append("cost_structure_evidence")

            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                missing_requirements=missing,
                derivation_allowed=False,
                reason=f"Revenue projection requires pricing, volume, and cost components. Missing: {', '.join(missing)}",
            )

        # Time to first dollar
        if metric == "time_to_first_dollar_days":
            has_sales_latency = any(t in {"EMPIRICAL_MEASUREMENT", "OPERATOR_INTAKE", "CONTRACT"} for t in claim_types)
            if not has_sales_latency:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.REQUIRES_EMPIRICAL_TEST,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    missing_requirements=["sales_cycle_latency_evidence"],
                    derivation_allowed=False,
                    reason="Technical capability to offer a service does not prove sales cycle or delivery turnaround latency.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.READY_FOR_RANGE,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                confidence=avg_confidence,
                jurisdiction=jurisdiction,
                freshness=freshness,
                derivation_allowed=True,
                reason="Sales cycle and operational lead time evidence verified.",
            )

        # Probability of success
        if metric == "probability_of_success":
            has_empirical = any(t in {"EMPIRICAL_MEASUREMENT", "CONTRACT"} for t in claim_types)
            if not has_empirical:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.REQUIRES_EMPIRICAL_TEST,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    missing_requirements=["empirical_conversion_or_win_rate_measurement"],
                    derivation_allowed=False,
                    reason="Success probability cannot be assumed; requires empirical conversion or backtest validation.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.READY_FOR_VALUE,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                confidence=avg_confidence,
                derivation_allowed=True,
                reason="Empirical win rate, conversion rate, or contract execution history verified.",
            )

        # Upfront capital
        if metric == "upfront_capital_usd":
            has_capex = any(t in {"CAPABILITY", "OPERATOR_INTAKE", "BENCHMARK"} for t in claim_types)
            if "INTERNAL_REPOSITORY" in source_types and any("zero upfront capital" in e.statement.lower() for e in evidence):
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.READY_FOR_VALUE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    derivation_allowed=True,
                    reason="Verified zero upfront capital consulting or existing internal asset model.",
                )
            if has_capex:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.READY_FOR_RANGE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    derivation_allowed=True,
                    reason="Capital outlay and asset acquisition requirements evidenced.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.REQUIRES_OPERATOR_DATA,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                missing_requirements=["asset_procurement_or_ownership_evidence"],
                derivation_allowed=False,
                reason="Asset inventory and acquisition costs require operator or quotation data.",
            )

        # Capital at risk
        if metric == "capital_at_risk_usd":
            has_risk_model = any(t in {"EMPIRICAL_MEASUREMENT", "CONTRACT", "PLATFORM_TERMS"} for t in claim_types)
            if not has_risk_model:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    missing_requirements=["loss_exposure_model_or_inventory_manifest"],
                    derivation_allowed=False,
                    reason="Capital at risk requires an explicit exposure model or asset replacement manifest, not market price alone.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.READY_FOR_RANGE,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                confidence=avg_confidence,
                derivation_allowed=True,
                reason="Loss exposure, guarantee limits, or capital drawdown limits verified.",
            )

        # Daniel hours (first 30 / 90 days)
        if metric in {"daniel_hours_first_30_days", "daniel_hours_first_90_days"}:
            has_operator_hours = any(t == "OPERATOR_INTAKE" for t in claim_types)
            has_empirical_labor = any(t == "EMPIRICAL_MEASUREMENT" for t in claim_types)
            if has_operator_hours or has_empirical_labor:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.READY_FOR_RANGE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    derivation_allowed=True,
                    reason="Operator bandwidth allocation or empirical time tracking evidenced.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.REQUIRES_OPERATOR_DATA,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                missing_requirements=["operator_bandwidth_commitment"],
                derivation_allowed=False,
                reason="Labor hours require operator schedule allocation or empirical tracking.",
            )

        # Capability reuse & automation potential
        if metric in {"dfg_capability_reuse", "automation_potential"}:
            has_codebase_evidence = any(t in {"CAPABILITY", "EMPIRICAL_MEASUREMENT"} for t in claim_types)
            if has_codebase_evidence or "INTERNAL_REPOSITORY" in source_types:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.READY_FOR_VALUE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    derivation_allowed=True,
                    reason="Direct DFG codebase, test suite, or pipeline implementation verified.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                missing_requirements=["codebase_or_pipeline_inspection_evidence"],
                derivation_allowed=False,
                reason="Capability metrics require internal repository or architecture evidence.",
            )

        # Legal compliance risk
        if metric == "legal_compliance_risk":
            has_regulatory = any(t in {"REGULATORY_FILING", "PLATFORM_TERMS"} for t in claim_types)
            if has_regulatory and jurisdiction:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.READY_FOR_VALUE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    jurisdiction=jurisdiction,
                    derivation_allowed=True,
                    reason="Jurisdiction-specific regulatory framework or statutory ruling verified.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                missing_requirements=["jurisdiction_specific_statutory_evidence"],
                derivation_allowed=False,
                reason="Compliance risk requires authoritative statutory or regulatory source evidence in target jurisdiction.",
            )

        # Platform dependency risk
        if metric == "platform_dependency_risk":
            has_platform_terms = any(t == "PLATFORM_TERMS" for t in claim_types)
            if has_platform_terms:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.READY_FOR_VALUE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    derivation_allowed=True,
                    reason="Current platform terms of service and marketplace policies verified.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                missing_requirements=["official_platform_terms_of_service"],
                derivation_allowed=False,
                reason="Platform risk requires official platform documentation and terms of service.",
            )

        # Gross margin & recurring revenue pct
        if metric in {"gross_margin_pct", "recurring_revenue_pct"}:
            has_fee_or_contract = any(t in {"PLATFORM_TERMS", "CONTRACT", "BENCHMARK"} for t in claim_types)
            if has_fee_or_contract:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.READY_FOR_RANGE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    derivation_allowed=True,
                    reason="Platform fee deductions or business contract model evidenced.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                missing_requirements=["fee_deduction_or_contract_structure_evidence"],
                derivation_allowed=False,
                reason="Margin/recurring revenue requires fee deduction or contract structure evidence.",
            )

        # Operational complexity
        if metric == "operational_complexity":
            has_workflow = any(t in {"CAPABILITY", "PLATFORM_TERMS", "OPERATOR_INTAKE"} for t in claim_types)
            if has_workflow:
                return MetricReadinessAssessment(
                    opportunity_id=opportunity_id,
                    metric=metric,
                    status=MetricReadinessStatus.READY_FOR_VALUE,
                    supporting_evidence_ids=evidence_ids,
                    source_types=source_types,
                    derivation_allowed=True,
                    reason="Operational stages, platform logistics, or physical labor touchpoints verified.",
                )
            return MetricReadinessAssessment(
                opportunity_id=opportunity_id,
                metric=metric,
                status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
                supporting_evidence_ids=evidence_ids,
                source_types=source_types,
                missing_requirements=["workflow_stage_and_logistics_evidence"],
                derivation_allowed=False,
                reason="Operational complexity requires workflow and logistics evidence.",
            )

        # Default fallback
        return MetricReadinessAssessment(
            opportunity_id=opportunity_id,
            metric=metric,
            status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
            supporting_evidence_ids=evidence_ids,
            source_types=source_types,
            missing_requirements=[f"evidence_policy_for_{metric}"],
            derivation_allowed=False,
            reason=f"No specific readiness policy satisfied for metric '{metric}'.",
        )
