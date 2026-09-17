"""Canonical Portfolio 01 baseline monetization opportunities for Darwin.

Represents 12 bounded DFG monetization paths using existing hardened schemas.
All unmeasured economic inputs remain explicitly None to prevent false precision
and economic data imputation.
"""

from __future__ import annotations

from darwin.monetization.schemas import (
    MonetizationOpportunity,
    MonetizationPortfolioRequest,
    OpportunityEvidenceQuality,
)

PORTFOLIO_01_OBJECTIVE = (
    "Establish canonical Portfolio 01 baseline across DFG monetization paths without economic imputation."
)

PORTFOLIO_01_OPPORTUNITIES: list[MonetizationOpportunity] = [
    MonetizationOpportunity(
        opportunity_id="fp-labs-external-services",
        title="FP Labs External Services",
        thesis="Provide specialized technical consulting, software engineering, and workflow automation services to external clients.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],
        unknowns=[
            "client_acquisition_pipeline_and_conversion",
            "hourly_or_project_billing_rates",
            "capacity_and_delivery_time_commitments",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="commercial-product-photography",
        title="Commercial Product Photography",
        thesis="Deliver commercial studio, e-commerce, and product photography services for brand and merchant clients.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],
        unknowns=[
            "commercial_studio_day_rate_pricing",
            "client_acquisition_channel_conversion",
            "post_production_turnaround_time_and_labor",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="cinema-collection-equipment-rental",
        title="Cinema Collection Equipment Rental",
        thesis="Generate rental income by listing high-end cinema and camera production gear on peer-to-peer and commercial rental networks.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],
        unknowns=[
            "asset_utilization_rate_and_rental_frequency",
            "platform_commission_rates_and_insurance_coverage",
            "equipment_maintenance_and_depreciation_costs",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="production-engine-acceleration",
        title="Production Engine Acceleration",
        thesis="Accelerate creative media production pipelines using automated rendering, asset processing, and batch workflow tools from Billy Production Engine.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],
        unknowns=[
            "pipeline_integration_effort_per_project",
            "rendering_compute_cost_per_job",
            "client_workflow_adoption_hurdles",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="trading-strategy-hardening",
        title="Trading Strategy Hardening",
        thesis="Harden and paper-validate existing EMA trend, RSI mean-reversion, and VWAP strategies from Trading Dashboard via Trade Executor infrastructure before live capital allocation.",
        evidence_quality=OpportunityEvidenceQuality.PRELIMINARY,
        evidence_refs=["docs/runtime/profitability-decision-framework.md"],
        blockers=[],
        unknowns=[
            "forward_paper_validation_expectancy",
            "realistic_fee_spread_and_slippage_drag",
            "max_drawdown_under_regime_shifts",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="fpcriptoclub-monetization",
        title="FPCriptoClub Monetization",
        thesis="Monetize crypto community audience through vetted affiliate programs, VIP subscription channels, and premium educational digital products.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],
        unknowns=[
            "active_community_conversion_to_paid_tiers",
            "affiliate_commission_rates_and_payout_schedules",
            "monthly_churn_rate_for_paid_membership",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="billy-the-trader",
        title="Billy The Trader Character Brand",
        thesis="Build audience and commercial sponsorship/content revenue around the fictional automated trading character Billy The Trader using synthetic media and automated content publishing.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],
        unknowns=[
            "organic_audience_growth_velocity",
            "content_generation_compute_and_labor_cost",
            "sponsorship_and_monetization_rates",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="airbnb-experiences-photography",
        title="Airbnb Experiences Photography",
        thesis="Host guided photography tours and photo-walk experiences booked through the Airbnb Experiences marketplace.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],
        unknowns=[
            "seasonal_booking_demand_and_calendar_utilization",
            "platform_service_fee_deductions",
            "per_session_capacity_and_optimal_ticket_price",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="section-8-real-estate",
        title="Section 8 Residential Real Estate",
        thesis="Acquire, renovate, and operate residential properties subsidized under the Section 8 housing choice voucher program for stable government-backed rental cash flow.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[
            "Upfront capital acquisition and financing required for residential property purchase.",
        ],
        unknowns=[
            "target_market_cap_rates_and_fair_market_rents",
            "lending_terms_downpayment_and_debt_service",
            "local_property_management_overhead",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="prediction-markets-latam",
        title="LATAM Prediction Markets Platform",
        thesis="Develop and operate a prediction market exchange or localized betting platform targeting Latin American event contracts.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[
            "Regulatory and licensing authorization required for prediction market operations in target jurisdictions.",
        ],
        unknowns=[
            "jurisdictional_regulatory_and_licensing_framework",
            "banking_and_fiat_onramp_rails_availability",
            "market_making_and_liquidity_seeding_capital",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="arbitrage-engine",
        title="Systematic Arbitrage Engine",
        thesis="Build and operate systematic cross-venue or statistical arbitrage strategies across digital asset exchanges.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=["docs/runtime/profitability-decision-framework.md"],
        blockers=[
            "Arbitrage implementation blocked until market and liquidity evidence captured (Arbitrage Dependency Gate).",
        ],
        unknowns=[
            "execution_latency_requirements_by_venue",
            "taker_fee_tiers_and_withdrawal_cost_hurdles",
            "cross_venue_capital_efficiency_and_inventory_rebalancing",
        ],
    ),
    MonetizationOpportunity(
        opportunity_id="tiktok-shop-affiliate-creative",
        title="TikTok Shop Affiliate Creative",
        thesis="Generate e-commerce affiliate commissions on TikTok Shop by producing high-volume AI-assisted product creative and showcase videos.",
        evidence_quality=OpportunityEvidenceQuality.HYPOTHESIS,
        evidence_refs=[],
        blockers=[],
        unknowns=[
            "tiktok_shop_account_gating_and_creator_requirements",
            "video_view_to_gmv_conversion_rates",
            "commission_rate_stability_and_merchant_payout_integrity",
        ],
    ),
]


def build_portfolio_01_request() -> MonetizationPortfolioRequest:
    """Build a validated MonetizationPortfolioRequest for Portfolio 01 baseline."""
    return MonetizationPortfolioRequest(
        objective=PORTFOLIO_01_OBJECTIVE,
        opportunities=[opp.model_copy() for opp in PORTFOLIO_01_OPPORTUNITIES],
    )


PORTFOLIO_01_REQUEST: MonetizationPortfolioRequest = build_portfolio_01_request()
