"""Tests for structured operator intake contracts in Darwin monetization."""

from datetime import date

import pytest

from darwin.monetization import (
    CinemaEquipmentItem,
    CinemaInventoryManifest,
    CreatorAccountMetrics,
    EquipmentCategory,
    EquipmentCondition,
    FPCCCommunityMetrics,
    FPLabsHistoricalProject,
    FPLabsOperatorIntake,
    OwnershipStatus,
)


def test_cinema_manifest_optional_serial_and_totals():
    """Verify Cinema inventory manifest allows optional serial numbers and calculates totals."""
    item1 = CinemaEquipmentItem(
        item_category=EquipmentCategory.CAMERA_BODY,
        manufacturer="RED Digital Cinema",
        model="Komodo 6K",
        quantity=1,
        mount="RF",
        condition=EquipmentCondition.EXCELLENT,
        ownership_status=OwnershipStatus.OWNED,
        available_for_rental=True,
        replacement_value_usd=6000.0,
        acquisition_cost_usd=5500.0,
        serial_number=None,  # Strictly optional
        notes="Primary cinema body package with cages.",
    )
    item2 = CinemaEquipmentItem(
        item_category=EquipmentCategory.LENS,
        manufacturer="Canon",
        model="RF 24-70mm f/2.8L IS USM",
        quantity=2,
        mount="RF",
        condition=EquipmentCondition.LIKE_NEW,
        ownership_status=OwnershipStatus.OWNED,
        available_for_rental=True,
        replacement_value_usd=2200.0,
        acquisition_cost_usd=2000.0,
    )

    manifest = CinemaInventoryManifest(
        manifest_id="CINEMA_MANIFEST_20260917",
        operator_name="Daniel",
        submission_date=date(2026, 9, 17),
        items=[item1, item2],
    )

    assert manifest.total_quantity == 3
    assert manifest.total_replacement_value_usd == 10400.0  # 6000 + 2*2200
    assert manifest.total_acquisition_cost_usd == 9500.0   # 5500 + 2*2000

    evidence_units = manifest.to_evidence_units()
    assert len(evidence_units) == 2
    assert any(e.source_type == "OPERATOR" for e in evidence_units)
    assert any("10,400" in e.statement for e in evidence_units)


def test_fp_labs_historical_projects_and_capacity_intake():
    """Verify FP Labs operator intake captures deliverables, hours, and rates without arbitrary desired pricing."""
    proj1 = FPLabsHistoricalProject(
        project_id="PROJ_AUTO_01",
        service_type="Workflow Automation",
        client_industry="Financial Services",
        historical_invoice_usd=5000.0,
        daniel_hours=25.0,
        effective_hourly_rate_usd=200.0,
        external_contractor_costs_usd=0.0,
        repeat_client=True,
        lead_source="Inbound Referral",
    )
    proj2 = FPLabsHistoricalProject(
        project_id="PROJ_AI_02",
        service_type="AI Pipeline Integration",
        client_industry="Media Production",
        historical_invoice_usd=7500.0,
        daniel_hours=30.0,
        effective_hourly_rate_usd=250.0,
        external_contractor_costs_usd=500.0,
        repeat_client=False,
        lead_source="Direct Network",
    )

    form = FPLabsOperatorIntake(
        form_id="FPLABS_INTAKE_01",
        operator_name="Daniel",
        committed_daniel_hours_first_30_days=40.0,
        committed_daniel_hours_first_90_days=120.0,
        historical_projects=[proj1, proj2],
    )

    evidence_units = form.to_evidence_units()
    assert len(evidence_units) == 3  # 30-day hours, 90-day hours, billing rate range
    assert any("40.0 Daniel hours" in e.statement for e in evidence_units)
    assert any("120.0 Daniel hours" in e.statement for e in evidence_units)
    assert any("200 to $250/hr" in e.statement for e in evidence_units)


def test_fpcc_community_metrics_intake():
    """Verify FPCC Telegram channel metrics are parsed into evidence units."""
    metrics = FPCCCommunityMetrics(
        channel_identifier="FPCriptoClub",
        platform="Telegram",
        subscribers_count=4500,
        average_views=1200,
        clicks_per_month=450,
        affiliate_conversions_per_month=25,
        monthly_affiliate_payout_usd=850.0,
        vip_subscribers=80,
        monthly_churn_pct=4.5,
        observation_date=date(2026, 9, 17),
    )

    evidence_units = metrics.to_evidence_units()
    assert len(evidence_units) == 2
    assert any("4,500 registered subscribers" in e.statement for e in evidence_units)
    assert any("850.00" in e.statement for e in evidence_units)


def test_creator_account_metrics_intake():
    """Verify social video creator account metrics are parsed into evidence units."""
    metrics = CreatorAccountMetrics(
        platform="TikTok",
        account_handle="billy_the_trader_ai",
        followers_count=18500,
        views_last_30_days=350000,
        creator_fund_or_affiliate_eligible=True,
        observation_date=date(2026, 9, 17),
    )

    evidence_units = metrics.to_evidence_units(opportunity_id="tiktok-shop-affiliate-creative")
    assert len(evidence_units) == 1
    assert "18,500 followers" in evidence_units[0].statement
    assert "TikTok" in evidence_units[0].statement
