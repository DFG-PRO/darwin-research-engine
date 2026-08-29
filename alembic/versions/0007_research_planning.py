"""add controlled research planning proposals

Revision ID: 0007_research_planning
Revises: 0006_claim_construction_synthesis
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_research_planning"
down_revision: str | Sequence[str] | None = "0006_claim_construction_synthesis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

research_plan_proposal_status = postgresql.ENUM(
    "PROPOSED",
    "APPROVED",
    "REJECTED",
    "FAILED",
    name="research_plan_proposal_status",
    create_type=False,
)
research_plan_approval_mode = postgresql.ENUM(
    "MANUAL",
    "AUTO_APPROVED",
    name="research_plan_approval_mode",
    create_type=False,
)
research_plan_priority = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    name="research_plan_priority",
    create_type=False,
)
research_plan_item_status = postgresql.ENUM(
    "PENDING",
    "SATISFIED",
    "WAIVED",
    name="research_plan_item_status",
    create_type=False,
)
source_type = postgresql.ENUM(
    "WEB_PAGE",
    "DOCUMENT",
    "DATASET",
    "API",
    "OTHER",
    name="source_type",
    create_type=False,
)


def upgrade() -> None:
    research_plan_proposal_status.create(op.get_bind(), checkfirst=True)
    research_plan_approval_mode.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "research_plan_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=True),
        sa.Column("original_question", sa.Text(), nullable=False),
        sa.Column("normalized_question", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column(
            "exclusions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "assumptions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "research_categories",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "expected_evidence_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "suggested_source_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", research_plan_proposal_status, nullable=False),
        sa.Column("approval_mode", research_plan_approval_mode, nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("provider_model", sa.String(length=256), nullable=True),
        sa.Column("provider_response_id", sa.String(length=256), nullable=True),
        sa.Column("planner_method_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
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
        sa.Column("planning_request", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("proposal_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "research_plan_proposal_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("item_key", sa.String(length=64), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("priority", research_plan_priority, nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("status", research_plan_item_status, nullable=False),
        sa.Column("expected_source_type", source_type, nullable=True),
        sa.Column(
            "expected_evidence_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "suggested_source_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "completion_criteria",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("item_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["proposal_id"], ["research_plan_proposals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "item_key", name="uq_research_plan_proposal_items_key"),
    )


def downgrade() -> None:
    op.drop_table("research_plan_proposal_items")
    op.drop_table("research_plan_proposals")

    research_plan_approval_mode.drop(op.get_bind(), checkfirst=True)
    research_plan_proposal_status.drop(op.get_bind(), checkfirst=True)
