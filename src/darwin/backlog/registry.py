"""Registry service for the Darwin Master Research Backlog.

Provides deterministic querying, filtering, dispatch qualification, provenance auditing,
and conversion to active Darwin ResearchLoopRequests without mutating canonical Portfolio state.
"""

from __future__ import annotations

from typing import Sequence

from darwin.backlog.master_backlog import CANONICAL_MASTER_BACKLOG_ITEMS
from darwin.backlog.schemas import (
    BacklogCategory,
    BacklogPriority,
    BacklogStatus,
    ResearchBacklogItem,
    TechScoutAssessment,
    TechScoutDecision,
)
from darwin.db.models import ResearchLoopExecutionMode, SourceType
from darwin.research_loop.schemas import ResearchLoopBudgets, ResearchLoopRequest


class MasterResearchBacklogRegistry:
    """Deterministic, immutable registry of all canonical research backlog items."""

    def __init__(
        self,
        items: Sequence[ResearchBacklogItem] | None = None,
        assessments: Sequence[TechScoutAssessment] | None = None,
    ) -> None:
        raw_items = items if items is not None else CANONICAL_MASTER_BACKLOG_ITEMS
        self._items: dict[str, ResearchBacklogItem] = {
            item.item_id: item.model_copy(deep=True) for item in raw_items
        }
        self._assessments: dict[str, TechScoutAssessment] = {
            a.item_id: a.model_copy(deep=True) for a in (assessments or [])
        }

    def get(self, item_id: str) -> ResearchBacklogItem | None:
        """Retrieve backlog item by unique ID."""
        item = self._items.get(item_id)
        if item:
            return item.model_copy(deep=True)
        return None

    def list_all(self) -> list[ResearchBacklogItem]:
        """Return all backlog items in deterministic order."""
        return [item.model_copy(deep=True) for item in self._items.values()]

    def filter(
        self,
        category: BacklogCategory | None = None,
        priority: BacklogPriority | None = None,
        status: BacklogStatus | None = None,
        dispatchable_only: bool = False,
    ) -> list[ResearchBacklogItem]:
        """Filter backlog items by category, priority, status, or dispatchability."""
        results: list[ResearchBacklogItem] = []
        for item in self._items.values():
            if category is not None and item.category != category:
                continue
            if priority is not None and item.priority != priority:
                continue
            if status is not None and item.status != status:
                continue
            if dispatchable_only and not item.is_dispatchable:
                continue
            results.append(item.model_copy(deep=True))
        return results

    def dispatchable_items(self) -> list[ResearchBacklogItem]:
        """Return all items that are READY, unblocked, and eligible for immediate execution."""
        return self.filter(dispatchable_only=True)

    def counts_by_category(self) -> dict[BacklogCategory, int]:
        """Return count distribution by category."""
        counts = {cat: 0 for cat in BacklogCategory}
        for item in self._items.values():
            counts[item.category] += 1
        return counts

    def counts_by_priority(self) -> dict[BacklogPriority, int]:
        """Return count distribution by priority."""
        counts = {pri: 0 for pri in BacklogPriority}
        for item in self._items.values():
            counts[item.priority] += 1
        return counts

    def counts_by_status(self) -> dict[BacklogStatus, int]:
        """Return count distribution by status."""
        counts = {st: 0 for st in BacklogStatus}
        for item in self._items.values():
            counts[item.status] += 1
        return counts

    def missing_provenance_items(self) -> list[ResearchBacklogItem]:
        """Return all items whose provenance is missing and requires recovery."""
        return [
            item.model_copy(deep=True)
            for item in self._items.values()
            if not item.has_provenance
        ]

    def register_tech_scout_assessment(self, assessment: TechScoutAssessment) -> None:
        """Register a formal Technology Scout assessment and update item decision."""
        item = self._items.get(assessment.item_id)
        if not item:
            raise KeyError(f"Item '{assessment.item_id}' not found in registry.")
        if item.category != BacklogCategory.TECHNOLOGY_SCOUT:
            raise ValueError(
                f"Item '{assessment.item_id}' is in category {item.category.value}, "
                f"not TECHNOLOGY_SCOUT."
            )

        self._assessments[assessment.item_id] = assessment.model_copy(deep=True)
        # Update item's tech_scout_decision deterministically
        updated_item = item.model_copy(
            update={"tech_scout_decision": assessment.decision}
        )
        self._items[assessment.item_id] = updated_item

    def get_tech_scout_assessment(self, item_id: str) -> TechScoutAssessment | None:
        """Retrieve Technology Scout assessment for an item."""
        assessment = self._assessments.get(item_id)
        if assessment:
            return assessment.model_copy(deep=True)
        return None

    def to_research_loop_request(
        self,
        item_id: str,
        budgets: ResearchLoopBudgets | None = None,
        planning_provider: str = "fake",
        acquisition_provider: str = "fake",
        execution_mode: ResearchLoopExecutionMode = ResearchLoopExecutionMode.AUTO_GROUNDED,
    ) -> ResearchLoopRequest:
        """Convert a dispatchable backlog item into an actionable Darwin ResearchLoopRequest.

        Raises ValueError if the item is not dispatchable.
        """
        item = self._items.get(item_id)
        if not item:
            raise KeyError(f"Item '{item_id}' not found in registry.")
        if not item.is_dispatchable:
            raise ValueError(
                f"Item '{item_id}' is not dispatchable (status={item.status.value}, "
                f"blocked_by={item.blocked_by})."
            )

        metadata = {
            "backlog_item_id": item.item_id,
            "category": item.category.value,
            "priority": item.priority.value,
            "decision_type": item.decision_type,
            "origin": item.origin,
            "related_opportunity_id": item.related_opportunity_id,
            "related_project": item.related_project,
            "research_questions": list(item.research_questions),
        }

        return ResearchLoopRequest(
            research_question=item.research_questions[0] if item.research_questions else item.title,
            objective=item.objective,
            scope=f"Master Backlog: {item.category.value} / {item.title}",
            desired_source_types=[SourceType.WEB_PAGE, SourceType.DOCUMENT],
            planning_provider=planning_provider,
            acquisition_provider=acquisition_provider,
            execution_mode=execution_mode,
            budgets=budgets or ResearchLoopBudgets(max_iterations=1, max_searches=2, max_sources=3),
            publish_report=False,
            metadata=metadata,
        )
