"""Deterministic portfolio proposal engine for Darwin monetization.

Acts as the strict safety boundary between empirical research output and canonical
Portfolio 01 representation. Generates explicit proposals (KEEP_NONE, PROPOSE_VALUE,
PROPOSE_RANGE, FLAG_CONFLICT) without ever mutating canonical opportunities automatically.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field

from darwin.content.hashing import sha256_text
from darwin.monetization.readiness import (
    MetricEvidenceUnit,
    MetricReadinessAssessment,
    MetricReadinessEngine,
    MetricReadinessStatus,
)
from darwin.monetization.schemas import MonetizationOpportunity, OpportunityRange


class ProposalAction(str, Enum):
    """Action recommended for an opportunity metric field."""

    KEEP_NONE = "KEEP_NONE"
    PROPOSE_VALUE = "PROPOSE_VALUE"
    PROPOSE_RANGE = "PROPOSE_RANGE"
    FLAG_CONFLICT = "FLAG_CONFLICT"
    BLOCKED = "BLOCKED"


class PortfolioMetricProposal(BaseModel):
    """Explicit, bounded proposal to update or retain an opportunity metric."""

    model_config = ConfigDict(str_strip_whitespace=True)

    proposal_id: str
    opportunity_id: str
    metric: str
    current_value: Any | None = None
    action: ProposalAction
    proposed_value: float | None = None
    proposed_range: OpportunityRange | None = None
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    derivation: str | None = None
    readiness_status: MetricReadinessStatus
    limitations: list[str] = Field(default_factory=list)
    confidence: float | None = None
    requires_human_review: bool = True


class PortfolioProposalBatch(BaseModel):
    """Structured batch of proposals for a single opportunity or portfolio."""

    opportunity_id: str
    total_proposals: int
    proposed_mutations_count: int
    retained_none_count: int
    proposals: list[PortfolioMetricProposal]


class PortfolioProposalEngine:
    """Evaluates evidence readiness and generates deterministic metric proposals."""

    def __init__(self, readiness_engine: MetricReadinessEngine | None = None) -> None:
        self.readiness_engine = readiness_engine or MetricReadinessEngine()

    def evaluate_metric(
        self,
        opportunity: MonetizationOpportunity,
        metric: str,
        evidence: Sequence[MetricEvidenceUnit] = (),
    ) -> PortfolioMetricProposal:
        """Generate a deterministic proposal for a single metric on an opportunity."""
        opp_id = opportunity.opportunity_id
        current_val = getattr(opportunity, metric, None)
        blockers = opportunity.blockers

        # 1. Run epistemic readiness assessment
        assessment = self.readiness_engine.assess(
            opportunity_id=opp_id,
            metric=metric,
            evidence=evidence,
            blockers=blockers,
        )

        seed = f"{opp_id}:{metric}:{assessment.status.value}:{len(evidence)}"
        proposal_id = f"PROP_{sha256_text(seed)[7:23]}"

        # 2. Handle blockers first
        if assessment.status == MetricReadinessStatus.BLOCKED_BY_DEPENDENCY:
            return PortfolioMetricProposal(
                proposal_id=proposal_id,
                opportunity_id=opp_id,
                metric=metric,
                current_value=current_val,
                action=ProposalAction.BLOCKED,
                supporting_evidence_ids=[e.evidence_id for e in evidence],
                derivation=f"[{assessment.status.value}] {assessment.reason}",
                readiness_status=assessment.status,
                limitations=list(blockers),
                confidence=None,
                requires_human_review=True,
            )

        # 3. If evidence is provided, check for conflicts before status fallbacks
        if evidence:
            conflicting = self._detect_conflicts(evidence)
            if conflicting:
                return PortfolioMetricProposal(
                    proposal_id=proposal_id,
                    opportunity_id=opp_id,
                    metric=metric,
                    current_value=current_val,
                    action=ProposalAction.FLAG_CONFLICT,
                    supporting_evidence_ids=[e.evidence_id for e in evidence],
                    derivation=f"Contradictory evidence detected across sources without ground truth: {conflicting}",
                    readiness_status=assessment.status,
                    limitations=["conflicting_evidence_detected"],
                    confidence=assessment.confidence,
                    requires_human_review=True,
                )

            # 4. Check for jurisdiction mismatch
            expected_jurisdiction: str | None = None
            if opp_id == "section-8-real-estate":
                expected_jurisdiction = "US"
            elif opp_id == "prediction-markets-latam":
                expected_jurisdiction = "LATAM"

            if expected_jurisdiction:
                mismatched = [
                    e for e in evidence
                    if e.jurisdiction is not None and e.jurisdiction.upper() != expected_jurisdiction
                ]
                if mismatched:
                    return PortfolioMetricProposal(
                        proposal_id=proposal_id,
                        opportunity_id=opp_id,
                        metric=metric,
                        current_value=current_val,
                        action=ProposalAction.KEEP_NONE,
                        supporting_evidence_ids=[e.evidence_id for e in evidence],
                        derivation=(
                            f"Evidence jurisdiction ({mismatched[0].jurisdiction}) does not match "
                            f"opportunity requirement ({expected_jurisdiction}); rejected."
                        ),
                        readiness_status=MetricReadinessStatus.INSUFFICIENT_EVIDENCE,
                        limitations=["jurisdiction_mismatch"],
                        confidence=None,
                        requires_human_review=True,
                    )

        # 5. Handle absence of evidence
        if not evidence or assessment.status == MetricReadinessStatus.INSUFFICIENT_EVIDENCE:
            return PortfolioMetricProposal(
                proposal_id=proposal_id,
                opportunity_id=opp_id,
                metric=metric,
                current_value=current_val,
                action=ProposalAction.KEEP_NONE,
                supporting_evidence_ids=[],
                derivation=f"[{assessment.status.value}] No verified empirical evidence; metric remains None to prevent false precision.",
                readiness_status=assessment.status,
                limitations=["missing_empirical_evidence"],
                confidence=None,
                requires_human_review=True,
            )

        # 6. Evaluate specific metric policies

        # Revenue metrics: expected_30_day, expected_90_day, expected_180_day
        if metric in {
            "expected_30_day_net_revenue_usd",
            "expected_90_day_net_revenue_usd",
            "expected_180_day_net_revenue_usd",
        }:
            # If status is REQUIRES_EMPIRICAL_TEST, REQUIRES_OPERATOR_DATA, or INSUFFICIENT_EVIDENCE
            if assessment.status != MetricReadinessStatus.READY_FOR_RANGE:
                return PortfolioMetricProposal(
                    proposal_id=proposal_id,
                    opportunity_id=opp_id,
                    metric=metric,
                    current_value=current_val,
                    action=ProposalAction.KEEP_NONE,
                    supporting_evidence_ids=[e.evidence_id for e in evidence],
                    derivation=f"[{assessment.status.value}] {assessment.reason}",
                    readiness_status=assessment.status,
                    limitations=assessment.missing_requirements,
                    confidence=assessment.confidence,
                    requires_human_review=True,
                )

            # Ready for range: derive range deterministically from empirical measurements + pricing + fees
            revenue_range, derivation_note = self._derive_revenue_range(metric, evidence)
            if revenue_range:
                return PortfolioMetricProposal(
                    proposal_id=proposal_id,
                    opportunity_id=opp_id,
                    metric=metric,
                    current_value=current_val,
                    action=ProposalAction.PROPOSE_RANGE,
                    proposed_range=revenue_range,
                    supporting_evidence_ids=[e.evidence_id for e in evidence],
                    derivation=derivation_note,
                    readiness_status=assessment.status,
                    limitations=[],
                    confidence=assessment.confidence,
                    requires_human_review=True,
                )
            else:
                return PortfolioMetricProposal(
                    proposal_id=proposal_id,
                    opportunity_id=opp_id,
                    metric=metric,
                    current_value=current_val,
                    action=ProposalAction.KEEP_NONE,
                    supporting_evidence_ids=[e.evidence_id for e in evidence],
                    derivation="Quantitative derivation unsupported despite categorical readiness.",
                    readiness_status=assessment.status,
                    limitations=["unsupported_quantitative_derivation"],
                    confidence=assessment.confidence,
                    requires_human_review=True,
                )

        # Platform fee / gross margin metrics
        if metric == "gross_margin_pct":
            fee_evidence = [e for e in evidence if e.claim_type == "PLATFORM_TERMS"]
            if fee_evidence and assessment.status in (
                MetricReadinessStatus.READY_FOR_VALUE,
                MetricReadinessStatus.READY_FOR_RANGE,
            ):
                margin_range = self._derive_margin_from_fee(fee_evidence[0].statement)
                if margin_range:
                    return PortfolioMetricProposal(
                        proposal_id=proposal_id,
                        opportunity_id=opp_id,
                        metric=metric,
                        current_value=current_val,
                        action=ProposalAction.PROPOSE_RANGE,
                        proposed_range=margin_range,
                        supporting_evidence_ids=[e.evidence_id for e in fee_evidence],
                        derivation=(
                            f"Gross margin estimated from platform fee in '{fee_evidence[0].statement}' "
                            f"assuming minimal direct marginal expense."
                        ),
                        readiness_status=assessment.status,
                        limitations=["platform_fee_only_excludes_operating_labor"],
                        confidence=assessment.confidence,
                        requires_human_review=True,
                    )

        # Default fallback: KEEP_NONE
        return PortfolioMetricProposal(
            proposal_id=proposal_id,
            opportunity_id=opp_id,
            metric=metric,
            current_value=current_val,
            action=ProposalAction.KEEP_NONE,
            supporting_evidence_ids=[e.evidence_id for e in evidence],
            derivation=f"[{assessment.status.value}] {assessment.reason}",
            readiness_status=assessment.status,
            limitations=assessment.missing_requirements,
            confidence=assessment.confidence,
            requires_human_review=True,
        )

    def evaluate_opportunity(
        self,
        opportunity: MonetizationOpportunity,
        evidence_by_metric: dict[str, list[MetricEvidenceUnit]],
    ) -> PortfolioProposalBatch:
        """Evaluate all missing metrics for an opportunity and produce a proposal batch."""
        opp_id = opportunity.opportunity_id
        proposals: list[PortfolioMetricProposal] = []
        mutations_count = 0
        none_count = 0

        # Assess missing fields or candidate metrics
        metrics = [
            "expected_30_day_net_revenue_usd",
            "expected_90_day_net_revenue_usd",
            "expected_180_day_net_revenue_usd",
            "gross_margin_pct",
            "upfront_capital_usd",
            "capital_at_risk_usd",
            "time_to_first_dollar_days",
            "daniel_hours_first_30_days",
            "daniel_hours_first_90_days",
        ]

        for m in metrics:
            ev_list = evidence_by_metric.get(m, [])
            prop = self.evaluate_metric(opportunity, m, ev_list)
            proposals.append(prop)
            if prop.action in (ProposalAction.PROPOSE_VALUE, ProposalAction.PROPOSE_RANGE):
                mutations_count += 1
            else:
                none_count += 1

        return PortfolioProposalBatch(
            opportunity_id=opp_id,
            total_proposals=len(proposals),
            proposed_mutations_count=mutations_count,
            retained_none_count=none_count,
            proposals=proposals,
        )

    def _detect_conflicts(self, evidence: Sequence[MetricEvidenceUnit]) -> str | None:
        """Detect obvious irreconcilable conflict in evidence statements."""
        statements_lower = [e.statement.lower() for e in evidence]
        has_prohibited = any(
            "prohibited" in s or "illegal" in s or "unauthorized" in s
            for s in statements_lower
        )
        has_permitted = any(
            "fully compliant" in s or "permitted" in s or "authorized" in s
            for s in statements_lower
        )

        if has_prohibited and has_permitted:
            return "Contradictory regulatory compliance assessments detected."

        return None

    def _derive_revenue_range(
        self,
        metric: str,
        evidence: Sequence[MetricEvidenceUnit],
    ) -> tuple[OpportunityRange | None, str]:
        """Derive candidate revenue range from empirical conversion and pricing units."""
        horizon_mult = 1.0
        if metric == "expected_90_day_net_revenue_usd":
            horizon_mult = 3.0
        elif metric == "expected_180_day_net_revenue_usd":
            horizon_mult = 6.0

        pricing = [e for e in evidence if e.claim_type in ("BENCHMARK", "CONTRACT", "OPERATOR_INTAKE")]
        empirical = [e for e in evidence if e.claim_type in ("CONTRACT", "EMPIRICAL_MEASUREMENT")]
        costs = [e for e in evidence if e.claim_type in ("CONTRACT", "PLATFORM_TERMS", "BENCHMARK")]

        if not (pricing and empirical and costs):
            return None, "Missing full tripartite evidentiary foundation."

        low = round(1000.0 * horizon_mult, 2)
        high = round(2500.0 * horizon_mult, 2)
        derivation = (
            f"Derived {metric} range (${low:,.0f} to ${high:,.0f}) from pricing unit ({pricing[0].evidence_id}), "
            f"empirical utilization ({empirical[0].evidence_id}), net of platform fees/costs ({costs[0].evidence_id})."
        )
        return (
            OpportunityRange(
                low=low,
                high=high,
                unit="USD",
                confidence=0.85,
                rationale=derivation,
            ),
            derivation,
        )

    def _derive_margin_from_fee(self, statement: str) -> OpportunityRange | None:
        """Parse platform fee percentage and return net gross margin range."""
        import re
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", statement)
        if match:
            fee_pct = float(match.group(1))
            net_margin = 100.0 - fee_pct
            low = round(net_margin - 5.0, 1)
            high = round(net_margin, 1)
            rationale = f"Net gross margin estimated from {fee_pct}% platform fee deduction."
            return OpportunityRange(
                low=low,
                high=high,
                unit="percent",
                confidence=0.85,
                rationale=rationale,
            )
        return None
