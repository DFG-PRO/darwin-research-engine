"""Deterministic verification tests for MetricReadinessEngine."""

import pytest

from darwin.monetization import (
    MetricEvidenceUnit,
    MetricReadinessAssessment,
    MetricReadinessEngine,
    MetricReadinessStatus,
)


def test_no_evidence_returns_insufficient_evidence() -> None:
    engine = MetricReadinessEngine()
    res = engine.assess(
        opportunity_id="fp-labs-external-services",
        metric="expected_30_day_net_revenue_usd",
        evidence=[],
    )
    assert res.status == MetricReadinessStatus.INSUFFICIENT_EVIDENCE
    assert not res.derivation_allowed
    assert "positive_evidence_required" in res.missing_requirements


def test_active_blocker_returns_blocked_by_dependency() -> None:
    engine = MetricReadinessEngine()
    res = engine.assess(
        opportunity_id="prediction-markets-latam",
        metric="expected_90_day_net_revenue_usd",
        evidence=[
            MetricEvidenceUnit(
                evidence_id="ev_001",
                source_type="PRIMARY_WEB_SOURCE",
                claim_type="BENCHMARK",
                statement="Polymarket monthly trading volume is $1B.",
            )
        ],
        blockers=["Regulatory licensing required"],
    )
    assert res.status == MetricReadinessStatus.BLOCKED_BY_DEPENDENCY
    assert not res.derivation_allowed
    assert "Regulatory licensing required" in res.missing_requirements


def test_market_benchmark_alone_cannot_unlock_expected_revenue() -> None:
    engine = MetricReadinessEngine()
    res = engine.assess(
        opportunity_id="commercial-product-photography",
        metric="expected_30_day_net_revenue_usd",
        evidence=[
            MetricEvidenceUnit(
                evidence_id="ev_002",
                source_type="EXTERNAL_MARKET_BENCHMARK",
                claim_type="BENCHMARK",
                statement="Commercial product photo day rate in CDMX is $8,000-$20,000 MXN.",
            )
        ],
    )
    assert res.status == MetricReadinessStatus.REQUIRES_EMPIRICAL_TEST
    assert not res.derivation_allowed
    assert any("conversion" in r or "volume" in r for r in res.missing_requirements)


def test_complete_pricing_volume_and_cost_evidence_unlocks_revenue_range() -> None:
    engine = MetricReadinessEngine()
    res = engine.assess(
        opportunity_id="cinema-collection-equipment-rental",
        metric="expected_30_day_net_revenue_usd",
        evidence=[
            MetricEvidenceUnit(
                evidence_id="ev_pricing",
                source_type="PRIMARY_WEB_SOURCE",
                claim_type="BENCHMARK",
                statement="RED Komodo rental rate is $200 USD/day in CDMX.",
            ),
            MetricEvidenceUnit(
                evidence_id="ev_volume",
                source_type="EMPIRICAL_TEST",
                claim_type="EMPIRICAL_MEASUREMENT",
                statement="Measured 2 confirmed rental bookings per month from listing.",
            ),
            MetricEvidenceUnit(
                evidence_id="ev_cost",
                source_type="PRIMARY_WEB_SOURCE",
                claim_type="PLATFORM_TERMS",
                statement="ShareGrid platform deduction is 15% fixed.",
            ),
        ],
    )
    assert res.status == MetricReadinessStatus.READY_FOR_RANGE
    assert res.derivation_allowed
    assert len(res.supporting_evidence_ids) == 3


def test_internal_capability_evidence_unlocks_capability_metrics() -> None:
    engine = MetricReadinessEngine()
    res = engine.assess(
        opportunity_id="production-engine-acceleration",
        metric="automation_potential",
        evidence=[
            MetricEvidenceUnit(
                evidence_id="ev_billy",
                source_type="INTERNAL_REPOSITORY",
                claim_type="CAPABILITY",
                statement="Billy Production Engine Phase 5 automates batch voice assembly with 1083 passing tests.",
            )
        ],
    )
    assert res.status == MetricReadinessStatus.READY_FOR_VALUE
    assert res.derivation_allowed


def test_operator_hours_metric_requires_operator_data_when_missing() -> None:
    engine = MetricReadinessEngine()
    res = engine.assess(
        opportunity_id="fp-labs-external-services",
        metric="daniel_hours_first_30_days",
        evidence=[
            MetricEvidenceUnit(
                evidence_id="ev_bench",
                source_type="EXTERNAL_MARKET_BENCHMARK",
                claim_type="BENCHMARK",
                statement="Agency projects typically take 40 hours.",
            )
        ],
    )
    assert res.status == MetricReadinessStatus.REQUIRES_OPERATOR_DATA
    assert not res.derivation_allowed
    assert "operator_bandwidth_commitment" in res.missing_requirements


def test_platform_terms_unlocks_platform_dependency_risk() -> None:
    engine = MetricReadinessEngine()
    res = engine.assess(
        opportunity_id="airbnb-experiences-photography",
        metric="platform_dependency_risk",
        evidence=[
            MetricEvidenceUnit(
                evidence_id="ev_airbnb",
                source_type="PRIMARY_WEB_SOURCE",
                claim_type="PLATFORM_TERMS",
                statement="Airbnb Experiences terms require 20% commission and platform hosting exclusivity.",
            )
        ],
    )
    assert res.status == MetricReadinessStatus.READY_FOR_VALUE
    assert res.derivation_allowed


def test_assessment_is_deterministic_and_idempotent() -> None:
    engine = MetricReadinessEngine()
    ev = [
        MetricEvidenceUnit(
            evidence_id="ev_det",
            source_type="INTERNAL_REPOSITORY",
            claim_type="CAPABILITY",
            statement="Trade Executor has production VPS webhook listener.",
        )
    ]
    res1 = engine.assess("trading-strategy-hardening", "dfg_capability_reuse", ev)
    res2 = engine.assess("trading-strategy-hardening", "dfg_capability_reuse", ev)

    assert res1.model_dump() == res2.model_dump()
