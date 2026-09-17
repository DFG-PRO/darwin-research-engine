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
    # 1. Zero capital at risk: EV is legitimately supported (5000 * 0.5 = 2500)
    opportunity_zero_risk = _opportunity(
        opportunity_id="zero-risk",
        evidence_quality=OpportunityEvidenceQuality.VALIDATED,
        evidence_refs=["validated-demand"],
        revenue_90_low=4000,
        revenue_90_high=6000,
        probability=0.5,
        capital_at_risk_low=0,
        capital_at_risk_high=0,
    )

    result_zero = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Evaluate zero capital risk EV.",
            opportunities=[opportunity_zero_risk],
        )
    )
    assert result_zero.ranked_opportunities[0].expected_value_90_day_usd == 2500.0

    # 2. Non-zero capital at risk without loss distribution: EV withheld to avoid inventing loss probability
    opportunity_with_risk = opportunity_zero_risk.model_copy(
        update={
            "capital_at_risk_usd": _range(500, 500, "usd"),
        }
    )
    result_risk = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Compare bounded capital exposure.",
            opportunities=[opportunity_with_risk],
        )
    )
    item = result_risk.ranked_opportunities[0]
    assert item.expected_value_90_day_usd is None
    assert any("loss probability distribution is unmodeled" in note for note in item.uncertainty)


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

    # Primary field
    assert "needs-research:explicit_evidence_refs" in result.research_targets
    assert "needs-research:stronger_market_or_operating_evidence" in result.research_targets
    assert "needs-research:probability_of_success" in result.research_targets

    # Backward compatibility alias
    assert "needs-research:explicit_evidence_refs" in result.highest_value_research_targets
    assert result.research_targets == result.highest_value_research_targets


def test_no_imputation_for_missing_economic_ranges() -> None:
    opportunity = MonetizationOpportunity(
        opportunity_id="unquantified-concept",
        title="Unquantified Concept",
        thesis="A concept with no economic ranges yet estimated.",
        evidence_quality=OpportunityEvidenceQuality.PRELIMINARY,
        evidence_refs=["note:preliminary-brainstorm"],
        # Core economic inputs omitted (None)
        time_to_first_dollar_days=None,
        expected_30_day_net_revenue_usd=None,
        expected_90_day_net_revenue_usd=None,
        expected_180_day_net_revenue_usd=None,
        upfront_capital_usd=None,
        capital_at_risk_usd=None,
        daniel_hours_first_30_days=None,
        daniel_hours_first_90_days=None,
        probability_of_success=None,
    )

    result = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Verify no placeholder imputation.",
            opportunities=[opportunity],
        )
    )

    item = result.ranked_opportunities[0]
    assert item.status is OpportunityStatus.NEEDS_EVIDENCE
    assert item.score is None
    assert item.expected_value_90_day_usd is None
    assert item.revenue_per_daniel_hour_90_day is None
    assert item.revenue_per_daniel_hour_30_day is None

    assert "time_to_first_dollar_days" in item.missing_evidence
    assert "expected_90_day_net_revenue_usd" in item.missing_evidence
    assert "upfront_capital_usd" in item.missing_evidence
    assert "unquantified-concept:expected_90_day_net_revenue_usd" in result.research_targets


def test_daniel_hour_semantics_does_not_mix_horizons() -> None:
    # 1. 90-day revenue with 30-day hours only: 90-day metric MUST remain None
    mixed_opportunity = _opportunity(
        opportunity_id="mixed-horizon",
        evidence_quality=OpportunityEvidenceQuality.VALIDATED,
        evidence_refs=["ref:ops"],
        revenue_90_low=3000,
        revenue_90_high=9000,
    ).model_copy(
        update={
            "daniel_hours_first_30_days": _range(10, 10, "hours"),
            "daniel_hours_first_90_days": None,
        }
    )

    result = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Enforce horizon isolation.",
            opportunities=[mixed_opportunity],
        )
    )
    item = result.ranked_opportunities[0]
    assert item.revenue_per_daniel_hour_90_day is None

    # 2. Supplying matching 90-day hours computes 90-day revenue / 90-day hours
    matching_opportunity = mixed_opportunity.model_copy(
        update={
            "daniel_hours_first_90_days": _range(20, 40, "hours"),  # midpoint 30
        }
    )
    result_matching = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Compute matching 90-day ratio.",
            opportunities=[matching_opportunity],
        )
    )
    item_matching = result_matching.ranked_opportunities[0]
    # 6000 midpoint revenue / 30 midpoint hours = 200.0
    assert item_matching.revenue_per_daniel_hour_90_day == 200.0

    # 3. Matching 30-day ratio: 1000 midpoint revenue / 10 midpoint hours = 100.0
    assert item_matching.revenue_per_daniel_hour_30_day == 100.0


def test_actionable_evidence_gate_requires_positive_evidence_and_score() -> None:
    # High evidence quality and evidence refs, but missing score input (automation_potential is None)
    opportunity = _opportunity(
        opportunity_id="incomplete-score",
        evidence_quality=OpportunityEvidenceQuality.VALIDATED,
        evidence_refs=["ref:prod"],
        probability=0.8,
    ).model_copy(
        update={
            "automation_potential": None,
        }
    )

    result = MonetizationOpportunityPortfolioService().compare(
        MonetizationPortfolioRequest(
            objective="Ensure positive evidence gate.",
            opportunities=[opportunity],
        )
    )
    item = result.ranked_opportunities[0]
    assert item.score is None
    # Must NOT qualify as ACTIONABLE when score is None
    assert item.status is OpportunityStatus.NEEDS_EVIDENCE
    assert "incomplete-score" in result.needs_evidence_opportunity_ids
    assert "incomplete-score" not in result.actionable_opportunity_ids


def test_research_targets_alias_backward_compatibility() -> None:
    from darwin.monetization import MonetizationPortfolioResult

    # Specified via research_targets
    res1 = MonetizationPortfolioResult(
        actionable_opportunity_ids=[],
        needs_evidence_opportunity_ids=["opp-1"],
        blocked_opportunity_ids=[],
        ranked_opportunities=[],
        research_targets=["opp-1:missing_metric"],
    )
    assert res1.research_targets == ["opp-1:missing_metric"]
    assert res1.highest_value_research_targets == ["opp-1:missing_metric"]

    # Specified via highest_value_research_targets (legacy)
    res2 = MonetizationPortfolioResult(
        actionable_opportunity_ids=[],
        needs_evidence_opportunity_ids=["opp-1"],
        blocked_opportunity_ids=[],
        ranked_opportunities=[],
        highest_value_research_targets=["opp-1:missing_metric"],
    )
    assert res2.research_targets == ["opp-1:missing_metric"]
    assert res2.highest_value_research_targets == ["opp-1:missing_metric"]


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
    capital_at_risk_low: float = 0,
    capital_at_risk_high: float = 0,
    daniel_hours_90_low: float = 15,
    daniel_hours_90_high: float = 60,
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
        capital_at_risk_usd=_range(capital_at_risk_low, capital_at_risk_high, "usd"),
        daniel_hours_first_30_days=_range(5, 20, "hours"),
        daniel_hours_first_90_days=_range(daniel_hours_90_low, daniel_hours_90_high, "hours"),
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
