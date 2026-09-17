"""Deterministic research target compression service for Darwin monetization.

Groups fine-grained atomic research targets into structured, high-leverage
research packages while maintaining complete atomic provenance.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from pydantic import BaseModel, Field

# Canonical cluster definitions mapping missing fields to cohesive package categories.
_FIELD_CLUSTERS: dict[str, tuple[str, str, str]] = {
    # field: (category_suffix, category_title, objective_prefix)
    "expected_30_day_net_revenue_usd": (
        "PRICING_AND_REVENUE",
        "Pricing & Revenue Expectations",
        "Determine pricing structures, net margins, and revenue trajectory across 30/90/180 days.",
    ),
    "expected_90_day_net_revenue_usd": (
        "PRICING_AND_REVENUE",
        "Pricing & Revenue Expectations",
        "Determine pricing structures, net margins, and revenue trajectory across 30/90/180 days.",
    ),
    "expected_180_day_net_revenue_usd": (
        "PRICING_AND_REVENUE",
        "Pricing & Revenue Expectations",
        "Determine pricing structures, net margins, and revenue trajectory across 30/90/180 days.",
    ),
    "gross_margin_pct": (
        "PRICING_AND_REVENUE",
        "Pricing & Revenue Expectations",
        "Determine pricing structures, net margins, and revenue trajectory across 30/90/180 days.",
    ),
    "recurring_revenue_pct": (
        "PRICING_AND_REVENUE",
        "Pricing & Revenue Expectations",
        "Determine pricing structures, net margins, and revenue trajectory across 30/90/180 days.",
    ),
    "upfront_capital_usd": (
        "CAPITAL_AND_RISK",
        "Capital Requirements & Risk Exposure",
        "Model upfront capital outlay, equipment acquisition, and loss exposure.",
    ),
    "capital_at_risk_usd": (
        "CAPITAL_AND_RISK",
        "Capital Requirements & Risk Exposure",
        "Model upfront capital outlay, equipment acquisition, and loss exposure.",
    ),
    "time_to_first_dollar_days": (
        "OPERATIONAL_BANDWIDTH",
        "Operational Capacity & Time to Revenue",
        "Establish delivery lead times, first-dollar timeline, and Daniel-hour commitments.",
    ),
    "daniel_hours_first_30_days": (
        "OPERATIONAL_BANDWIDTH",
        "Operational Capacity & Time to Revenue",
        "Establish delivery lead times, first-dollar timeline, and Daniel-hour commitments.",
    ),
    "daniel_hours_first_90_days": (
        "OPERATIONAL_BANDWIDTH",
        "Operational Capacity & Time to Revenue",
        "Establish delivery lead times, first-dollar timeline, and Daniel-hour commitments.",
    ),
    "operational_complexity": (
        "OPERATIONAL_BANDWIDTH",
        "Operational Capacity & Time to Revenue",
        "Establish delivery lead times, first-dollar timeline, and Daniel-hour commitments.",
    ),
    "probability_of_success": (
        "MARKET_AND_GOVERNANCE_RISK",
        "Market Validation & Governance Risk",
        "Verify success probability, customer demand, platform dependency, and regulatory compliance.",
    ),
    "legal_compliance_risk": (
        "MARKET_AND_GOVERNANCE_RISK",
        "Market Validation & Governance Risk",
        "Verify success probability, customer demand, platform dependency, and regulatory compliance.",
    ),
    "platform_dependency_risk": (
        "MARKET_AND_GOVERNANCE_RISK",
        "Market Validation & Governance Risk",
        "Verify success probability, customer demand, platform dependency, and regulatory compliance.",
    ),
    "automation_potential": (
        "CAPABILITY_LEVERAGE",
        "DFG Capability Leverage & Automation",
        "Quantify software automation throughput and direct reuse of existing DFG technical systems.",
    ),
    "dfg_capability_reuse": (
        "CAPABILITY_LEVERAGE",
        "DFG Capability Leverage & Automation",
        "Quantify software automation throughput and direct reuse of existing DFG technical systems.",
    ),
    "explicit_evidence_refs": (
        "EVIDENCE_PROVENANCE",
        "Baseline Evidence Provenance",
        "Gather canonical documentation references, past client records, and verified operational data.",
    ),
    "stronger_market_or_operating_evidence": (
        "EVIDENCE_PROVENANCE",
        "Baseline Evidence Provenance",
        "Gather canonical documentation references, past client records, and verified operational data.",
    ),
}


class ResearchPackage(BaseModel):
    """A cohesive research work package clustering related atomic missing dimensions."""

    package_id: str
    opportunity_id: str
    cluster_name: str
    title: str
    objective: str
    target_fields: list[str] = Field(default_factory=list)


class TargetCompressionResult(BaseModel):
    """Structured result of compressing atomic targets into manageable research packages."""

    total_atomic_targets: int
    total_packages: int
    compression_ratio: float
    packages: list[ResearchPackage]
    packages_by_opportunity: dict[str, list[ResearchPackage]]


class ResearchTargetGrouper:
    """Service to compress atomic monetization targets into actionable research packages."""

    def compress(self, targets: Sequence[str]) -> TargetCompressionResult:
        """Deterministically group raw '{opportunity_id}:{missing_field}' targets into packages."""
        if not targets:
            return TargetCompressionResult(
                total_atomic_targets=0,
                total_packages=0,
                compression_ratio=1.0,
                packages=[],
                packages_by_opportunity={},
            )

        # Map opportunity -> cluster_suffix -> list of fields
        opp_clusters: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

        for raw_target in targets:
            if ":" not in raw_target:
                continue
            opp_id, field_name = raw_target.split(":", 1)
            cluster_meta = _FIELD_CLUSTERS.get(
                field_name,
                ("GENERAL_EVIDENCE", "General Evidence", f"Resolve missing evidence for {field_name}."),
            )
            cluster_suffix = cluster_meta[0]
            opp_clusters[opp_id][cluster_suffix].append(field_name)

        packages: list[ResearchPackage] = []
        packages_by_opp: dict[str, list[ResearchPackage]] = defaultdict(list)

        # Build packages deterministically sorted by opportunity_id then cluster_suffix
        for opp_id in sorted(opp_clusters.keys()):
            for cluster_suffix in sorted(opp_clusters[opp_id].keys()):
                fields = sorted(set(opp_clusters[opp_id][cluster_suffix]))
                # Derive title and objective from the first field in cluster
                sample_field = fields[0]
                cluster_meta = _FIELD_CLUSTERS.get(
                    sample_field,
                    ("GENERAL_EVIDENCE", "General Evidence", f"Resolve missing evidence for {sample_field}."),
                )
                _, title, objective = cluster_meta
                pkg_id = f"{opp_id.upper().replace('-', '_')}_{cluster_suffix}"

                pkg = ResearchPackage(
                    package_id=pkg_id,
                    opportunity_id=opp_id,
                    cluster_name=cluster_suffix,
                    title=f"{opp_id}: {title}",
                    objective=f"{objective} (Covers: {', '.join(fields)})",
                    target_fields=fields,
                )
                packages.append(pkg)
                packages_by_opp[opp_id].append(pkg)

        total_atomic = len(targets)
        total_pkgs = len(packages)
        ratio = round(total_atomic / total_pkgs, 2) if total_pkgs > 0 else 1.0

        return TargetCompressionResult(
            total_atomic_targets=total_atomic,
            total_packages=total_pkgs,
            compression_ratio=ratio,
            packages=packages,
            packages_by_opportunity=dict(packages_by_opp),
        )
