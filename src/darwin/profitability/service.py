"""Deterministic profitability path comparison service."""

from __future__ import annotations

from darwin.profitability.schemas import (
    CandidatePathType,
    DecisionStatus,
    EvidenceQuality,
    ProfitabilityComparisonRequest,
    ProfitabilityComparisonResult,
    ProfitabilityPathCandidate,
    RankedProfitabilityPath,
)

_EVIDENCE_SCORE = {
    EvidenceQuality.INSUFFICIENT: 0,
    EvidenceQuality.PRELIMINARY: 35,
    EvidenceQuality.PAPER_VALIDATED: 70,
    EvidenceQuality.CONTROLLED_LIVE_VALIDATED: 90,
}


class ProfitabilityPathComparisonService:
    """Rank candidate trading paths without converting projections into proof."""

    def compare(self, request: ProfitabilityComparisonRequest) -> ProfitabilityComparisonResult:
        ranked = sorted(
            [_rank_candidate(candidate) for candidate in request.candidates],
            key=lambda item: (-int(item.status == DecisionStatus.DEFENSIBLE), -item.score, item.rank),
        )
        normalized = [
            item.model_copy(update={"rank": index + 1}) for index, item in enumerate(ranked)
        ]
        defensible = [item for item in normalized if item.status == DecisionStatus.DEFENSIBLE]
        fastest = defensible[0].path_id if defensible else None
        secondary = defensible[1].path_id if len(defensible) > 1 else None
        warnings = _comparison_warnings(request, fastest)
        return ProfitabilityComparisonResult(
            fastest_defensible_path=fastest,
            secondary_path=secondary,
            rejected_or_deferred_paths=[
                item.path_id for item in normalized if item.status != DecisionStatus.DEFENSIBLE
            ],
            ranked_paths=normalized,
            capital_scenarios=request.capital_scenarios,
            seven_to_ten_percent_monthly_evidence=_monthly_target_evidence(request.candidates),
            warnings=warnings,
        )


def _rank_candidate(candidate: ProfitabilityPathCandidate) -> RankedProfitabilityPath:
    uncertainty: list[str] = []
    rationale: list[str] = []
    evidence_score = _EVIDENCE_SCORE[candidate.evidence_quality]
    if candidate.evidence_quality == EvidenceQuality.INSUFFICIENT:
        uncertainty.append("Evidence is insufficient for a defensible profitability path.")
    if not candidate.evidence_refs:
        uncertainty.append("No explicit evidence references were supplied.")
    if candidate.blockers:
        uncertainty.extend(candidate.blockers)

    status = DecisionStatus.DEFENSIBLE
    if candidate.evidence_quality == EvidenceQuality.INSUFFICIENT or not candidate.evidence_refs:
        status = DecisionStatus.DEFERRED_FOR_EVIDENCE
    if candidate.blockers:
        status = DecisionStatus.DEFERRED_FOR_EVIDENCE

    speed_score = max(0.0, 100.0 - candidate.time_to_paper_validation_days.high * 3.0)
    effort_score = max(0.0, 100.0 - candidate.engineering_effort_days.high * 5.0)
    complexity_score = max(0.0, 100.0 - candidate.operational_complexity * 12.0)
    risk_score = max(0.0, 100.0 - candidate.expected_drawdown_pct.high * 2.0)
    confidence_score = candidate.research_confidence * 100.0
    score = round(
        evidence_score * 0.30
        + speed_score * 0.22
        + effort_score * 0.18
        + confidence_score * 0.15
        + complexity_score * 0.10
        + risk_score * 0.05,
        2,
    )
    rationale.extend(
        [
            f"evidence={candidate.evidence_quality.value}",
            f"time_to_paper_days={candidate.time_to_paper_validation_days.low}-{candidate.time_to_paper_validation_days.high}",
            f"engineering_effort_days={candidate.engineering_effort_days.low}-{candidate.engineering_effort_days.high}",
            f"operational_complexity={candidate.operational_complexity}/5",
            f"expected_drawdown_pct={candidate.expected_drawdown_pct.low}-{candidate.expected_drawdown_pct.high}",
        ]
    )
    if candidate.path_type == CandidatePathType.ARBITRAGE:
        rationale.append("arbitrage_requires_fee_slippage_latency_and_inventory_evidence")
    return RankedProfitabilityPath(
        rank=0,
        path_id=candidate.path_id,
        title=candidate.title,
        path_type=candidate.path_type,
        status=status,
        score=score,
        rationale=rationale,
        evidence_quality=candidate.evidence_quality,
        uncertainty=uncertainty,
    )


def _monthly_target_evidence(candidates: list[ProfitabilityPathCandidate]) -> str:
    supporting = [
        candidate.path_id
        for candidate in candidates
        if candidate.expected_monthly_return_pct.low <= 10
        and candidate.expected_monthly_return_pct.high >= 7
        and candidate.evidence_quality
        in {EvidenceQuality.PAPER_VALIDATED, EvidenceQuality.CONTROLLED_LIVE_VALIDATED}
        and candidate.evidence_refs
    ]
    if supporting:
        return "SUPPORTED_BY_VALIDATED_EVIDENCE: " + ", ".join(sorted(supporting))
    return "INSUFFICIENT_EVIDENCE"


def _comparison_warnings(
    request: ProfitabilityComparisonRequest,
    fastest_defensible_path: str | None,
) -> list[str]:
    warnings: list[str] = []
    has_leveraged = any(
        round(item.capital_usd, 2) == 2000.0 and item.max_notional_exposure_usd > item.capital_usd
        for item in request.capital_scenarios
    )
    if not has_leveraged:
        warnings.append("No leveraged-notional scenario was supplied for the USD 2000 capital case.")
    if fastest_defensible_path is None:
        warnings.append("No candidate path is defensible until stronger evidence is supplied.")
    return warnings
