"""add assisted claim construction candidates

Revision ID: 0009_assisted_claim_construction
Revises: 0008_assisted_evidence_extraction
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_assisted_claim_construction"
down_revision: str | Sequence[str] | None = "0008_assisted_evidence_extraction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

assisted_claim_construction_request_status = postgresql.ENUM(
    "COMPLETED",
    "FAILED",
    name="assisted_claim_construction_request_status",
    create_type=False,
)
claim_candidate_status = postgresql.ENUM(
    "VALIDATED",
    "REJECTED_INVALID_PROVENANCE",
    "REJECTED",
    "ACCEPTED",
    name="claim_candidate_status",
    create_type=False,
)
claim_candidate_acceptance_mode = postgresql.ENUM(
    "MANUAL",
    "AUTO_ACCEPTED",
    name="claim_candidate_acceptance_mode",
    create_type=False,
)
claim_type = postgresql.ENUM(
    "PROPOSITION",
    "ASSUMPTION",
    "FINDING",
    name="claim_type",
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
claim_construction_method = postgresql.ENUM(
    "MANUAL_EXPLICIT",
    name="claim_construction_method",
    create_type=False,
)


def upgrade() -> None:
    assisted_claim_construction_request_status.create(op.get_bind(), checkfirst=True)
    claim_candidate_status.create(op.get_bind(), checkfirst=True)
    claim_candidate_acceptance_mode.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "assisted_claim_construction_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("research_plan_item_id", sa.Uuid(), nullable=False),
        sa.Column(
            "evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("research_objective", sa.Text(), nullable=False),
        sa.Column("construction_instruction", sa.Text(), nullable=False),
        sa.Column("expected_claim_type", claim_type, nullable=True),
        sa.Column("temporal_scope", sa.Text(), nullable=True),
        sa.Column("max_candidate_count", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("provider_model", sa.String(length=256), nullable=True),
        sa.Column("provider_response_id", sa.String(length=256), nullable=True),
        sa.Column("construction_method_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", assisted_claim_construction_request_status, nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "claim_candidate_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("construction_request_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("research_plan_item_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=True),
        sa.Column("candidate_key", sa.String(length=64), nullable=False),
        sa.Column("proposed_claim_text", sa.Text(), nullable=False),
        sa.Column("proposed_claim_type", claim_type, nullable=False),
        sa.Column("temporal_scope", sa.Text(), nullable=True),
        sa.Column(
            "qualifiers",
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
        sa.Column("construction_rationale", sa.Text(), nullable=False),
        sa.Column("status", claim_candidate_status, nullable=False),
        sa.Column("acceptance_mode", claim_candidate_acceptance_mode, nullable=True),
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["claims.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["construction_request_id"],
            ["assisted_claim_construction_requests.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["research_plan_item_id"], ["research_plan_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("construction_request_id", "candidate_key", name="uq_claim_candidate_key"),
    )
    op.create_table(
        "claim_candidate_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("relation", claim_evidence_relation, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_candidate_id"],
            ["claim_candidate_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_candidate_id", "evidence_id", name="uq_claim_candidate_evidence"),
    )


def downgrade() -> None:
    op.drop_table("claim_candidate_evidence")
    op.drop_table("claim_candidate_proposals")
    op.drop_table("assisted_claim_construction_requests")

    claim_candidate_acceptance_mode.drop(op.get_bind(), checkfirst=True)
    claim_candidate_status.drop(op.get_bind(), checkfirst=True)
    assisted_claim_construction_request_status.drop(op.get_bind(), checkfirst=True)
