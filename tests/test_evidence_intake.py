"""Tests for EvidenceIntakeAdapter and EvidenceIntakePayload."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from darwin.db.models import ClaimStatus, ClaimType, EvidenceType
from darwin.monetization import (
    EpistemicClass,
    EvidenceIntakeAdapter,
    EvidenceIntakePayload,
    IntakeClaimType,
    IntakeSourceType,
)
from darwin.research.schemas import ClaimRead, EvidenceRead


def test_intake_across_all_five_source_types():
    """Verify evidence ingestion across all five canonical source types."""
    adapter = EvidenceIntakeAdapter()
    now = datetime.now(timezone.utc)

    sources = [
        (IntakeSourceType.INTERNAL_REPOSITORY, "docs/trading-backtest.log", IntakeClaimType.CAPABILITY, 0.95),
        (IntakeSourceType.OPERATOR, "operator:daniel_timesheet", IntakeClaimType.OPERATOR_INTAKE, 0.80),
        (IntakeSourceType.PRIMARY_WEB_SOURCE, "https://sharegrid.com/pricing", IntakeClaimType.PLATFORM_TERMS, 0.85),
        (IntakeSourceType.EMPIRICAL_TEST, "run:paper_trade_20260917", IntakeClaimType.EMPIRICAL_MEASUREMENT, 0.90),
        (IntakeSourceType.EXTERNAL_MARKET_BENCHMARK, "report:gartner_consulting_rates_2026", IntakeClaimType.BENCHMARK, 0.65),
    ]

    for src_type, src_id, expected_claim_type, expected_conf in sources:
        payload = EvidenceIntakePayload(
            opportunity_id="test-opportunity",
            target_metric="expected_30_day_net_revenue_usd",
            source_type=src_type,
            source_identifier=src_id,
            statement=f"Evidence statement from {src_type.value}",
            observation_time=now,
        )
        assert payload.content_fingerprint.startswith("sha256:")
        unit = adapter.ingest(payload)
        assert unit.source_type == src_type.value
        assert unit.claim_type == expected_claim_type.value
        assert unit.confidence == expected_conf
        assert unit.evidence_id.startswith("EV_")


def test_deterministic_identity_and_fingerprinting():
    """Verify identical inputs yield identical unit IDs and content fingerprints."""
    adapter = EvidenceIntakeAdapter()
    fixed_time = datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)

    payload1 = EvidenceIntakePayload(
        opportunity_id="cinema-collection-equipment-rental",
        target_metric="upfront_capital_usd",
        source_type=IntakeSourceType.OPERATOR,
        source_identifier="manifest:camera_gear_v1",
        statement="Total acquisition cost of cinema package is $25,000.",
        observation_time=fixed_time,
        numeric_value=25000.0,
    )
    payload2 = EvidenceIntakePayload(
        opportunity_id="cinema-collection-equipment-rental",
        target_metric="upfront_capital_usd",
        source_type=IntakeSourceType.OPERATOR,
        source_identifier="manifest:camera_gear_v1",
        statement="Total acquisition cost of cinema package is $25,000.",
        observation_time=fixed_time,
        numeric_value=25000.0,
    )

    assert payload1.content_fingerprint == payload2.content_fingerprint

    unit1 = adapter.ingest(payload1)
    unit2 = adapter.ingest(payload2)

    assert unit1.evidence_id == unit2.evidence_id


def test_external_market_benchmark_cannot_silently_become_fact():
    """Verify that external market benchmarks reject FACT classification."""
    with pytest.raises(ValueError, match="EXTERNAL_MARKET_BENCHMARK cannot be classified as FACT"):
        EvidenceIntakePayload(
            opportunity_id="fp-labs-external-services",
            target_metric="expected_30_day_net_revenue_usd",
            source_type=IntakeSourceType.EXTERNAL_MARKET_BENCHMARK,
            source_identifier="survey:consulting_rates_2026",
            statement="Average consulting rate is $200/hr.",
            epistemic_class=EpistemicClass.FACT,  # Must fail closed
        )


def test_missing_source_fails_closed():
    """Verify that empty source_identifier or statement fails closed with validation error."""
    with pytest.raises(ValueError, match="Field cannot be empty"):
        EvidenceIntakePayload(
            opportunity_id="test-opp",
            target_metric="upfront_capital_usd",
            source_type=IntakeSourceType.OPERATOR,
            source_identifier="",
            statement="Valid statement",
        )

    with pytest.raises(ValueError, match="Field cannot be empty"):
        EvidenceIntakePayload(
            opportunity_id="test-opp",
            target_metric="upfront_capital_usd",
            source_type=IntakeSourceType.OPERATOR,
            source_identifier="valid-source",
            statement="   ",
        )


def test_invalid_range_and_negative_metrics_fail():
    """Verify inverted ranges and negative numbers on non-negative metrics fail validation."""
    with pytest.raises(ValueError, match="range_min .* cannot be greater than range_max"):
        EvidenceIntakePayload(
            opportunity_id="test-opp",
            target_metric="expected_30_day_net_revenue_usd",
            source_type=IntakeSourceType.PRIMARY_WEB_SOURCE,
            source_identifier="https://example.com",
            statement="Range test",
            range_min=5000.0,
            range_max=2000.0,
        )

    with pytest.raises(ValueError, match="cannot have negative numeric_value"):
        EvidenceIntakePayload(
            opportunity_id="test-opp",
            target_metric="daniel_hours_first_30_days",
            source_type=IntakeSourceType.OPERATOR,
            source_identifier="operator:timesheet",
            statement="Daniel hours cannot be negative",
            numeric_value=-15.0,
        )


def test_from_evidence_and_claim_canonical_conversion():
    """Verify canonical Darwin EvidenceRead + ClaimRead can be adapted to MetricEvidenceUnit."""
    adapter = EvidenceIntakeAdapter()
    run_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    src_id = uuid.uuid4()
    cl_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    ev = EvidenceRead(
        id=ev_id,
        research_run_id=run_id,
        source_id=src_id,
        evidence_type=EvidenceType.MEASUREMENT,
        statement="ShareGrid average daily rental fee for RED Komodo is $185/day.",
        source_locator="https://sharegrid.com/los-angeles/rent/red-komodo",
        captured_at=now,
        evidence_metadata={},
    )
    cl = ClaimRead(
        id=cl_id,
        research_run_id=run_id,
        statement="RED Komodo day rate ranges from $150 to $220/day.",
        claim_type=ClaimType.FINDING,
        status=ClaimStatus.PROPOSED,
        confidence=Decimal("0.85"),
        created_at=now,
        updated_at=now,
    )

    unit = adapter.from_evidence_and_claim(
        evidence=ev,
        claim=cl,
        opportunity_id="cinema-collection-equipment-rental",
        target_metric="expected_30_day_net_revenue_usd",
        source_type=IntakeSourceType.PRIMARY_WEB_SOURCE,
        jurisdiction="US",
        confidence=0.85,
    )

    assert unit.source_type == IntakeSourceType.PRIMARY_WEB_SOURCE.value
    assert unit.statement == cl.statement
    assert unit.confidence == 0.85
    assert unit.jurisdiction == "US"
    assert unit.evidence_id.startswith("EV_")
