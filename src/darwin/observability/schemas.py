"""Read models for operator-facing research run observability."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from darwin.research.schemas import ResearchRunRead
from darwin.research_loop.schemas import ResearchLoopExecutionSummary


class ResearchRunOverviewCountsRead(BaseModel):
    """Aggregate record counts for one research run."""

    source_count: int
    evidence_count: int
    claim_count: int
    claim_evidence_count: int
    conclusion_count: int


class ResearchRunOverviewIntegrityRead(BaseModel):
    """Condensed integrity status for one research run."""

    healthy: bool
    issue_count: int
    error_count: int
    warning_count: int
    info_count: int


class ResearchRunOverviewRead(BaseModel):
    """Single operator-facing health and state overview for one research run."""

    schema_version: str = "research-run-overview.v1"
    generated_at: datetime
    research_run: ResearchRunRead
    counts: ResearchRunOverviewCountsRead
    integrity: ResearchRunOverviewIntegrityRead
    loop_count: int
    latest_loop: ResearchLoopExecutionSummary | None
    loops: list[ResearchLoopExecutionSummary]
    overall_state: str
    operator_next_action: str
    warnings: list[str]
