import pytest

from darwin.profitability import (
    CandidatePathType,
    DecisionStatus,
    EvidenceQuality,
    ProfitabilityComparisonRequest,
    ProfitabilityPathComparisonService,
)


def test_existing_strategy_can_rank_above_arbitrage_when_evidence_is_closer() -> None:
    request = _request(
        candidates=[
            _candidate(
                path_id="existing-dashboard-strategy",
                path_type=CandidatePathType.EXISTING_STRATEGY,
                evidence_quality=EvidenceQuality.PRELIMINARY,
                evidence_refs=["dashboard:server/strategies/index.js", "dashboard:server/services/backtestEngine.js"],
                paper_high=7,
                effort_high=3,
                complexity=2,
                confidence=0.58,
            ),
            _candidate(
                path_id="greenfield-arbitrage",
                path_type=CandidatePathType.ARBITRAGE,
                evidence_quality=EvidenceQuality.INSUFFICIENT,
                evidence_refs=[],
                paper_high=18,
                effort_high=15,
                complexity=5,
                confidence=0.25,
            ),
        ]
    )

    result = ProfitabilityPathComparisonService().compare(request)

    assert result.fastest_defensible_path == "existing-dashboard-strategy"
    assert result.ranked_paths[0].path_id == "existing-dashboard-strategy"
    assert result.ranked_paths[0].status == DecisionStatus.DEFENSIBLE
    assert result.ranked_paths[1].status == DecisionStatus.DEFERRED_FOR_EVIDENCE
    assert "greenfield-arbitrage" in result.rejected_or_deferred_paths


def test_seven_to_ten_percent_monthly_requires_validated_evidence() -> None:
    request = _request(
        candidates=[
            _candidate(
                path_id="attractive-but-unvalidated",
                path_type=CandidatePathType.ARBITRAGE,
                evidence_quality=EvidenceQuality.PRELIMINARY,
                evidence_refs=["operator-hypothesis"],
                monthly_low=7,
                monthly_high=10,
            )
        ]
    )

    result = ProfitabilityPathComparisonService().compare(request)

    assert result.seven_to_ten_percent_monthly_evidence == "INSUFFICIENT_EVIDENCE"


def test_validated_monthly_target_support_is_explicit() -> None:
    request = _request(
        candidates=[
            _candidate(
                path_id="paper-validated-strategy",
                path_type=CandidatePathType.EXISTING_STRATEGY,
                evidence_quality=EvidenceQuality.PAPER_VALIDATED,
                evidence_refs=["paper-run:123"],
                monthly_low=7,
                monthly_high=9,
            )
        ]
    )

    result = ProfitabilityPathComparisonService().compare(request)

    assert result.seven_to_ten_percent_monthly_evidence == (
        "SUPPORTED_BY_VALIDATED_EVIDENCE: paper-validated-strategy"
    )


def test_usd_2000_capital_scenario_is_required() -> None:
    payload = _request_payload()
    for scenario in payload["capital_scenarios"]:
        scenario["capital_usd"] = 1000
        scenario["max_notional_exposure_usd"] = 1000

    with pytest.raises(ValueError, match="USD 2000 capital scenario"):
        ProfitabilityComparisonRequest.model_validate(payload)


def test_capital_notional_and_risk_are_separate() -> None:
    request = _request()

    assert request.capital_scenarios[0].capital_usd == 2000
    assert request.capital_scenarios[0].max_notional_exposure_usd == 2000
    assert request.capital_scenarios[1].capital_usd == 2000
    assert request.capital_scenarios[1].max_notional_exposure_usd == 10000
    assert request.capital_scenarios[1].risk_per_trade_pct == 1


def _request(candidates=None) -> ProfitabilityComparisonRequest:
    payload = _request_payload()
    if candidates is not None:
        payload["candidates"] = [candidate.model_dump(mode="json") for candidate in candidates]
    return ProfitabilityComparisonRequest.model_validate(payload)


def _request_payload() -> dict:
    return {
        "objective": "Minimize time to credible positive expectancy.",
        "capital_scenarios": [
            {
                "capital_usd": 2000,
                "max_notional_exposure_usd": 2000,
                "risk_per_trade_pct": 1,
                "max_drawdown_pct": _range(5, 15, "percent"),
                "liquidation_risk": "none from leverage in unlevered scenario",
                "leverage_note": "unlevered capital scenario",
            },
            {
                "capital_usd": 2000,
                "max_notional_exposure_usd": 10000,
                "risk_per_trade_pct": 1,
                "max_drawdown_pct": _range(8, 25, "percent"),
                "liquidation_risk": "material if position sizing ignores liquidation distance",
                "leverage_note": "5x notional exposure is analysis only, not permission",
            },
        ],
        "candidates": [
            _candidate(
                path_id="baseline-existing",
                path_type=CandidatePathType.EXISTING_STRATEGY,
                evidence_quality=EvidenceQuality.PRELIMINARY,
                evidence_refs=["dashboard:server/strategies/index.js"],
            ).model_dump(mode="json")
        ],
    }


def _candidate(
    *,
    path_id: str,
    path_type: CandidatePathType,
    evidence_quality: EvidenceQuality,
    evidence_refs: list[str],
    paper_high: int = 10,
    effort_high: int = 4,
    complexity: int = 3,
    confidence: float = 0.45,
    monthly_low: float = 1,
    monthly_high: float = 6,
):
    from darwin.profitability import ProfitabilityPathCandidate

    return ProfitabilityPathCandidate(
        path_id=path_id,
        path_type=path_type,
        title=path_id.replace("-", " ").title(),
        thesis="Candidate path for comparison.",
        evidence_quality=evidence_quality,
        evidence_refs=evidence_refs,
        blockers=[],
        time_to_paper_validation_days=_range(2, paper_high, "days"),
        time_to_controlled_live_validation_days=_range(14, 45, "days"),
        engineering_effort_days=_range(1, effort_high, "days"),
        research_confidence=confidence,
        capital_required_usd=_range(2000, 2000, "usd"),
        expected_monthly_return_pct=_range(monthly_low, monthly_high, "percent"),
        expected_drawdown_pct=_range(5, 18, "percent"),
        tail_risk="not yet measured",
        operational_complexity=complexity,
        data_requirements=["OHLCV history", "fees"],
        infrastructure_requirements=["paper validation"],
        dependency_risk="medium",
    )


def _range(low: float, high: float, unit: str) -> dict:
    return {
        "low": low,
        "high": high,
        "unit": unit,
        "confidence": 0.5,
        "rationale": "test fixture",
    }
