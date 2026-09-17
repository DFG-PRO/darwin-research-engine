"""Structured operator input contracts for Darwin monetization.

Provides reusable, validated schemas for operator intake: Cinema equipment inventory,
FP Labs historical projects, FPCC community channels, and Creator accounts.
Enforces epistemic boundaries (e.g. historical evidence vs desired pricing) and ensures
equipment serial numbers remain optional for economic evaluation.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from darwin.monetization.intake import (
    EvidenceIntakeAdapter,
    EvidenceIntakePayload,
    IntakeClaimType,
    IntakeSourceType,
)
from darwin.monetization.readiness import MetricEvidenceUnit


class EquipmentCategory(str, Enum):
    """Broad category for cinema production gear."""

    CAMERA_BODY = "CAMERA_BODY"
    LENS = "LENS"
    LIGHTING = "LIGHTING"
    AUDIO = "AUDIO"
    GRIP_AND_SUPPORT = "GRIP_AND_SUPPORT"
    MONITOR_AND_WIRELESS = "MONITOR_AND_WIRELESS"
    POWER_AND_ACCESSORIES = "POWER_AND_ACCESSORIES"
    OTHER = "OTHER"


class EquipmentCondition(str, Enum):
    """Working condition of equipment asset."""

    NEW = "NEW"
    LIKE_NEW = "LIKE_NEW"
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"


class OwnershipStatus(str, Enum):
    """Legal ownership relationship."""

    OWNED = "OWNED"
    LEASED = "LEASED"
    RENTED = "RENTED"


class CinemaEquipmentItem(BaseModel):
    """One individual gear item in the Cinema Collection inventory."""

    model_config = ConfigDict(str_strip_whitespace=True)

    item_category: EquipmentCategory
    manufacturer: str = Field(min_length=1)
    model: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=1)
    mount: str | None = None
    condition: EquipmentCondition = EquipmentCondition.EXCELLENT
    ownership_status: OwnershipStatus = OwnershipStatus.OWNED
    available_for_rental: bool = True
    replacement_value_usd: float | None = Field(default=None, ge=0.0)
    acquisition_cost_usd: float | None = Field(default=None, ge=0.0)
    serial_number: str | None = None  # Strictly optional for economic modeling
    notes: str | None = None


class CinemaInventoryManifest(BaseModel):
    """Complete equipment inventory manifest submitted by operator."""

    model_config = ConfigDict(str_strip_whitespace=True)

    manifest_id: str
    operator_name: str = "Daniel"
    submission_date: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())
    items: list[CinemaEquipmentItem] = Field(default_factory=list)
    storage_location: str | None = None
    notes: str | None = None

    @property
    def total_quantity(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def total_replacement_value_usd(self) -> float | None:
        vals = [item.replacement_value_usd * item.quantity for item in self.items if item.replacement_value_usd is not None]
        return round(sum(vals), 2) if vals else None

    @property
    def total_acquisition_cost_usd(self) -> float | None:
        vals = [item.acquisition_cost_usd * item.quantity for item in self.items if item.acquisition_cost_usd is not None]
        return round(sum(vals), 2) if vals else None

    def to_evidence_units(self, adapter: EvidenceIntakeAdapter | None = None) -> list[MetricEvidenceUnit]:
        """Convert inventory manifest into canonical MetricEvidenceUnits."""
        ad = adapter or EvidenceIntakeAdapter()
        units: list[MetricEvidenceUnit] = []
        opp_id = "cinema-collection-equipment-rental"

        # Evidence for upfront capital / equipment asset value
        if self.total_replacement_value_usd is not None:
            p = EvidenceIntakePayload(
                opportunity_id=opp_id,
                target_metric="upfront_capital_usd",
                source_type=IntakeSourceType.OPERATOR,
                source_identifier=f"manifest:{self.manifest_id}",
                statement=f"Verified equipment replacement value totaling ${self.total_replacement_value_usd:,.2f} across {self.total_quantity} items.",
                claim_type=IntakeClaimType.OPERATOR_INTAKE,
                numeric_value=self.total_replacement_value_usd,
                confidence=0.90,
            )
            units.append(ad.ingest(p))

        # Evidence for rental availability provenance
        rental_ready_count = sum(item.quantity for item in self.items if item.available_for_rental)
        p_prov = EvidenceIntakePayload(
            opportunity_id=opp_id,
            target_metric="explicit_evidence_refs",
            source_type=IntakeSourceType.OPERATOR,
            source_identifier=f"manifest:{self.manifest_id}",
            statement=f"Operator manifest confirms {rental_ready_count} units available for immediate rental listing.",
            claim_type=IntakeClaimType.OPERATOR_INTAKE,
            confidence=0.90,
        )
        units.append(ad.ingest(p_prov))

        return units


class FPLabsHistoricalProject(BaseModel):
    """Historical project record delivered by FP Labs."""

    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: str = Field(min_length=1)
    service_type: str = Field(min_length=1)
    client_industry: str | None = None
    historical_invoice_usd: float | None = Field(default=None, ge=0.0)
    daniel_hours: float | None = Field(default=None, ge=0.0)
    effective_hourly_rate_usd: float | None = Field(default=None, ge=0.0)
    external_contractor_costs_usd: float = Field(default=0.0, ge=0.0)
    repeat_client: bool = False
    lead_source: str | None = None
    completion_date: date | None = None
    notes: str | None = None


class FPLabsOperatorIntake(BaseModel):
    """FP Labs operator capacity and historical track record intake."""

    model_config = ConfigDict(str_strip_whitespace=True)

    form_id: str
    operator_name: str = "Daniel"
    submission_date: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())
    committed_daniel_hours_first_30_days: float | None = Field(default=None, ge=0.0)
    committed_daniel_hours_first_90_days: float | None = Field(default=None, ge=0.0)
    historical_projects: list[FPLabsHistoricalProject] = Field(default_factory=list)

    def to_evidence_units(self, adapter: EvidenceIntakeAdapter | None = None) -> list[MetricEvidenceUnit]:
        """Convert FP Labs operator inputs into canonical MetricEvidenceUnits."""
        ad = adapter or EvidenceIntakeAdapter()
        units: list[MetricEvidenceUnit] = []
        opp_id = "fp-labs-external-services"

        # Hours commitments
        if self.committed_daniel_hours_first_30_days is not None:
            p = EvidenceIntakePayload(
                opportunity_id=opp_id,
                target_metric="daniel_hours_first_30_days",
                source_type=IntakeSourceType.OPERATOR,
                source_identifier=f"form:{self.form_id}",
                statement=f"Operator committed {self.committed_daniel_hours_first_30_days:.1f} Daniel hours for the first 30 days.",
                claim_type=IntakeClaimType.OPERATOR_INTAKE,
                numeric_value=self.committed_daniel_hours_first_30_days,
                confidence=0.90,
            )
            units.append(ad.ingest(p))

        if self.committed_daniel_hours_first_90_days is not None:
            p = EvidenceIntakePayload(
                opportunity_id=opp_id,
                target_metric="daniel_hours_first_90_days",
                source_type=IntakeSourceType.OPERATOR,
                source_identifier=f"form:{self.form_id}",
                statement=f"Operator committed {self.committed_daniel_hours_first_90_days:.1f} Daniel hours for the first 90 days.",
                claim_type=IntakeClaimType.OPERATOR_INTAKE,
                numeric_value=self.committed_daniel_hours_first_90_days,
                confidence=0.90,
            )
            units.append(ad.ingest(p))

        # Historical billings
        rates = [p.effective_hourly_rate_usd for p in self.historical_projects if p.effective_hourly_rate_usd is not None]
        if rates:
            min_r = min(rates)
            max_r = max(rates)
            p_rate = EvidenceIntakePayload(
                opportunity_id=opp_id,
                target_metric="expected_30_day_net_revenue_usd",
                source_type=IntakeSourceType.OPERATOR,
                source_identifier=f"form:{self.form_id}",
                statement=f"Historical client billing rates range from ${min_r:,.0f} to ${max_r:,.0f}/hr across {len(rates)} delivered projects.",
                claim_type=IntakeClaimType.OPERATOR_INTAKE,
                range_min=min_r,
                range_max=max_r,
                confidence=0.85,
            )
            units.append(ad.ingest(p_rate))

        return units


class FPCCCommunityMetrics(BaseModel):
    """Community metrics for FPCriptoClub channel."""

    model_config = ConfigDict(str_strip_whitespace=True)

    channel_identifier: str = "FPCriptoClub"
    platform: str = "Telegram"
    subscribers_count: int = Field(ge=0)
    average_views: int | None = Field(default=None, ge=0)
    clicks_per_month: int | None = Field(default=None, ge=0)
    affiliate_conversions_per_month: int | None = Field(default=None, ge=0)
    monthly_affiliate_payout_usd: float | None = Field(default=None, ge=0.0)
    vip_subscribers: int | None = Field(default=None, ge=0)
    monthly_churn_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    observation_date: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())

    def to_evidence_units(self, adapter: EvidenceIntakeAdapter | None = None) -> list[MetricEvidenceUnit]:
        """Convert community metrics into MetricEvidenceUnits."""
        ad = adapter or EvidenceIntakeAdapter()
        units: list[MetricEvidenceUnit] = []
        opp_id = "fpcriptoclub-monetization"

        p_sub = EvidenceIntakePayload(
            opportunity_id=opp_id,
            target_metric="explicit_evidence_refs",
            source_type=IntakeSourceType.OPERATOR,
            source_identifier=f"channel:{self.channel_identifier}:{self.platform}",
            statement=f"{self.platform} channel has {self.subscribers_count:,} registered subscribers as of {self.observation_date}.",
            claim_type=IntakeClaimType.OPERATOR_INTAKE,
            confidence=0.90,
        )
        units.append(ad.ingest(p_sub))

        if self.monthly_affiliate_payout_usd is not None:
            p_payout = EvidenceIntakePayload(
                opportunity_id=opp_id,
                target_metric="expected_30_day_net_revenue_usd",
                source_type=IntakeSourceType.OPERATOR,
                source_identifier=f"channel:{self.channel_identifier}:payout",
                statement=f"Historical monthly affiliate payout recorded at ${self.monthly_affiliate_payout_usd:,.2f}.",
                claim_type=IntakeClaimType.OPERATOR_INTAKE,
                numeric_value=self.monthly_affiliate_payout_usd,
                confidence=0.85,
            )
            units.append(ad.ingest(p_payout))

        return units


class CreatorAccountMetrics(BaseModel):
    """Creator account metrics for TikTok / social video channels."""

    model_config = ConfigDict(str_strip_whitespace=True)

    platform: str = Field(min_length=1)
    account_handle: str = Field(min_length=1)
    followers_count: int = Field(ge=0)
    views_last_30_days: int | None = Field(default=None, ge=0)
    creator_fund_or_affiliate_eligible: bool = False
    observation_date: date = Field(default_factory=lambda: datetime.now(timezone.utc).date())
    notes: str | None = None

    def to_evidence_units(self, opportunity_id: str, adapter: EvidenceIntakeAdapter | None = None) -> list[MetricEvidenceUnit]:
        """Convert creator metrics into MetricEvidenceUnits."""
        ad = adapter or EvidenceIntakeAdapter()
        p = EvidenceIntakePayload(
            opportunity_id=opportunity_id,
            target_metric="explicit_evidence_refs",
            source_type=IntakeSourceType.OPERATOR,
            source_identifier=f"account:{self.platform}:{self.account_handle}",
            statement=(
                f"{self.platform} account @{self.account_handle} has {self.followers_count:,} followers "
                f"and eligibility status: {self.creator_fund_or_affiliate_eligible} as of {self.observation_date}."
            ),
            claim_type=IntakeClaimType.OPERATOR_INTAKE,
            confidence=0.90,
        )
        return [ad.ingest(p)]
