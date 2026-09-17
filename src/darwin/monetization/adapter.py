"""Adapter connecting compressed research packages to Darwin research execution.

Converts fine-grained research packages into structured, actionable research objectives
while preserving 100% provenance back to atomic targets and opportunity IDs.
Ensures operator evidence requirements are emitted explicitly rather than attempting
invalid web substitution.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field

from darwin.db.models import ResearchLoopExecutionMode, SourceType
from darwin.monetization.grouper import ResearchPackage
from darwin.monetization.schemas import MonetizationOpportunity
from darwin.research_loop.schemas import ResearchLoopBudgets, ResearchLoopRequest


class PackageObjectiveType(str, Enum):
    """Categorizes the primary execution mechanism for a research objective."""

    OPERATOR_INTAKE = "OPERATOR_INTAKE"
    INTERNAL_AUDIT = "INTERNAL_AUDIT"
    WEB_RESEARCH = "WEB_RESEARCH"
    EMPIRICAL_VALIDATION = "EMPIRICAL_VALIDATION"


class ResearchPackageObjective(BaseModel):
    """Actionable research objective derived from a compressed ResearchPackage."""

    model_config = ConfigDict(str_strip_whitespace=True)

    objective_id: str
    package_id: str
    opportunity_id: str
    cluster_name: str
    atomic_target_ids: list[str] = Field(default_factory=list)
    target_fields: list[str] = Field(default_factory=list)
    objective_type: PackageObjectiveType
    title: str
    research_question: str
    detailed_scope: str
    desired_source_types: list[SourceType] = Field(default_factory=list)
    jurisdiction: str | None = None
    freshness_days: int = 90
    requires_operator_input: bool = False
    operator_instructions: str | None = None
    is_blocked: bool = False
    blocker_reason: str | None = None
    search_queries: list[str] = Field(default_factory=list)

    def can_execute_via_web_loop(self) -> bool:
        """Indicate whether this objective can be executed via Darwin's web research loop."""
        if self.requires_operator_input:
            return False
        if self.is_blocked:
            return False
        if self.objective_type != PackageObjectiveType.WEB_RESEARCH:
            return False
        return True

    def to_research_loop_request(
        self,
        budgets: ResearchLoopBudgets | None = None,
        planning_provider: str = "fake",
        acquisition_provider: str = "fake",
        execution_mode: ResearchLoopExecutionMode = ResearchLoopExecutionMode.AUTO_GROUNDED,
    ) -> ResearchLoopRequest:
        """Convert to a canonical Darwin ResearchLoopRequest.

        Raises ValueError if the objective requires operator input (no web substitution),
        is blocked, or is not web-executable.
        """
        if self.requires_operator_input:
            raise ValueError(
                f"Objective '{self.objective_id}' requires operator evidence and cannot "
                f"be executed via web research loop without invalid evidence substitution."
            )
        if self.is_blocked:
            raise ValueError(
                f"Objective '{self.objective_id}' is blocked: {self.blocker_reason}"
            )
        if not self.can_execute_via_web_loop():
            raise ValueError(
                f"Objective '{self.objective_id}' with type {self.objective_type.value} cannot "
                f"be executed via web research loop."
            )

        metadata: dict[str, Any] = {
            "objective_id": self.objective_id,
            "package_id": self.package_id,
            "opportunity_id": self.opportunity_id,
            "cluster_name": self.cluster_name,
            "atomic_target_ids": list(self.atomic_target_ids),
            "target_fields": list(self.target_fields),
            "jurisdiction": self.jurisdiction,
            "search_queries": list(self.search_queries),
        }

        source_types = self.desired_source_types or [SourceType.WEB_PAGE]

        return ResearchLoopRequest(
            research_question=self.research_question,
            objective=self.detailed_scope,
            scope=f"Monetization opportunity: {self.opportunity_id}",
            desired_source_types=source_types,
            planning_provider=planning_provider,
            acquisition_provider=acquisition_provider,
            execution_mode=execution_mode,
            budgets=budgets or ResearchLoopBudgets(max_iterations=1, max_searches=2, max_sources=3),
            publish_report=False,
            metadata=metadata,
        )


# Mapping of opportunity IDs to default search queries for PRICING_AND_REVENUE
_OPPORTUNITY_SEARCH_QUERIES: dict[str, list[str]] = {
    "cinema-collection-equipment-rental": [
        "cinema camera gear rental daily rates sharegrid",
        "peer to peer camera rental fee commission kit split",
    ],
    "commercial-product-photography": [
        "commercial product photography day rates studio",
        "product catalog photography pricing benchmarks",
    ],
    "airbnb-experiences-photography": [
        "airbnb experiences host commission service fee",
        "guided photo tour ticket pricing airbnb experiences",
    ],
    "tiktok-shop-affiliate-creative": [
        "tiktok shop affiliate commission rates by category",
        "tiktok shop creator payout terms requirements",
    ],
    "fpcriptoclub-monetization": [
        "crypto trading telegram vip channel subscription pricing",
        "crypto exchange affiliate commission rates and terms",
    ],
    "billy-the-trader": [
        "synthetic creator brand sponsorship rates benchmarks",
        "automated trading social media monetization metrics",
    ],
    "trading-strategy-hardening": [
        "binance futures taker fees tier structure",
        "crypto trading execution slippage benchmarks",
    ],
    "production-engine-acceleration": [
        "cloud render farm compute pricing per hour gpu",
        "automated batch video rendering service rates",
    ],
    "fp-labs-external-services": [
        "boutique software engineering consulting hourly rates",
        "workflow automation agency project pricing",
    ],
    "section-8-real-estate": [
        "section 8 housing choice voucher fair market rents hud",
        "residential real estate cap rates rental subsidies",
    ],
    "prediction-markets-latam": [
        "prediction market exchange regulatory licensing latam",
        "sports betting event contract legal framework latin america",
    ],
    "arbitrage-engine": [
        "crypto exchange api latency taker fee tier arbitrage",
        "cross exchange digital asset liquidity spreads",
    ],
}


class ResearchPackageAdapter:
    """Service to adapt compressed ResearchPackages into bounded ResearchObjectives."""

    def adapt_package(
        self,
        package: ResearchPackage,
        opportunity: MonetizationOpportunity | None = None,
    ) -> ResearchPackageObjective:
        """Convert a single ResearchPackage into a ResearchPackageObjective.

        Preserves 100% of atomic target IDs, opportunity ID, and cluster context.
        Identifies operator requirements and blocks invalid web substitution.
        """
        atomic_targets = [f"{package.opportunity_id}:{field}" for field in package.target_fields]
        objective_id = f"OBJ_{package.package_id}"
        opp_id = package.opportunity_id
        cluster = package.cluster_name

        # Determine jurisdiction
        jurisdiction: str | None = None
        if opp_id == "section-8-real-estate":
            jurisdiction = "US"
        elif opp_id == "prediction-markets-latam":
            jurisdiction = "LATAM"

        # Determine blockers
        is_blocked = False
        blocker_reason: str | None = None
        if opportunity and opportunity.blockers:
            is_blocked = True
            blocker_reason = "; ".join(opportunity.blockers)
        elif opp_id in ("section-8-real-estate", "prediction-markets-latam", "arbitrage-engine"):
            # Known baseline blockers
            is_blocked = True
            blocker_reason = f"Upstream structural blocker identified for {opp_id}"

        # Default classification variables
        requires_operator = False
        operator_instructions: str | None = None
        obj_type = PackageObjectiveType.WEB_RESEARCH
        desired_sources: list[SourceType] = [SourceType.WEB_PAGE]
        search_queries: list[str] = []

        # Cluster-specific routing
        if cluster == "OPERATIONAL_BANDWIDTH":
            obj_type = PackageObjectiveType.OPERATOR_INTAKE
            requires_operator = True
            operator_instructions = (
                f"Operator must provide operational commitments for {opp_id}: "
                f"Daniel hours (first 30 and 90 days), estimated time-to-first-dollar days, "
                f"and operational complexity rating."
            )
            desired_sources = [SourceType.DOCUMENT]

        elif cluster == "CAPABILITY_LEVERAGE":
            if opp_id in ("trading-strategy-hardening", "production-engine-acceleration"):
                obj_type = PackageObjectiveType.INTERNAL_AUDIT
                desired_sources = [SourceType.DOCUMENT]
            else:
                obj_type = PackageObjectiveType.INTERNAL_AUDIT
                desired_sources = [SourceType.DOCUMENT]

        elif cluster == "CAPITAL_AND_RISK":
            if opp_id == "cinema-collection-equipment-rental":
                obj_type = PackageObjectiveType.OPERATOR_INTAKE
                requires_operator = True
                operator_instructions = (
                    "Operator must provide owned equipment manifest: make, model, mount, "
                    "working condition, acquisition cost, and replacement value."
                )
                desired_sources = [SourceType.DOCUMENT]
            elif opp_id in ("trading-strategy-hardening", "arbitrage-engine"):
                obj_type = PackageObjectiveType.EMPIRICAL_VALIDATION
                desired_sources = [SourceType.DOCUMENT]
            else:
                obj_type = PackageObjectiveType.WEB_RESEARCH
                search_queries = _OPPORTUNITY_SEARCH_QUERIES.get(opp_id, [f"{opp_id} capital requirements"])

        elif cluster == "EVIDENCE_PROVENANCE":
            if opp_id == "cinema-collection-equipment-rental":
                obj_type = PackageObjectiveType.OPERATOR_INTAKE
                requires_operator = True
                operator_instructions = (
                    "Operator must provide verified equipment inventory records and rental availability."
                )
                desired_sources = [SourceType.DOCUMENT]
            elif opp_id == "fp-labs-external-services":
                obj_type = PackageObjectiveType.OPERATOR_INTAKE
                requires_operator = True
                operator_instructions = (
                    "Operator must provide historical client project deliverables, invoices/rates, "
                    "Daniel hours, and lead sources. Desired pricing is excluded as strategy."
                )
                desired_sources = [SourceType.DOCUMENT]
            elif opp_id == "fpcriptoclub-monetization":
                obj_type = PackageObjectiveType.OPERATOR_INTAKE
                requires_operator = True
                operator_instructions = (
                    "Operator must provide channel observation metrics: Telegram subscribers, "
                    "active conversion rates, and monthly churn."
                )
                desired_sources = [SourceType.DOCUMENT]
            elif opp_id == "tiktok-shop-affiliate-creative":
                obj_type = PackageObjectiveType.OPERATOR_INTAKE
                requires_operator = True
                operator_instructions = (
                    "Operator must provide TikTok creator account status, followers, view metrics, "
                    "and affiliate eligibility status."
                )
                desired_sources = [SourceType.DOCUMENT]
            else:
                obj_type = PackageObjectiveType.INTERNAL_AUDIT
                desired_sources = [SourceType.DOCUMENT]

        elif cluster == "MARKET_AND_GOVERNANCE_RISK":
            if opp_id == "trading-strategy-hardening":
                obj_type = PackageObjectiveType.EMPIRICAL_VALIDATION
                desired_sources = [SourceType.DOCUMENT]
            else:
                obj_type = PackageObjectiveType.WEB_RESEARCH
                search_queries = _OPPORTUNITY_SEARCH_QUERIES.get(opp_id, [f"{opp_id} regulatory compliance risk"])

        elif cluster == "PRICING_AND_REVENUE":
            obj_type = PackageObjectiveType.WEB_RESEARCH
            search_queries = _OPPORTUNITY_SEARCH_QUERIES.get(
                opp_id,
                [f"{opp_id} pricing market benchmarks", f"{opp_id} revenue model rates"],
            )

        return ResearchPackageObjective(
            objective_id=objective_id,
            package_id=package.package_id,
            opportunity_id=opp_id,
            cluster_name=cluster,
            atomic_target_ids=atomic_targets,
            target_fields=list(package.target_fields),
            objective_type=obj_type,
            title=f"Research Objective: {package.title}",
            research_question=f"Investigate {cluster.lower().replace('_', ' ')} for {opp_id}: {package.objective}",
            detailed_scope=package.objective,
            desired_source_types=desired_sources,
            jurisdiction=jurisdiction,
            requires_operator_input=requires_operator,
            operator_instructions=operator_instructions,
            is_blocked=is_blocked,
            blocker_reason=blocker_reason,
            search_queries=search_queries,
        )

    def adapt_all(
        self,
        packages: Sequence[ResearchPackage],
        opportunities: Sequence[MonetizationOpportunity] | None = None,
    ) -> list[ResearchPackageObjective]:
        """Adapt a sequence of ResearchPackages into ResearchPackageObjectives.

        Maintains ordering and complete atomic provenance across all packages.
        """
        opp_map: dict[str, MonetizationOpportunity] = {}
        if opportunities:
            opp_map = {opp.opportunity_id: opp for opp in opportunities}

        return [
            self.adapt_package(pkg, opportunity=opp_map.get(pkg.opportunity_id))
            for pkg in packages
        ]
