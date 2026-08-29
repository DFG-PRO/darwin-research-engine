"""add claim construction and conclusion claim traceability

Revision ID: 0006_claim_construction_synthesis
Revises: 0005_source_content_acquisition
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_claim_construction_synthesis"
down_revision: str | Sequence[str] | None = "0005_source_content_acquisition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

claim_construction_method = postgresql.ENUM(
    "MANUAL_EXPLICIT",
    name="claim_construction_method",
    create_type=False,
)
conclusion_claim_relation = postgresql.ENUM(
    "SUPPORTS_CONCLUSION",
    "CONTRADICTS_CONCLUSION",
    "CONTEXTUALIZES_CONCLUSION",
    name="conclusion_claim_relation",
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


def upgrade() -> None:
    claim_construction_method.create(op.get_bind(), checkfirst=True)
    conclusion_claim_relation.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "claim_construction_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("construction_method", claim_construction_method, nullable=False),
        sa.Column("construction_method_version", sa.String(length=64), nullable=False),
        sa.Column("claim_statement", sa.Text(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column(
            "warnings",
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
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "claim_construction_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_construction_record_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("relation", claim_evidence_relation, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_construction_record_id"],
            ["claim_construction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "claim_construction_record_id",
            "evidence_id",
            name="uq_claim_construction_evidence_record_evidence",
        ),
    )
    op.create_table(
        "conclusion_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conclusion_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("relation", conclusion_claim_relation, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conclusion_id"], ["conclusions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conclusion_id", "claim_id", name="uq_conclusion_claim_pair"),
    )


def downgrade() -> None:
    op.drop_table("conclusion_claims")
    op.drop_table("claim_construction_evidence")
    op.drop_table("claim_construction_records")

    conclusion_claim_relation.drop(op.get_bind(), checkfirst=True)
    claim_construction_method.drop(op.get_bind(), checkfirst=True)
