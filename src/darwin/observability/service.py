"""Read-only aggregation service for research run observability."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from darwin.db.models import utc_now
from darwin.observability.schemas import (
    ResearchRunOverviewCountsRead,
    ResearchRunOverviewIntegrityRead,
    ResearchRunOverviewRead,
)
from darwin.research import ResearchService
from darwin.research_loop import ResearchLoopController
from darwin.research_loop.schemas import ResearchLoopExecutionSummary


class ResearchRunOverviewService:
    """Compose existing read-only primitives into one operator overview."""

    def __init__(self, session: Session, settings: Any) -> None:
        self.session = session
        self.settings = settings
        self.research_service = ResearchService(session)

    def overview(
        self,
        identifier: str,
        *,
        min_supporting_sources: int = 1,
        include_loops: bool = True,
    ) -> ResearchRunOverviewRead:
        record = self.research_service.get_research_record(identifier)
        integrity = self.research_service.report_research_record_integrity(
            identifier,
            min_supporting_sources=min_supporting_sources,
        )
        loops = (
            ResearchLoopController(self.session, self.settings).list_for_research_run(
                record.research_run.id
            )
            if include_loops
            else []
        )
        latest_loop = _latest_loop(loops)
        return ResearchRunOverviewRead(
            generated_at=utc_now(),
            research_run=record.research_run,
            counts=ResearchRunOverviewCountsRead(
                source_count=len(record.sources),
                evidence_count=len(record.evidence),
                claim_count=len(record.claims),
                claim_evidence_count=len(record.claim_evidence),
                conclusion_count=len(record.conclusions),
            ),
            integrity=ResearchRunOverviewIntegrityRead(
                healthy=integrity.healthy,
                issue_count=integrity.summary.issue_count,
                error_count=integrity.summary.error_count,
                warning_count=integrity.summary.warning_count,
                info_count=integrity.summary.info_count,
            ),
            loop_count=len(loops),
            latest_loop=latest_loop,
            loops=loops,
            overall_state=_overall_state(integrity.healthy, latest_loop, include_loops),
            operator_next_action=_operator_next_action(
                integrity.healthy,
                latest_loop,
                include_loops,
            ),
            warnings=_warnings(integrity.healthy, loops, include_loops),
        )


def _latest_loop(
    loops: list[ResearchLoopExecutionSummary],
) -> ResearchLoopExecutionSummary | None:
    if not loops:
        return None
    return max(loops, key=lambda loop: loop.updated_at)


def _warnings(
    healthy: bool,
    loops: list[ResearchLoopExecutionSummary],
    include_loops: bool,
) -> list[str]:
    warnings: list[str] = []
    if not healthy:
        warnings.append("INTEGRITY_ISSUES_PRESENT")
    if include_loops and not loops:
        warnings.append("NO_LOOP_EXECUTIONS")
    return warnings


def _overall_state(
    healthy: bool,
    latest_loop: ResearchLoopExecutionSummary | None,
    include_loops: bool,
) -> str:
    if not healthy:
        return "NEEDS_ATTENTION"
    if include_loops and latest_loop is None:
        return "NO_LOOP_EXECUTIONS"
    if latest_loop is not None:
        return latest_loop.state.value
    return "OK"


def _operator_next_action(
    healthy: bool,
    latest_loop: ResearchLoopExecutionSummary | None,
    include_loops: bool,
) -> str:
    if not healthy:
        return "Review integrity issues with `darwin research integrity-report`."
    if include_loops and latest_loop is None:
        return "No loop execution is recorded for this run; inspect the record or start a loop if needed."
    if latest_loop is not None and latest_loop.stop_reason is not None:
        if "WAITING" in latest_loop.stop_reason.value:
            return "Resume or review the latest waiting loop checkpoint."
        if latest_loop.stop_reason.value == "HUMAN_REVIEW_REQUIRED":
            return "Human review is required for the latest loop."
    return "No immediate operator action detected by the overview."
