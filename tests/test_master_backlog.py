"""Deterministic acceptance tests for the Darwin Master Research Backlog."""

import pytest
from pydantic import ValidationError

from darwin.backlog import (
    BacklogCategory,
    BacklogPriority,
    BacklogStatus,
    CANONICAL_MASTER_BACKLOG_ITEMS,
    MasterResearchBacklogRegistry,
    ResearchBacklogItem,
    TechScoutAssessment,
    TechScoutDecision,
)
from darwin.monetization.portfolio import PORTFOLIO_01_OPPORTUNITIES
from darwin.research_loop.schemas import ResearchLoopRequest


@pytest.fixture
def registry() -> MasterResearchBacklogRegistry:
    return MasterResearchBacklogRegistry()


def test_1_all_canonical_items_load(registry: MasterResearchBacklogRegistry):
    """1. Verify that all canonical items load and registry is non-empty."""
    items = registry.list_all()
    assert len(items) == 44
    assert len(items) == len(CANONICAL_MASTER_BACKLOG_ITEMS)


def test_2_unique_item_ids(registry: MasterResearchBacklogRegistry):
    """2. Verify that every canonical backlog item has a unique ID."""
    items = registry.list_all()
    item_ids = [item.item_id for item in items]
    assert len(item_ids) == len(set(item_ids))


def test_3_valid_categories(registry: MasterResearchBacklogRegistry):
    """3. Verify that all items have one of the 4 canonical categories."""
    valid_cats = set(BacklogCategory)
    for item in registry.list_all():
        assert item.category in valid_cats
    counts = registry.counts_by_category()
    assert counts[BacklogCategory.MONETIZATION] == 12
    assert counts[BacklogCategory.BUSINESS_VALIDATION] == 5
    assert counts[BacklogCategory.TECHNOLOGY_SCOUT] == 16
    assert counts[BacklogCategory.INTELLIGENCE_CAPABILITIES] == 11


def test_4_valid_priorities(registry: MasterResearchBacklogRegistry):
    """4. Verify that all items have valid priorities from the canonical priority tiers."""
    valid_priorities = set(BacklogPriority)
    for item in registry.list_all():
        assert item.priority in valid_priorities


def test_5_valid_statuses(registry: MasterResearchBacklogRegistry):
    """5. Verify that all items have valid lifecycle statuses."""
    valid_statuses = set(BacklogStatus)
    for item in registry.list_all():
        assert item.status in valid_statuses


def test_6_existing_portfolio_opportunities_link_rather_than_duplicate(registry: MasterResearchBacklogRegistry):
    """6. Verify all 12 Monetization items link to existing Portfolio 01 opportunities without duplication."""
    mon_items = registry.filter(category=BacklogCategory.MONETIZATION)
    assert len(mon_items) == 12

    portfolio_opp_ids = {opp.opportunity_id for opp in PORTFOLIO_01_OPPORTUNITIES}
    linked_ids = {item.related_opportunity_id for item in mon_items}

    # Every monetization backlog item links to an exact Portfolio 01 opportunity ID
    assert linked_ids == portfolio_opp_ids
    assert len(linked_ids) == 12


def test_7_dependencies_preserved(registry: MasterResearchBacklogRegistry):
    """7. Verify blocked and dependent items preserve explicit dependencies and blocker reasons."""
    blocked_items = registry.filter(status=BacklogStatus.BLOCKED)
    assert len(blocked_items) == 3

    for item in blocked_items:
        assert len(item.blocked_by) > 0 or len(item.dependencies) > 0


def test_8_blocked_items_cannot_be_dispatched_as_ready():
    """8. Verify that constructing or setting a blocked item as READY raises validation error."""
    with pytest.raises(ValidationError, match="cannot have status 'READY'"):
        ResearchBacklogItem(
            item_id="RBACK-TEST-BLOCKED",
            title="Test Blocked Item",
            category=BacklogCategory.MONETIZATION,
            priority=BacklogPriority.P0,
            status=BacklogStatus.READY,  # Invalid: has blocked_by but set to READY
            objective="Testing blocked invariant",
            origin="Test",
            blocked_by=["Upfront capital required"],
            expected_output="None",
            decision_type="TEST",
            created_at="2026-09-17",
            updated_at="2026-09-17",
        )


def test_9_parked_and_rejected_cannot_dispatch():
    """9. Verify PARKED and REJECTED items cannot have READY status or be dispatchable."""
    with pytest.raises(ValidationError, match="cannot have active status 'READY'"):
        ResearchBacklogItem(
            item_id="RBACK-TEST-PARKED",
            title="Test Parked Item",
            category=BacklogCategory.TECHNOLOGY_SCOUT,
            priority=BacklogPriority.PARKED,
            status=BacklogStatus.READY,  # Invalid
            objective="Testing parked invariant",
            origin="Test",
            expected_output="None",
            decision_type="TEST",
            created_at="2026-09-17",
            updated_at="2026-09-17",
        )

    # Valid parked item with status PARKED
    parked_item = ResearchBacklogItem(
        item_id="RBACK-TEST-PARKED-VALID",
        title="Test Parked Valid",
        category=BacklogCategory.TECHNOLOGY_SCOUT,
        priority=BacklogPriority.PARKED,
        status=BacklogStatus.PARKED,
        objective="Testing parked valid",
        origin="Test",
        expected_output="None",
        decision_type="TEST",
        created_at="2026-09-17",
        updated_at="2026-09-17",
    )
    assert parked_item.is_dispatchable is False


def test_10_provenance_can_explicitly_be_missing(registry: MasterResearchBacklogRegistry):
    """10. Verify that provenance can explicitly be empty without triggering error."""
    val_item = registry.get("RBACK-VAL-001")
    assert val_item is not None
    assert val_item.provenance_refs == []
    assert val_item.has_provenance is False


def test_11_missing_provenance_produces_research_requirement_rather_than_fabricated_citation(
    registry: MasterResearchBacklogRegistry,
):
    """11. Verify missing provenance items are explicitly identified for provenance recovery."""
    missing_items = registry.missing_provenance_items()
    assert len(missing_items) > 0

    scrapling = registry.get("RBACK-TECH-001")
    assert scrapling is not None
    assert scrapling.provenance_refs == []
    assert scrapling.has_provenance is False
    assert "provenance" in scrapling.expected_output.lower() or "scout" in scrapling.title.lower()


def test_12_technology_scout_outcomes_use_canonical_decision_vocabulary(
    registry: MasterResearchBacklogRegistry,
):
    """12. Verify that Technology Scout assessments require canonical decision vocabulary."""
    valid_decisions = {
        TechScoutDecision.USE,
        TechScoutDecision.USE_BEHIND_ADAPTER,
        TechScoutDecision.FORK_ADAPT,
        TechScoutDecision.REIMPLEMENT,
        TechScoutDecision.COPY_ARCHITECTURAL_PATTERN,
        TechScoutDecision.STUDY_ONLY,
        TechScoutDecision.REJECT,
    }
    assert len(valid_decisions) == 7

    assessment = TechScoutAssessment(
        item_id="RBACK-TECH-001",
        technology_name="Scrapling",
        what_it_does="Undetected web scraping library",
        problem_solved="Anti-bot bypassing and structured extraction",
        maturity="Active community library",
        evidence_it_works="Demonstrated evasion of Cloudflare/Datadome benchmarks",
        architecture="Python async HTTP/browser abstraction layer",
        programmatic_access="Python API and CLI",
        self_hosting="Fully local self-hosted",
        license="MIT",
        cost="Free open-source",
        vendor_dependency="Zero cloud vendor lock-in",
        privacy_and_security="No outbound telemetry",
        maintenance_burden="Low (Python dependency)",
        dfg_integration_potential="High for Darwin AcquisitionService",
        existing_overlap="Overlaps with raw httpx/playwright",
        implementation_effort="Medium (Adapter creation required)",
        expected_leverage="High acquisition reliability",
        decision=TechScoutDecision.USE_BEHIND_ADAPTER,
        decision_rationale="Provides evasion without polluting Darwin core.",
    )

    registry.register_tech_scout_assessment(assessment)
    retrieved = registry.get_tech_scout_assessment("RBACK-TECH-001")
    assert retrieved is not None
    assert retrieved.decision == TechScoutDecision.USE_BEHIND_ADAPTER

    # Verify item is updated
    item = registry.get("RBACK-TECH-001")
    assert item is not None
    assert item.tech_scout_decision == TechScoutDecision.USE_BEHIND_ADAPTER


def test_13_serialization_deterministic(registry: MasterResearchBacklogRegistry):
    """13. Verify that JSON serialization of backlog items is deterministic."""
    item = registry.get("RBACK-MON-001")
    assert item is not None
    json1 = item.model_dump_json(indent=2)
    json2 = item.model_dump_json(indent=2)
    assert json1 == json2


def test_14_loading_is_idempotent():
    """14. Verify that loading the registry multiple times yields identical states."""
    reg1 = MasterResearchBacklogRegistry()
    reg2 = MasterResearchBacklogRegistry()

    items1 = reg1.list_all()
    items2 = reg2.list_all()

    assert len(items1) == len(items2)
    for i1, i2 in zip(items1, items2, strict=True):
        assert i1.item_id == i2.item_id
        assert i1.model_dump() == i2.model_dump()


def test_15_no_portfolio_mutation_occurs(registry: MasterResearchBacklogRegistry):
    """15. Verify that querying, filtering, or dispatching never mutates Portfolio 01."""
    # Record baseline state of Portfolio 01
    baseline_opp = PORTFOLIO_01_OPPORTUNITIES[0]
    assert baseline_opp.expected_30_day_net_revenue_usd is None
    assert baseline_opp.upfront_capital_usd is None

    # Perform registry operations
    dispatchable = registry.dispatchable_items()
    assert len(dispatchable) > 0

    first_dispatchable = dispatchable[0]
    loop_request = registry.to_research_loop_request(first_dispatchable.item_id)
    assert isinstance(loop_request, ResearchLoopRequest)

    # Ensure canonical opportunity fields remain unmutated
    assert baseline_opp.expected_30_day_net_revenue_usd is None
    assert baseline_opp.upfront_capital_usd is None
