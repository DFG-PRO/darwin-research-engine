"""Tests for ResearchPackageAdapter connecting packages to research execution."""

import pytest

from darwin.monetization import (
    PORTFOLIO_01_REQUEST,
    MonetizationOpportunityPortfolioService,
    PackageObjectiveType,
    ResearchPackage,
    ResearchPackageAdapter,
    ResearchPackageObjective,
    ResearchTargetGrouper,
)
from darwin.monetization.portfolio import PORTFOLIO_01_OPPORTUNITIES


def test_full_portfolio_01_pipeline_to_objectives():
    """Verify Portfolio 01 -> 160 targets -> 53 packages -> 53 objectives with 100% provenance."""
    svc = MonetizationOpportunityPortfolioService()
    comp = svc.compare(PORTFOLIO_01_REQUEST)
    targets = comp.research_targets
    assert len(targets) == 160

    grouper = ResearchTargetGrouper()
    compressed = grouper.compress(targets)
    assert compressed.total_packages == 53
    assert len(compressed.packages) == 53

    adapter = ResearchPackageAdapter()
    objectives = adapter.adapt_all(compressed.packages, opportunities=PORTFOLIO_01_OPPORTUNITIES)
    assert len(objectives) == 53

    # Verify 100% provenance retention across all objectives
    total_atomic_in_objectives = 0
    for obj, pkg in zip(objectives, compressed.packages):
        assert obj.package_id == pkg.package_id
        assert obj.opportunity_id == pkg.opportunity_id
        assert obj.cluster_name == pkg.cluster_name
        assert obj.target_fields == pkg.target_fields
        expected_atomics = [f"{pkg.opportunity_id}:{f}" for f in pkg.target_fields]
        assert obj.atomic_target_ids == expected_atomics
        total_atomic_in_objectives += len(obj.atomic_target_ids)

    assert total_atomic_in_objectives == 160


def test_operator_intake_bandwidth_cluster_prevents_web_substitution():
    """Verify that operational bandwidth packages require operator input and reject web loop execution."""
    adapter = ResearchPackageAdapter()
    pkg = ResearchPackage(
        package_id="TEST_OPP_OPERATIONAL_BANDWIDTH",
        opportunity_id="test-opp",
        cluster_name="OPERATIONAL_BANDWIDTH",
        title="test-opp: Operational Bandwidth",
        objective="Determine Daniel hours and delivery lead times.",
        target_fields=["daniel_hours_first_30_days", "time_to_first_dollar_days"],
    )

    obj = adapter.adapt_package(pkg)
    assert obj.requires_operator_input is True
    assert obj.objective_type == PackageObjectiveType.OPERATOR_INTAKE
    assert obj.can_execute_via_web_loop() is False
    assert "Operator must provide" in (obj.operator_instructions or "")

    # Attempting to convert to a web research loop must fail closed
    with pytest.raises(ValueError, match="requires operator evidence and cannot be executed via web research loop"):
        obj.to_research_loop_request()


def test_cinema_collection_operator_evidence_routing():
    """Verify Cinema Collection equipment manifest requires operator evidence."""
    adapter = ResearchPackageAdapter()
    pkg = ResearchPackage(
        package_id="CINEMA_COLLECTION_EQUIPMENT_RENTAL_CAPITAL_AND_RISK",
        opportunity_id="cinema-collection-equipment-rental",
        cluster_name="CAPITAL_AND_RISK",
        title="Cinema Collection: Capital & Risk",
        objective="Determine equipment replacement value and upfront outlay.",
        target_fields=["upfront_capital_usd", "capital_at_risk_usd"],
    )

    obj = adapter.adapt_package(pkg)
    assert obj.requires_operator_input is True
    assert obj.objective_type == PackageObjectiveType.OPERATOR_INTAKE
    assert obj.can_execute_via_web_loop() is False
    assert "equipment manifest" in (obj.operator_instructions or "").lower()


def test_web_executable_package_converts_to_research_loop_request():
    """Verify that web-executable packages convert cleanly to canonical ResearchLoopRequest."""
    adapter = ResearchPackageAdapter()
    pkg = ResearchPackage(
        package_id="COMMERCIAL_PRODUCT_PHOTOGRAPHY_PRICING_AND_REVENUE",
        opportunity_id="commercial-product-photography",
        cluster_name="PRICING_AND_REVENUE",
        title="Commercial Product Photography: Pricing & Revenue",
        objective="Determine studio day rates and margin benchmarks.",
        target_fields=["expected_30_day_net_revenue_usd", "gross_margin_pct"],
    )

    obj = adapter.adapt_package(pkg)
    assert obj.requires_operator_input is False
    assert obj.objective_type == PackageObjectiveType.WEB_RESEARCH
    assert obj.can_execute_via_web_loop() is True
    assert len(obj.search_queries) > 0

    req = obj.to_research_loop_request()
    assert req.research_question == obj.research_question
    assert req.metadata["package_id"] == pkg.package_id
    assert req.metadata["opportunity_id"] == pkg.opportunity_id
    assert req.metadata["atomic_target_ids"] == ["commercial-product-photography:expected_30_day_net_revenue_usd", "commercial-product-photography:gross_margin_pct"]
    assert req.metadata["cluster_name"] == "PRICING_AND_REVENUE"


def test_blocked_opportunity_handling():
    """Verify that blocked opportunities are flagged and reject web loop conversion."""
    adapter = ResearchPackageAdapter()
    pkg = ResearchPackage(
        package_id="SECTION_8_REAL_ESTATE_PRICING_AND_REVENUE",
        opportunity_id="section-8-real-estate",
        cluster_name="PRICING_AND_REVENUE",
        title="Section 8: Pricing & Revenue",
        objective="Determine Fair Market Rents.",
        target_fields=["expected_30_day_net_revenue_usd"],
    )

    obj = adapter.adapt_package(pkg)
    assert obj.is_blocked is True
    assert obj.jurisdiction == "US"
    assert obj.can_execute_via_web_loop() is False

    with pytest.raises(ValueError, match="is blocked"):
        obj.to_research_loop_request()


def test_jurisdiction_preservation():
    """Verify jurisdiction is correctly set for LATAM and US opportunities."""
    adapter = ResearchPackageAdapter()
    pkg_latam = ResearchPackage(
        package_id="PREDICTION_MARKETS_LATAM_MARKET_AND_GOVERNANCE_RISK",
        opportunity_id="prediction-markets-latam",
        cluster_name="MARKET_AND_GOVERNANCE_RISK",
        title="LATAM Prediction Markets: Market Risk",
        objective="Verify regulatory frameworks.",
        target_fields=["legal_compliance_risk"],
    )
    obj_latam = adapter.adapt_package(pkg_latam)
    assert obj_latam.jurisdiction == "LATAM"

    pkg_us = ResearchPackage(
        package_id="SECTION_8_REAL_ESTATE_CAPITAL_AND_RISK",
        opportunity_id="section-8-real-estate",
        cluster_name="CAPITAL_AND_RISK",
        title="Section 8: Capital & Risk",
        objective="Verify acquisition capital.",
        target_fields=["upfront_capital_usd"],
    )
    obj_us = adapter.adapt_package(pkg_us)
    assert obj_us.jurisdiction == "US"


def test_deterministic_adaptation_idempotence():
    """Verify that adapting the same package repeatedly yields identical results."""
    adapter = ResearchPackageAdapter()
    pkg = ResearchPackage(
        package_id="BILLY_THE_TRADER_PRICING_AND_REVENUE",
        opportunity_id="billy-the-trader",
        cluster_name="PRICING_AND_REVENUE",
        title="Billy: Pricing & Revenue",
        objective="Determine sponsorship rates.",
        target_fields=["expected_30_day_net_revenue_usd", "gross_margin_pct"],
    )

    obj1 = adapter.adapt_package(pkg)
    obj2 = adapter.adapt_package(pkg)
    assert obj1.model_dump() == obj2.model_dump()
