"""Deterministic verification tests for ResearchTargetGrouper."""

import pytest

from darwin.monetization import (
    PORTFOLIO_01_REQUEST,
    MonetizationOpportunityPortfolioService,
    ResearchPackage,
    ResearchTargetGrouper,
    TargetCompressionResult,
)


def test_grouper_handles_empty_input() -> None:
    grouper = ResearchTargetGrouper()
    result = grouper.compress([])
    assert isinstance(result, TargetCompressionResult)
    assert result.total_atomic_targets == 0
    assert result.total_packages == 0
    assert result.packages == []
    assert result.packages_by_opportunity == {}


def test_grouper_compresses_portfolio_01_targets_completely() -> None:
    portfolio_service = MonetizationOpportunityPortfolioService()
    portfolio_result = portfolio_service.compare(PORTFOLIO_01_REQUEST)
    raw_targets = portfolio_result.research_targets

    assert len(raw_targets) == 160

    grouper = ResearchTargetGrouper()
    compression_result = grouper.compress(raw_targets)

    # 1. Total atomic targets match exactly
    assert compression_result.total_atomic_targets == 160

    # 2. Compression reduces operational count significantly (ratio >= 2.5x)
    assert compression_result.compression_ratio >= 2.5
    assert compression_result.total_packages < len(raw_targets)
    assert compression_result.total_packages == len(compression_result.packages)

    # 3. Exactly the 9 NEEDS_EVIDENCE opportunities are grouped
    expected_opp_ids = set(portfolio_result.needs_evidence_opportunity_ids)
    assert set(compression_result.packages_by_opportunity.keys()) == expected_opp_ids

    # 4. Zero loss of atomic targets (every single atomic target is preserved)
    recovered_targets = set()
    for pkg in compression_result.packages:
        assert isinstance(pkg, ResearchPackage)
        assert pkg.package_id
        assert pkg.opportunity_id in expected_opp_ids
        assert len(pkg.target_fields) > 0
        for field in pkg.target_fields:
            recovered_targets.add(f"{pkg.opportunity_id}:{field}")

    assert recovered_targets == set(raw_targets)


def test_grouper_is_deterministic_and_idempotent() -> None:
    portfolio_service = MonetizationOpportunityPortfolioService()
    raw_targets = portfolio_service.compare(PORTFOLIO_01_REQUEST).research_targets

    grouper = ResearchTargetGrouper()
    res1 = grouper.compress(raw_targets)
    res2 = grouper.compress(raw_targets)

    assert res1.model_dump() == res2.model_dump()


def test_grouper_handles_unknown_or_novel_fields_gracefully() -> None:
    novel_targets = [
        "fp-labs-external-services:custom_proprietary_metric",
        "cinema-collection-equipment-rental:special_lens_coating_risk",
    ]
    grouper = ResearchTargetGrouper()
    res = grouper.compress(novel_targets)

    assert res.total_atomic_targets == 2
    assert res.total_packages == 2
    for pkg in res.packages:
        assert pkg.cluster_name == "GENERAL_EVIDENCE"
