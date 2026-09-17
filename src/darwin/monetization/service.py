"""Deterministic evidence-aware monetization opportunity prioritization."""

from __future__ import annotations

from darwin.monetization.schemas import (
    MonetizationOpportunity,
    MonetizationPortfolioRequest,
    MonetizationPortfolioResult,
    OpportunityEvidenceQuality,
    OpportunityStatus,
    RankedMonetizationOpportunity,
)


_EVIDENCE_SCORE = {
    OpportunityEvidenceQuality.INSUFFICIENT: 0.0,
    OpportunityEvidenceQuality.HYPOTHESIS: 20.0,
    OpportunityEvidenceQuality.PRELIMINARY: 45.0,
    OpportunityEvidenceQuality.VALIDATED: 75.0,
    OpportunityEvidenceQuality.OPERATING: 95.0,
}


class MonetizationOpportunityPortfolioService:
    """Prioritize opportunities without converting assumptions into evidence."""

    def compare(
        self,
        request: MonetizationPortfolioRequest,
    ) -> MonetizationPortfolioResult:
        evaluated = [_evaluate(item) for item in request.opportunities]

        ranked = sorted(
            evaluated,
            key=_ranking_key,
        )

        normalized = [
            item.model_copy(update={"rank": index + 1})
            for index, item in enumerate(ranked)
        ]

        actionable = [
            item.opportunity_id
            for item in normalized
            if item.status is OpportunityStatus.ACTIONABLE
        ]
        needs_evidence = [
            item.opportunity_id
            for item in normalized
            if item.status is OpportunityStatus.NEEDS_EVIDENCE
        ]
        blocked = [
            item.opportunity_id
            for item in normalized
            if item.status is OpportunityStatus.BLOCKED
        ]

        research_targets = _research_targets(normalized)

        warnings: list[str] = []
        if not actionable:
            warnings.append(
                "No opportunity is currently actionable with sufficient evidence."
            )
        if needs_evidence:
            warnings.append(
                "Evidence gaps remain explicit; missing values were not imputed."
            )

        return MonetizationPortfolioResult(
            actionable_opportunity_ids=actionable,
            needs_evidence_opportunity_ids=needs_evidence,
            blocked_opportunity_ids=blocked,
            ranked_opportunities=normalized,
            research_targets=research_targets,
            highest_value_research_targets=research_targets,
            warnings=warnings,
        )


def _evaluate(
    opportunity: MonetizationOpportunity,
) -> RankedMonetizationOpportunity:
    uncertainty = list(opportunity.unknowns)
    missing_evidence: list[str] = []
    rationale: list[str] = []

    if not opportunity.evidence_refs:
        missing_evidence.append("explicit_evidence_refs")

    if opportunity.evidence_quality in {
        OpportunityEvidenceQuality.INSUFFICIENT,
        OpportunityEvidenceQuality.HYPOTHESIS,
    }:
        missing_evidence.append("stronger_market_or_operating_evidence")

    core_economic_inputs = {
        "time_to_first_dollar_days": opportunity.time_to_first_dollar_days,
        "expected_30_day_net_revenue_usd": opportunity.expected_30_day_net_revenue_usd,
        "expected_90_day_net_revenue_usd": opportunity.expected_90_day_net_revenue_usd,
        "expected_180_day_net_revenue_usd": opportunity.expected_180_day_net_revenue_usd,
        "upfront_capital_usd": opportunity.upfront_capital_usd,
        "capital_at_risk_usd": opportunity.capital_at_risk_usd,
        "daniel_hours_first_30_days": opportunity.daniel_hours_first_30_days,
        "daniel_hours_first_90_days": opportunity.daniel_hours_first_90_days,
    }

    for name, value in core_economic_inputs.items():
        if value is None:
            missing_evidence.append(name)

    optional_inputs = {
        "probability_of_success": opportunity.probability_of_success,
        "automation_potential": opportunity.automation_potential,
        "dfg_capability_reuse": opportunity.dfg_capability_reuse,
        "legal_compliance_risk": opportunity.legal_compliance_risk,
        "platform_dependency_risk": opportunity.platform_dependency_risk,
        "operational_complexity": opportunity.operational_complexity,
        "gross_margin_pct": opportunity.gross_margin_pct,
        "recurring_revenue_pct": opportunity.recurring_revenue_pct,
    }

    for name, value in optional_inputs.items():
        if value is None:
            missing_evidence.append(name)

    score = _score(opportunity)

    if opportunity.blockers:
        status = OpportunityStatus.BLOCKED
        uncertainty.extend(opportunity.blockers)
    elif (
        opportunity.evidence_quality
        in {
            OpportunityEvidenceQuality.INSUFFICIENT,
            OpportunityEvidenceQuality.HYPOTHESIS,
        }
        or not opportunity.evidence_refs
        or score is None
        or opportunity.expected_90_day_net_revenue_usd is None
        or opportunity.probability_of_success is None
    ):
        status = OpportunityStatus.NEEDS_EVIDENCE
    else:
        status = OpportunityStatus.ACTIONABLE

    expected_value_90 = None
    if (
        opportunity.probability_of_success is not None
        and opportunity.expected_90_day_net_revenue_usd is not None
        and opportunity.capital_at_risk_usd is not None
    ):
        midpoint_capital_at_risk = _midpoint(
            opportunity.capital_at_risk_usd.low,
            opportunity.capital_at_risk_usd.high,
        )
        if midpoint_capital_at_risk == 0.0:
            midpoint_90 = _midpoint(
                opportunity.expected_90_day_net_revenue_usd.low,
                opportunity.expected_90_day_net_revenue_usd.high,
            )
            expected_value_90 = round(
                midpoint_90 * opportunity.probability_of_success,
                2,
            )
        else:
            expected_value_90 = None
            uncertainty.append(
                f"capital_at_risk_usd is non-zero ({midpoint_capital_at_risk}) but loss probability distribution is unmodeled; expected_value_90_day_usd withheld to avoid inventing loss probability."
            )

    revenue_per_hour_90 = None
    if (
        opportunity.expected_90_day_net_revenue_usd is not None
        and opportunity.daniel_hours_first_90_days is not None
    ):
        midpoint_hours_90 = _midpoint(
            opportunity.daniel_hours_first_90_days.low,
            opportunity.daniel_hours_first_90_days.high,
        )
        if midpoint_hours_90 > 0:
            midpoint_rev_90 = _midpoint(
                opportunity.expected_90_day_net_revenue_usd.low,
                opportunity.expected_90_day_net_revenue_usd.high,
            )
            revenue_per_hour_90 = round(midpoint_rev_90 / midpoint_hours_90, 2)

    revenue_per_hour_30 = None
    if (
        opportunity.expected_30_day_net_revenue_usd is not None
        and opportunity.daniel_hours_first_30_days is not None
    ):
        midpoint_hours_30 = _midpoint(
            opportunity.daniel_hours_first_30_days.low,
            opportunity.daniel_hours_first_30_days.high,
        )
        if midpoint_hours_30 > 0:
            midpoint_rev_30 = _midpoint(
                opportunity.expected_30_day_net_revenue_usd.low,
                opportunity.expected_30_day_net_revenue_usd.high,
            )
            revenue_per_hour_30 = round(midpoint_rev_30 / midpoint_hours_30, 2)

    rationale.append(f"evidence={opportunity.evidence_quality.value}")
    if opportunity.time_to_first_dollar_days is not None:
        rationale.append(
            (
                "time_to_first_dollar_days="
                f"{opportunity.time_to_first_dollar_days.low}-"
                f"{opportunity.time_to_first_dollar_days.high}"
            )
        )
    if opportunity.expected_90_day_net_revenue_usd is not None:
        rationale.append(
            (
                "expected_90_day_net_revenue_usd="
                f"{opportunity.expected_90_day_net_revenue_usd.low}-"
                f"{opportunity.expected_90_day_net_revenue_usd.high}"
            )
        )
    if opportunity.upfront_capital_usd is not None:
        rationale.append(
            (
                "upfront_capital_usd="
                f"{opportunity.upfront_capital_usd.low}-"
                f"{opportunity.upfront_capital_usd.high}"
            )
        )
    if opportunity.daniel_hours_first_30_days is not None:
        rationale.append(
            (
                "daniel_hours_first_30_days="
                f"{opportunity.daniel_hours_first_30_days.low}-"
                f"{opportunity.daniel_hours_first_30_days.high}"
            )
        )
    if opportunity.daniel_hours_first_90_days is not None:
        rationale.append(
            (
                "daniel_hours_first_90_days="
                f"{opportunity.daniel_hours_first_90_days.low}-"
                f"{opportunity.daniel_hours_first_90_days.high}"
            )
        )

    if missing_evidence:
        uncertainty.append(
            "Missing evidence: " + ", ".join(sorted(set(missing_evidence)))
        )

    return RankedMonetizationOpportunity(
        rank=0,
        opportunity_id=opportunity.opportunity_id,
        title=opportunity.title,
        status=status,
        score=score,
        expected_value_90_day_usd=expected_value_90,
        revenue_per_daniel_hour_90_day=revenue_per_hour_90,
        revenue_per_daniel_hour_30_day=revenue_per_hour_30,
        evidence_quality=opportunity.evidence_quality,
        rationale=rationale,
        uncertainty=uncertainty,
        missing_evidence=sorted(set(missing_evidence)),
    )


def _score(opportunity: MonetizationOpportunity) -> float | None:
    required = (
        opportunity.probability_of_success,
        opportunity.automation_potential,
        opportunity.dfg_capability_reuse,
        opportunity.legal_compliance_risk,
        opportunity.platform_dependency_risk,
        opportunity.operational_complexity,
    )
    if (
        opportunity.time_to_first_dollar_days is None
        or opportunity.upfront_capital_usd is None
        or any(value is None for value in required)
    ):
        return None

    evidence_score = _EVIDENCE_SCORE[opportunity.evidence_quality]

    speed_score = max(
        0.0,
        100.0 - opportunity.time_to_first_dollar_days.high * 2.5,
    )

    capital_score = max(
        0.0,
        100.0 - opportunity.upfront_capital_usd.high / 50.0,
    )

    probability_score = opportunity.probability_of_success * 100.0

    automation_score = opportunity.automation_potential * 20.0
    reuse_score = opportunity.dfg_capability_reuse * 20.0

    legal_score = max(
        0.0,
        100.0 - opportunity.legal_compliance_risk * 18.0,
    )
    platform_score = max(
        0.0,
        100.0 - opportunity.platform_dependency_risk * 15.0,
    )
    complexity_score = max(
        0.0,
        100.0 - opportunity.operational_complexity * 15.0,
    )

    score = (
        evidence_score * 0.20
        + speed_score * 0.20
        + probability_score * 0.15
        + capital_score * 0.10
        + automation_score * 0.10
        + reuse_score * 0.10
        + legal_score * 0.05
        + platform_score * 0.05
        + complexity_score * 0.05
    )

    return round(score, 2)


def _ranking_key(
    item: RankedMonetizationOpportunity,
) -> tuple:
    status_rank = {
        OpportunityStatus.ACTIONABLE: 0,
        OpportunityStatus.NEEDS_EVIDENCE: 1,
        OpportunityStatus.BLOCKED: 2,
    }[item.status]

    score = item.score if item.score is not None else -1.0
    expected_value = (
        item.expected_value_90_day_usd
        if item.expected_value_90_day_usd is not None
        else float("-inf")
    )

    return (
        status_rank,
        -score,
        -expected_value,
        item.opportunity_id,
    )


def _research_targets(
    ranked: list[RankedMonetizationOpportunity],
) -> list[str]:
    targets: list[str] = []

    for item in ranked:
        if item.status is not OpportunityStatus.NEEDS_EVIDENCE:
            continue

        for missing in item.missing_evidence:
            targets.append(f"{item.opportunity_id}:{missing}")

    return targets


def _midpoint(low: float, high: float) -> float:
    return (low + high) / 2.0
