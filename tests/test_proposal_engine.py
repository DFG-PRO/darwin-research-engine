"""Tests for PortfolioProposalEngine generating bounded proposals without canonical mutation."""

import pytest

from darwin.monetization import (
    MetricEvidenceUnit,
    MetricReadinessEngine,
    MetricReadinessStatus,
    MonetizationOpportunity,
    OpportunityEvidenceQuality,
    PortfolioMetricProposal,
    PortfolioProposalBatch,
    PortfolioProposalEngine,
    ProposalAction,
)


@pytest.fixture
def proposal_engine() -> PortfolioProposalEngine:
    return PortfolioProposalEngine()


@pytest.fixture
def sample_opportunity() -> MonetizationOpportunity:
    return MonetizationOpportunity(
        opportunity_id="cinema-collection-equipment-rental",
        title="Cinema Collection Equipment Rental",
        thesis="Generate rental income by listing high-end cinema equipment.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],
        unknowns=["asset_utilization_rate_and_rental_frequency"],
    )


def test_market_price_alone_proposes_keep_none_expected_revenue(
    proposal_engine: PortfolioProposalEngine,
    sample_opportunity: MonetizationOpportunity,
):
    """Verify that market pricing evidence alone proposes KEEP_NONE for expected revenue."""
    ev = [
        MetricEvidenceUnit(
            evidence_id="EV_PRICE_01",
            source_type="EXTERNAL_MARKET_BENCHMARK",
            claim_type="BENCHMARK",
            statement="ShareGrid median rental day rate for cinema packages is $250/day.",
            confidence=0.70,
        )
    ]

    proposal = proposal_engine.evaluate_metric(
        opportunity=sample_opportunity,
        metric="expected_30_day_net_revenue_usd",
        evidence=ev,
    )

    assert proposal.action == ProposalAction.KEEP_NONE
    assert proposal.proposed_value is None
    assert proposal.proposed_range is None
    assert proposal.readiness_status == MetricReadinessStatus.REQUIRES_EMPIRICAL_TEST
    assert "REQUIRES_EMPIRICAL_TEST" in (proposal.derivation or "")


def test_technical_capability_alone_proposes_keep_none(
    proposal_engine: PortfolioProposalEngine,
    sample_opportunity: MonetizationOpportunity,
):
    """Verify that technical capability alone proposes KEEP_NONE for commercial revenue."""
    ev = [
        MetricEvidenceUnit(
            evidence_id="EV_TECH_01",
            source_type="INTERNAL_REPOSITORY",
            claim_type="CAPABILITY",
            statement="Billy Production Engine can render 200 clips per hour.",
            confidence=0.95,
        )
    ]

    proposal = proposal_engine.evaluate_metric(
        opportunity=sample_opportunity,
        metric="expected_30_day_net_revenue_usd",
        evidence=ev,
    )

    assert proposal.action == ProposalAction.KEEP_NONE
    assert proposal.proposed_value is None
    assert proposal.proposed_range is None
    assert proposal.readiness_status == MetricReadinessStatus.INSUFFICIENT_EVIDENCE


def test_platform_fee_evidence_proposes_margin_range(
    proposal_engine: PortfolioProposalEngine,
    sample_opportunity: MonetizationOpportunity,
):
    """Verify that platform fee evidence proposes gross margin range if matching schema semantics."""
    ev = [
        MetricEvidenceUnit(
            evidence_id="EV_FEE_01",
            source_type="PRIMARY_WEB_SOURCE",
            claim_type="PLATFORM_TERMS",
            statement="ShareGrid charges 15% platform commission on equipment rentals.",
            confidence=0.85,
        )
    ]

    proposal = proposal_engine.evaluate_metric(
        opportunity=sample_opportunity,
        metric="gross_margin_pct",
        evidence=ev,
    )

    assert proposal.action == ProposalAction.PROPOSE_RANGE
    assert proposal.proposed_range is not None
    assert proposal.proposed_range.low == 80.0
    assert proposal.proposed_range.high == 85.0
    assert "15%" in (proposal.derivation or "")


def test_empirical_conversion_pricing_costs_proposes_revenue_range(
    proposal_engine: PortfolioProposalEngine,
    sample_opportunity: MonetizationOpportunity,
):
    """Verify that pricing + empirical conversion + cost evidence proposes candidate revenue range."""
    ev = [
        MetricEvidenceUnit(
            evidence_id="EV_PRICE_01",
            source_type="PRIMARY_WEB_SOURCE",
            claim_type="BENCHMARK",
            statement="ShareGrid median rental day rate is $250/day.",
            confidence=0.85,
        ),
        MetricEvidenceUnit(
            evidence_id="EV_CONV_01",
            source_type="EMPIRICAL_TEST",
            claim_type="EMPIRICAL_MEASUREMENT",
            statement="Empirical rental pilot achieved 8 rental days in 30 days.",
            confidence=0.90,
        ),
        MetricEvidenceUnit(
            evidence_id="EV_FEE_01",
            source_type="PRIMARY_WEB_SOURCE",
            claim_type="PLATFORM_TERMS",
            statement="Platform takes 15% fee.",
            confidence=0.85,
        ),
    ]

    proposal = proposal_engine.evaluate_metric(
        opportunity=sample_opportunity,
        metric="expected_30_day_net_revenue_usd",
        evidence=ev,
    )

    assert proposal.action == ProposalAction.PROPOSE_RANGE
    assert proposal.proposed_range is not None
    assert proposal.proposed_range.low == 1000.0
    assert proposal.proposed_range.high == 2500.0
    assert "Derived expected_30_day_net_revenue_usd range" in (proposal.derivation or "")
    assert proposal.requires_human_review is True


def test_missing_evidence_proposes_keep_none(
    proposal_engine: PortfolioProposalEngine,
    sample_opportunity: MonetizationOpportunity,
):
    """Verify that absent evidence proposes KEEP_NONE."""
    proposal = proposal_engine.evaluate_metric(
        opportunity=sample_opportunity,
        metric="upfront_capital_usd",
        evidence=[],
    )

    assert proposal.action == ProposalAction.KEEP_NONE
    assert proposal.proposed_value is None
    assert proposal.readiness_status == MetricReadinessStatus.INSUFFICIENT_EVIDENCE
    assert "No verified empirical evidence" in (proposal.derivation or "")


def test_conflicting_evidence_flags_conflict_no_silent_selection(
    proposal_engine: PortfolioProposalEngine,
    sample_opportunity: MonetizationOpportunity,
):
    """Verify that conflicting evidence raises FLAG_CONFLICT without silently choosing a side."""
    ev = [
        MetricEvidenceUnit(
            evidence_id="EV_LEGAL_01",
            source_type="PRIMARY_WEB_SOURCE",
            claim_type="REGULATORY_FILING",
            statement="Event contracts are fully compliant and authorized under national law.",
            confidence=0.80,
        ),
        MetricEvidenceUnit(
            evidence_id="EV_LEGAL_02",
            source_type="PRIMARY_WEB_SOURCE",
            claim_type="REGULATORY_FILING",
            statement="Event contracts are prohibited and illegal under state regulations.",
            confidence=0.80,
        ),
    ]

    proposal = proposal_engine.evaluate_metric(
        opportunity=sample_opportunity,
        metric="legal_compliance_risk",
        evidence=ev,
    )

    assert proposal.action == ProposalAction.FLAG_CONFLICT
    assert proposal.proposed_value is None
    assert "Contradictory" in (proposal.derivation or "")
    assert proposal.requires_human_review is True


def test_jurisdiction_mismatch_proposes_keep_none(
    proposal_engine: PortfolioProposalEngine,
):
    """Verify that mismatched jurisdiction evidence fails closed with KEEP_NONE."""
    opp = MonetizationOpportunity(
        opportunity_id="section-8-real-estate",
        title="Section 8 Residential Real Estate",
        thesis="Acquire subsidized rental properties.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],  # Unblocked for test of jurisdiction gate
        unknowns=[],
    )

    ev = [
        MetricEvidenceUnit(
            evidence_id="EV_UK_RENT_01",
            source_type="PRIMARY_WEB_SOURCE",
            claim_type="BENCHMARK",
            statement="UK council housing average fair rent is £800/month.",
            jurisdiction="UK",  # Mismatched jurisdiction (expected US)
            confidence=0.85,
        )
    ]

    proposal = proposal_engine.evaluate_metric(
        opportunity=opp,
        metric="expected_30_day_net_revenue_usd",
        evidence=ev,
    )

    assert proposal.action == ProposalAction.KEEP_NONE
    assert "jurisdiction" in (proposal.derivation or "").lower()


def test_opportunity_remains_unmutated(
    proposal_engine: PortfolioProposalEngine,
    sample_opportunity: MonetizationOpportunity,
):
    """Verify that evaluating proposals never mutates the original opportunity object."""
    assert sample_opportunity.expected_30_day_net_revenue_usd is None

    batch = proposal_engine.evaluate_opportunity(
        opportunity=sample_opportunity,
        evidence_by_metric={},
    )

    assert isinstance(batch, PortfolioProposalBatch)
    assert batch.total_proposals == 9
    assert batch.retained_none_count == 9
    assert batch.proposed_mutations_count == 0

    # Ensure canonical opportunity fields are untouched
    assert sample_opportunity.expected_30_day_net_revenue_usd is None
    assert sample_opportunity.gross_margin_pct is None
    assert sample_opportunity.upfront_capital_usd is None
