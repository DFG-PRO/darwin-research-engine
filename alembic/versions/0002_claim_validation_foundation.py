"""add claim validation foundation

Revision ID: 0002_claim_validation_foundation
Revises: 0001_core_research_data_model
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_claim_validation_foundation"
down_revision: str | Sequence[str] | None = "0001_core_research_data_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

source_lineage_type = postgresql.ENUM(
    "DERIVED_FROM",
    "REPUBLISHED_FROM",
    name="source_lineage_type",
    create_type=False,
)
claim_validation_state = postgresql.ENUM(
    "UNASSESSED",
    "INSUFFICIENT_EVIDENCE",
    "SUPPORTED",
    "CORROBORATED",
    "CONTESTED",
    "CONTRADICTED",
    "HUMAN_REVIEW_PENDING",
    "HUMAN_VALIDATED",
    name="claim_validation_state",
    create_type=False,
)
human_validation_type = postgresql.ENUM(
    "REVIEW_REQUESTED",
    "VALIDATED",
    name="human_validation_type",
    create_type=False,
)


def upgrade() -> None:
    source_lineage_type.create(op.get_bind(), checkfirst=True)
    claim_validation_state.create(op.get_bind(), checkfirst=True)
    human_validation_type.create(op.get_bind(), checkfirst=True)

    op.add_column("sources", sa.Column("origin_source_id", sa.Uuid(), nullable=True))
    op.add_column(
        "sources",
        sa.Column("source_lineage_type", source_lineage_type, nullable=True),
    )
    op.create_foreign_key(
        "fk_sources_origin_source_id_sources",
        "sources",
        "sources",
        ["origin_source_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_sources_lineage_pair",
        "sources",
        "(origin_source_id is null and source_lineage_type is null) "
        "or (origin_source_id is not null and source_lineage_type is not null)",
    )

    op.create_table(
        "claim_validation_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("validation_state", claim_validation_state, nullable=False),
        sa.Column("supporting_evidence_count", sa.Integer(), nullable=False),
        sa.Column("contradicting_evidence_count", sa.Integer(), nullable=False),
        sa.Column("contextual_evidence_count", sa.Integer(), nullable=False),
        sa.Column("distinct_source_count", sa.Integer(), nullable=False),
        sa.Column("independent_supporting_source_count", sa.Integer(), nullable=False),
        sa.Column("independent_contradicting_source_count", sa.Integer(), nullable=False),
        sa.Column("independent_corroboration_exists", sa.Boolean(), nullable=False),
        sa.Column("contradiction_exists", sa.Boolean(), nullable=False),
        sa.Column("human_review_requested", sa.Boolean(), nullable=False),
        sa.Column("human_validation_present", sa.Boolean(), nullable=False),
        sa.Column(
            "reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("validation_method_version", sa.String(length=64), nullable=False),
        sa.CheckConstraint("supporting_evidence_count >= 0", name="ck_cve_supporting_count_nonnegative"),
        sa.CheckConstraint("contradicting_evidence_count >= 0", name="ck_cve_contradicting_count_nonnegative"),
        sa.CheckConstraint("contextual_evidence_count >= 0", name="ck_cve_contextual_count_nonnegative"),
        sa.CheckConstraint("distinct_source_count >= 0", name="ck_cve_distinct_source_count_nonnegative"),
        sa.CheckConstraint(
            "independent_supporting_source_count >= 0",
            name="ck_cve_independent_supporting_count_nonnegative",
        ),
        sa.CheckConstraint(
            "independent_contradicting_source_count >= 0",
            name="ck_cve_independent_contradicting_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "claim_human_validations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("validation_type", human_validation_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("validator_label", sa.String(length=128), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("claim_human_validations")
    op.drop_table("claim_validation_evaluations")
    op.drop_constraint("ck_sources_lineage_pair", "sources", type_="check")
    op.drop_constraint("fk_sources_origin_source_id_sources", "sources", type_="foreignkey")
    op.drop_column("sources", "source_lineage_type")
    op.drop_column("sources", "origin_source_id")

    human_validation_type.drop(op.get_bind(), checkfirst=True)
    claim_validation_state.drop(op.get_bind(), checkfirst=True)
    source_lineage_type.drop(op.get_bind(), checkfirst=True)
