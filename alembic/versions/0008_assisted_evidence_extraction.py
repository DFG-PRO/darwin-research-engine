"""add assisted evidence extraction candidates

Revision ID: 0008_assisted_evidence_extraction
Revises: 0007_research_planning
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_assisted_evidence_extraction"
down_revision: str | Sequence[str] | None = "0007_research_planning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

assisted_extraction_request_status = postgresql.ENUM(
    "COMPLETED",
    "FAILED",
    name="assisted_extraction_request_status",
    create_type=False,
)
evidence_candidate_status = postgresql.ENUM(
    "VALIDATED",
    "REJECTED_INVALID_GROUNDING",
    "REJECTED",
    "ACCEPTED",
    name="evidence_candidate_status",
    create_type=False,
)
evidence_candidate_acceptance_mode = postgresql.ENUM(
    "MANUAL",
    "AUTO_ACCEPTED",
    name="evidence_candidate_acceptance_mode",
    create_type=False,
)
evidence_type = postgresql.ENUM(
    "EXCERPT",
    "SUMMARY",
    "MEASUREMENT",
    "OBSERVATION",
    "OTHER",
    name="evidence_type",
    create_type=False,
)


def upgrade() -> None:
    assisted_extraction_request_status.create(op.get_bind(), checkfirst=True)
    evidence_candidate_status.create(op.get_bind(), checkfirst=True)
    evidence_candidate_acceptance_mode.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "assisted_evidence_extraction_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("research_plan_item_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column(
            "segment_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("research_objective", sa.Text(), nullable=False),
        sa.Column("evidence_requirement", sa.Text(), nullable=False),
        sa.Column("expected_evidence_type", evidence_type, nullable=True),
        sa.Column("extraction_instructions", sa.Text(), nullable=True),
        sa.Column("freshness_start", sa.Date(), nullable=True),
        sa.Column("freshness_end", sa.Date(), nullable=True),
        sa.Column("max_candidate_count", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("provider_model", sa.String(length=256), nullable=True),
        sa.Column("provider_response_id", sa.String(length=256), nullable=True),
        sa.Column("extraction_method_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", assisted_extraction_request_status, nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("accepted_candidate_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
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
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "validation_result",
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
            "usage_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "cost_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["research_plan_item_id"], ["research_plan_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["source_content_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "evidence_candidate_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("extraction_request_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("research_plan_item_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("source_content_segment_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=True),
        sa.Column("candidate_key", sa.String(length=64), nullable=False),
        sa.Column("exact_excerpt", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("proposed_evidence_type", evidence_type, nullable=False),
        sa.Column("relevance_explanation", sa.Text(), nullable=False),
        sa.Column("supports_research_task", sa.Boolean(), nullable=False),
        sa.Column("temporal_applicability", sa.Text(), nullable=True),
        sa.Column("status", evidence_candidate_status, nullable=False),
        sa.Column("acceptance_mode", evidence_candidate_acceptance_mode, nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "provider_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "structural_validation",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "grounding_validation",
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["extraction_request_id"],
            ["assisted_evidence_extraction_requests.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["research_plan_item_id"], ["research_plan_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["source_content_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_content_segment_id"], ["source_content_segments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("extraction_request_id", "candidate_key", name="uq_evidence_candidate_key"),
    )


def downgrade() -> None:
    op.drop_table("evidence_candidate_proposals")
    op.drop_table("assisted_evidence_extraction_requests")

    evidence_candidate_acceptance_mode.drop(op.get_bind(), checkfirst=True)
    evidence_candidate_status.drop(op.get_bind(), checkfirst=True)
    assisted_extraction_request_status.drop(op.get_bind(), checkfirst=True)
