"""add controlled research loop execution records

Revision ID: 0011_research_loop
Revises: 0010_narrative_synthesis
Create Date: 2026-08-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011_research_loop"
down_revision: str | Sequence[str] | None = "0010_narrative_synthesis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

research_loop_execution_mode = postgresql.ENUM(
    "MANUAL_GATE",
    "AUTO_GROUNDED",
    "DRY_RUN",
    name="research_loop_execution_mode",
    create_type=False,
)
research_loop_state = postgresql.ENUM(
    "PENDING",
    "PLANNING",
    "ACQUIRING",
    "FETCHING_CONTENT",
    "EXTRACTING_EVIDENCE",
    "WAITING_EVIDENCE_APPROVAL",
    "CONSTRUCTING_CLAIMS",
    "WAITING_CLAIM_APPROVAL",
    "VALIDATING",
    "ASSESSING_COMPLETION",
    "ITERATING",
    "SYNTHESIZING",
    "WAITING_SYNTHESIS_PUBLICATION",
    "COMPLETED",
    "STOPPED_NEEDS_EVIDENCE",
    "STOPPED_CONTRADICTION",
    "STOPPED_HUMAN_REVIEW",
    "STOPPED_BUDGET",
    "FAILED",
    name="research_loop_state",
    create_type=False,
)
research_loop_stop_reason = postgresql.ENUM(
    "SUCCESS_COMPLETE",
    "NEEDS_EVIDENCE_NO_BUDGET",
    "MAX_ITERATIONS_REACHED",
    "UNRESOLVED_CONTRADICTION",
    "HUMAN_REVIEW_REQUIRED",
    "WAITING_EVIDENCE_APPROVAL",
    "WAITING_CLAIM_APPROVAL",
    "WAITING_SYNTHESIS_PUBLICATION",
    "PROVIDER_FAILURE",
    "BUDGET_EXHAUSTED",
    "TIME_BUDGET_EXCEEDED",
    "NO_USABLE_SOURCES",
    "NO_CANONICAL_EVIDENCE",
    "NO_CANONICAL_CLAIMS",
    "FATAL_INTEGRITY_ERROR",
    "DRY_RUN_COMPLETE",
    name="research_loop_stop_reason",
    create_type=False,
)
research_completion_assessment = postgresql.ENUM(
    "COMPLETE",
    "INCOMPLETE",
    "NEEDS_EVIDENCE",
    "UNRESOLVED_CONTRADICTION",
    "HUMAN_REVIEW_REQUIRED",
    name="research_completion_assessment",
    create_type=False,
)


def upgrade() -> None:
    research_loop_execution_mode.create(op.get_bind(), checkfirst=True)
    research_loop_state.create(op.get_bind(), checkfirst=True)
    research_loop_stop_reason.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "research_loop_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=True),
        sa.Column("execution_mode", research_loop_execution_mode, nullable=False),
        sa.Column("state", research_loop_state, nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("iteration_count", sa.Integer(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("budget_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "counters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "provider_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("stop_reason", research_loop_stop_reason, nullable=True),
        sa.Column("completion_assessment", research_completion_assessment, nullable=True),
        sa.Column("plan_proposal_id", sa.Uuid(), nullable=True),
        sa.Column("structured_synthesis_record_id", sa.Uuid(), nullable=True),
        sa.Column("narrative_synthesis_proposal_id", sa.Uuid(), nullable=True),
        sa.Column("narrative_report_id", sa.Uuid(), nullable=True),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "errors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "resume_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("loop_method_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["narrative_report_id"], ["narrative_research_reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["narrative_synthesis_proposal_id"],
            ["narrative_synthesis_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["plan_proposal_id"], ["research_plan_proposals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["structured_synthesis_record_id"],
            ["research_synthesis_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_loop_executions_run", "research_loop_executions", ["research_run_id"])
    op.create_index("ix_research_loop_executions_state", "research_loop_executions", ["state"])

    op.create_table(
        "research_loop_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("stage", research_loop_state, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("code", sa.String(length=128), nullable=True),
        sa.Column(
            "linked_object_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "counters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "provider_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "errors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["research_loop_executions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id", "sequence", name="uq_research_loop_event_sequence"),
    )
    op.create_index("ix_research_loop_events_execution", "research_loop_events", ["execution_id"])

    op.create_table(
        "research_loop_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("research_plan_item_id", sa.Uuid(), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("acquisition_request_id", sa.Uuid(), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["acquisition_request_id"], ["research_acquisition_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["execution_id"], ["research_loop_executions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["research_plan_item_id"], ["research_plan_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_loop_queries_execution", "research_loop_queries", ["execution_id"])


def downgrade() -> None:
    op.drop_index("ix_research_loop_queries_execution", table_name="research_loop_queries")
    op.drop_table("research_loop_queries")
    op.drop_index("ix_research_loop_events_execution", table_name="research_loop_events")
    op.drop_table("research_loop_events")
    op.drop_index("ix_research_loop_executions_state", table_name="research_loop_executions")
    op.drop_index("ix_research_loop_executions_run", table_name="research_loop_executions")
    op.drop_table("research_loop_executions")

    research_loop_stop_reason.drop(op.get_bind(), checkfirst=True)
    research_loop_state.drop(op.get_bind(), checkfirst=True)
    research_loop_execution_mode.drop(op.get_bind(), checkfirst=True)
