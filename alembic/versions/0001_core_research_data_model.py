"""create core research data model

Revision ID: 0001_core_research_data_model
Revises:
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_core_research_data_model"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

research_run_status = postgresql.ENUM(
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "FAILED",
    name="research_run_status",
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
evidence_type = postgresql.ENUM(
    "EXCERPT",
    "SUMMARY",
    "MEASUREMENT",
    "OBSERVATION",
    "OTHER",
    name="evidence_type",
    create_type=False,
)
claim_type = postgresql.ENUM(
    "PROPOSITION",
    "ASSUMPTION",
    "FINDING",
    name="claim_type",
    create_type=False,
)
claim_status = postgresql.ENUM(
    "PROPOSED",
    "UNDER_REVIEW",
    "RESOLVED",
    "REJECTED",
    name="claim_status",
    create_type=False,
)
claim_evidence_relation = postgresql.ENUM(
    "SUPPORTS",
    "CONTRADICTS",
    "CONTEXTUALIZES",
    "RELATED",
    name="claim_evidence_relation",
    create_type=False,
)
conclusion_status = postgresql.ENUM(
    "DRAFT",
    "FINAL",
    "SUPERSEDED",
    name="conclusion_status",
    create_type=False,
)


def upgrade() -> None:
    research_run_status.create(op.get_bind(), checkfirst=True)
    source_type.create(op.get_bind(), checkfirst=True)
    evidence_type.create(op.get_bind(), checkfirst=True)
    claim_type.create(op.get_bind(), checkfirst=True)
    claim_status.create(op.get_bind(), checkfirst=True)
    claim_evidence_relation.create(op.get_bind(), checkfirst=True)
    conclusion_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "research_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", research_run_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("research_method_version", sa.String(length=64), nullable=False),
        sa.Column("darwin_version", sa.String(length=64), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("canonical_locator", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("claim_type", claim_type, nullable=False),
        sa.Column("status", claim_status, nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_claims_confidence_range",
        ),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", evidence_type, nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "conclusions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("status", conclusion_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_conclusions_confidence_range",
        ),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "claim_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("relation", claim_evidence_relation, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id", "evidence_id", name="uq_claim_evidence_pair"),
    )


def downgrade() -> None:
    op.drop_table("claim_evidence")
    op.drop_table("conclusions")
    op.drop_table("evidence")
    op.drop_table("claims")
    op.drop_table("sources")
    op.drop_table("research_runs")

    conclusion_status.drop(op.get_bind(), checkfirst=True)
    claim_evidence_relation.drop(op.get_bind(), checkfirst=True)
    claim_status.drop(op.get_bind(), checkfirst=True)
    claim_type.drop(op.get_bind(), checkfirst=True)
    evidence_type.drop(op.get_bind(), checkfirst=True)
    source_type.drop(op.get_bind(), checkfirst=True)
    research_run_status.drop(op.get_bind(), checkfirst=True)
