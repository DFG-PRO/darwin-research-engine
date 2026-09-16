import pytest

from darwin.monetization import (
    MonetizationOpportunity,
    MonetizationOpportunityPortfolioService,
    MonetizationPortfolioRequest,
    OpportunityEvidenceQuality,
    OpportunityStatus,
)


def test_actionable_opportunity_can_rank_first() -> None:
    request = MonetizationPortfolioRequest(
        objective="Prioritize shortest credible path to net revenue.",
        opportunities=[
            _opportunity(
                opportunity_id="service-business",
                evidence_quality=OpportunityEvidenceQuality.VALIDATED,
                evidence_refs=["client-history:commercial-production"],
                first_dollar_high=10,
                revenue_90_low=3000,
                revenue_90_high=9000,
                probability=0.7,
            ),
            _opportunity(
                opportunity_id="speculative-platform",
                evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
                evidence_refs=[],
                first_dollar_high=90,
                revenue_90_low=0,
                revenue_90_high=20000,
                probability=None,
            ),
        ],
    )

    result = MonetizationOpportunityPortfolioService().compare(request)

    assert result.ranked_opportunities[0].opportunity_id == "service-business"
    assert result.ranked_opportunities[0].status is OpportunityStatus.ACTIONABLE
    assert result.ranked_opportunities[1].status is OpportunityStatus.NEEDS_EVIDENCE


def test_missing_probability_does_not_get_imputed() -> None:
    request = MonetizationPortfolioRequest(
        objective="Preserve uncertainty.",
        opportunities=[
            _opportunity(
                opportunity_id="unknown-probability",
                evidence_quality=OpportunityEvidenceQuality.PRELIMINARY,
                evidence_refs=["research:1"],
                probability=None,
            )
        ],
    )

    result = MonetizationOpportunityPortfolioService().compare(request)
    item = result.ranked_opportunities[0]

    assert item.status is OpportunityStatus.NEEDS_EVIDENCE
    assert item.score is None
    assert item.expected_value_90_day_usd is None
    assert "probability_of_success" in item.missing_evidence


def test_missing_optional_score_input_prevents_false_precision() -> None:
    opportunity = _opportunity(
        opportunity_id="missing-automation",
        evidence_quality=OpportunityEvidenceQuality.VALIDATED,
        evidence_refs=["research:2"],
        probability=0.6,
    ).model_copy(update={"automation_potential": None})

    result = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Avoid false precision.",
            opportunities=[opportunity],
        )
    )

    item = result.ranked_opportunities[0]

    assert item.score is None
    assert "automation_potential" in item.missing_evidence


def test_blocker_produces_blocked_status() -> None:
    opportunity = _opportunity(
        opportunity_id="regulated-opportunity",
        evidence_quality=OpportunityEvidenceQuality.VALIDATED,
        evidence_refs=["legal-review:pending"],
        probability=0.5,
    ).model_copy(update={"blockers": ["legal clearance required"]})

    result = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Respect compliance blockers.",
            opportunities=[opportunity],
        )
    )

    assert result.ranked_opportunities[0].status is OpportunityStatus.BLOCKED
    assert result.blocked_opportunity_ids == ["regulated-opportunity"]


def test_expected_value_keeps_capital_at_risk_separate() -> None:
    opportunity = _opportunity(
        opportunity_id="bounded-investment",
        evidence_quality=OpportunityEvidenceQuality.VALIDATED,
        evidence_refs=["validated-demand"],
        revenue_90_low=4000,
        revenue_90_high=6000,
        probability=0.5,
    ).model_copy(
        update={
            "capital_at_risk_usd": _range(500, 500, "usd"),
        }
    )

    result = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Compare bounded capital exposure.",
            opportunities=[opportunity],
        )
    )

    assert result.ranked_opportunities[0].expected_value_90_day_usd == 2000


def test_research_targets_expose_missing_evidence() -> None:
    opportunity = _opportunity(
        opportunity_id="needs-research",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        probability=None,
    )

    result = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Find highest-value evidence gaps.",
            opportunities=[opportunity],
        )
    )

    assert "needs-research:explicit_evidence_refs" in result.highest_value_research_targets
    assert (
        "needs-research:stronger_market_or_operating_evidence"
        in result.highest_value_research_targets
    )
    assert "needs-research:probability_of_success" in result.highest_value_research_targets


def test_duplicate_opportunity_ids_fail_closed() -> None:
    opportunity = _opportunity(
        opportunity_id="duplicate",
        evidence_quality=OpportunityEvidenceQuality.PRELIMINARY,
        evidence_refs=["research:x"],
        probability=0.4,
    )

    with pytest.raises(ValueError, match="must be unique"):
        MonetizationPortfolioRequest(
            objective="No ambiguous identity.",
            opportunities=[opportunity, opportunity],
        )


def test_invalid_range_fails_closed() -> None:
    with pytest.raises(ValueError, match="range high"):
        _range(10, 1, "days")


def _opportunity(
    *,
    opportunity_id: str,
    evidence_quality: OpportunityEvidenceQuality,
    evidence_refs: list[str],
    first_dollar_high: float = 20,
    revenue_90_low: float = 1000,
    revenue_90_high: float = 5000,
    probability: float | None = 0.5,
) -> MonetizationOpportunity:
    return MonetizationOpportunity(
        opportunity_id=opportunity_id,
        title=opportunity_id.replace("-", " ").title(),
        thesis="Bounded opportunity for deterministic comparison.",
        evidence_quality=evidence_quality,
        evidence_refs=evidence_refs,
        blockers=[],
        unknowns=[],
        time_to_first_dollar_days=_range(1, first_dollar_high, "days"),
        expected_30_day_net_revenue_usd=_range(0, 2000, "usd"),
        expected_90_day_net_revenue_usd=_range(
            revenue_90_low,
            revenue_90_high,
            "usd",
        ),
        expected_180_day_net_revenue_usd=_range(2000, 12000, "usd"),
        upfront_capital_usd=_range(0, 500, "usd"),
        capital_at_risk_usd=_range(0, 250, "usd"),
        daniel_hours_first_30_days=_range(5, 20, "hours"),
        gross_margin_pct=_range(40, 80, "percent"),
        recurring_revenue_pct=_range(10, 60, "percent"),
        probability_of_success=probability,
        automation_potential=4,
        dfg_capability_reuse=4,
        legal_compliance_risk=2,
        platform_dependency_risk=2,
        operational_complexity=2,
    )


def _range(low: float, high: float, unit: str):
    from darwin.monetization import OpportunityRange

    return OpportunityRange(
        low=low,
        high=high,
        unit=unit,
        confidence=0.5,
        rationale="test fixture",
    )
