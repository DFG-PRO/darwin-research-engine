"""Deterministic verification tests for Portfolio 01 baseline monetization opportunities."""

import pytest
from pydantic import ValidationError

from darwin.monetization import (
    MonetizationOpportunity,
    MonetizationOpportunityPortfolioService,
    MonetizationPortfolioRequest,
    OpportunityEvidenceQuality,
    OpportunityStatus,
    PORTFOLIO_01_REQUEST,
    build_portfolio_01_request,
)

EXPECTED_OPPORTUNITY_IDS = {
    "fp-labs-external-services",
    "commercial-product-photography",
    "cinema-collection-equipment-rental",
    "production-engine-acceleration",
    "trading-strategy-hardening",
    "fpcriptoclub-monetization",
    "billy-the-trader",
    "airbnb-experiences-photography",
    "section-8-real-estate",
    "prediction-markets-latam",
    "arbitrage-engine",
    "tiktok-shop-affiliate-creative",
}

EXPECTED_BLOCKED_IDS = {
    "arbitrage-engine",
    "prediction-markets-latam",
    "section-8-real-estate",
}

EXPECTED_NEEDS_EVIDENCE_IDS = EXPECTED_OPPORTUNITY_IDS - EXPECTED_BLOCKED_IDS


def test_portfolio_01_request_validates_and_has_12_unique_opportunities() -> None:
    request = PORTFOLIO_01_REQUEST
    assert isinstance(request, MonetizationPortfolioRequest)
    assert len(request.opportunities) == 12
    opportunity_ids = [opp.opportunity_id for opp in request.opportunities]
    assert len(opportunity_ids) == len(set(opportunity_ids))
    assert set(opportunity_ids) == EXPECTED_OPPORTUNITY_IDS


def test_build_portfolio_01_request_returns_independent_copy() -> None:
    req1 = build_portfolio_01_request()
    req2 = build_portfolio_01_request()
    assert req1 is not req2
    assert len(req1.opportunities) == 12
    assert req1.opportunities[0] is not req2.opportunities[0]
    assert req1.opportunities[0].opportunity_id == req2.opportunities[0].opportunity_id


def test_zero_economic_imputation_in_portfolio_01_definitions() -> None:
    economic_fields = [
        "time_to_first_dollar_days",
        "expected_30_day_net_revenue_usd",
        "expected_90_day_net_revenue_usd",
        "expected_180_day_net_revenue_usd",
        "upfront_capital_usd",
        "capital_at_risk_usd",
        "daniel_hours_first_30_days",
        "daniel_hours_first_90_days",
        "gross_margin_pct",
        "recurring_revenue_pct",
        "probability_of_success",
        "automation_potential",
        "dfg_capability_reuse",
        "legal_compliance_risk",
        "platform_dependency_risk",
        "operational_complexity",
    ]

    for opp in PORTFOLIO_01_REQUEST.opportunities:
        for field in economic_fields:
            assert getattr(opp, field) is None, f"{opp.opportunity_id}.{field} must be None (no imputation)"


def test_evidence_references_provenance_strictness() -> None:
    for opp in PORTFOLIO_01_REQUEST.opportunities:
        if opp.opportunity_id in {"trading-strategy-hardening", "arbitrage-engine"}:
            assert opp.evidence_refs == ["docs/runtime/profitability-decision-framework.md"]
        else:
            assert opp.evidence_refs == [], f"{opp.opportunity_id} must have empty evidence_refs without concrete provenance"


def test_portfolio_01_evaluation_satisfies_governance_gates() -> None:
    service = MonetizationOpportunityPortfolioService()
    result = service.compare(PORTFOLIO_01_REQUEST)

    # 1. Zero opportunities are ACTIONABLE
    assert len(result.actionable_opportunity_ids) == 0

    # 2. Blocked opportunities match exactly
    assert set(result.blocked_opportunity_ids) == EXPECTED_BLOCKED_IDS

    # 3. Needs evidence opportunities match exactly
    assert set(result.needs_evidence_opportunity_ids) == EXPECTED_NEEDS_EVIDENCE_IDS

    # 4. Total ranked count equals 12
    assert len(result.ranked_opportunities) == 12

    # 5. Derived metrics are None for all ranked opportunities lacking required inputs
    for ranked in result.ranked_opportunities:
        assert ranked.score is None
        assert ranked.expected_value_90_day_usd is None
        assert ranked.revenue_per_daniel_hour_90_day is None
        assert ranked.revenue_per_daniel_hour_30_day is None

    # 6. Research targets emitted for all NEEDS_EVIDENCE items
    assert len(result.research_targets) > 0
    target_opp_ids = {t.split(":")[0] for t in result.research_targets}
    assert target_opp_ids == EXPECTED_NEEDS_EVIDENCE_IDS

    # 7. Warnings emitted regarding actionable state and preserved evidence gaps
    assert any("No opportunity is currently actionable" in w for w in result.warnings)
    assert any("Evidence gaps remain explicit" in w for w in result.warnings)


def test_portfolio_01_fails_closed_on_malformed_input() -> None:
    with pytest.raises(ValidationError):
        MonetizationOpportunity(
            opportunity_id="",  # blank not permitted
            title="Invalid",
            thesis="Invalid thesis",
            evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        )

    with pytest.raises(ValidationError):
        MonetizationPortfolioRequest(
            objective="",  # blank not permitted
            opportunities=[],  # empty not permitted
        )
