"""add research method orchestration records

Revision ID: 0003_research_method_orchestration
Revises: 0002_claim_validation_foundation
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_research_method_orchestration"
down_revision: str | Sequence[str] | None = "0002_claim_validation_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

research_plan_item_status = postgresql.ENUM(
    "PENDING",
    "SATISFIED",
    "WAIVED",
    name="research_plan_item_status",
    create_type=False,
)
research_plan_priority = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    name="research_plan_priority",
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
    research_plan_item_status.create(op.get_bind(), checkfirst=True)
    research_plan_priority.create(op.get_bind(), checkfirst=True)
    research_completion_assessment.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "research_framings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
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
            "key_decision_criteria",
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
            "required_evidence_categories",
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
        "research_plan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("item_key", sa.String(length=64), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("priority", research_plan_priority, nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("status", research_plan_item_status, nullable=False),
        sa.Column("expected_source_type", source_type, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("research_run_id", "item_key", name="uq_research_plan_items_run_key"),
    )
    op.create_table(
        "research_synthesis_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("research_method_version", sa.String(length=64), nullable=False),
        sa.Column("completion_assessment", research_completion_assessment, nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("claim_count", sa.Integer(), nullable=False),
        sa.Column("conclusion_count", sa.Integer(), nullable=False),
        sa.Column(
            "evidence_gaps",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "unresolved_contradictions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("research_synthesis_records")
    op.drop_table("research_plan_items")
    op.drop_table("research_framings")

    research_completion_assessment.drop(op.get_bind(), checkfirst=True)
    research_plan_priority.drop(op.get_bind(), checkfirst=True)
    research_plan_item_status.drop(op.get_bind(), checkfirst=True)
