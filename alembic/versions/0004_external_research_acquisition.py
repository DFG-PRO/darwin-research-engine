"""add external research acquisition audit records

Revision ID: 0004_external_research_acquisition
Revises: 0003_research_method_orchestration
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_external_research_acquisition"
down_revision: str | Sequence[str] | None = "0003_research_method_orchestration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

acquisition_status = postgresql.ENUM(
    "SUCCESS",
    "PARTIAL",
    "FAILED",
    name="acquisition_status",
    create_type=False,
)
source_candidate_registration_status = postgresql.ENUM(
    "REGISTERED_NEW_SOURCE",
    "REGISTERED_EXISTING_SOURCE",
    "DUPLICATE_CANDIDATE",
    "NOT_REGISTERED",
    "REGISTRATION_FAILED",
    name="source_candidate_registration_status",
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
    acquisition_status.create(op.get_bind(), checkfirst=True)
    source_candidate_registration_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "research_acquisition_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("provider_request_id", sa.String(length=256), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column(
            "requested_source_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("freshness_start", sa.Date(), nullable=True),
        sa.Column("freshness_end", sa.Date(), nullable=True),
        sa.Column(
            "domain_constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("result_limit", sa.Integer(), nullable=False),
        sa.Column("status", acquisition_status, nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("registered_source_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("retry_attempts", sa.Integer(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=True),
        sa.Column("usage_units", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("actual_cost", sa.Numeric(precision=12, scale=6), nullable=True),
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
            "metadata",
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
            "rate_limit_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "source_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("acquisition_request_id", sa.Uuid(), nullable=False),
        sa.Column("provider_candidate_id", sa.String(length=256), nullable=True),
        sa.Column("canonical_locator", sa.Text(), nullable=False),
        sa.Column("normalized_locator", sa.Text(), nullable=False),
        sa.Column("deduplication_key", sa.String(length=512), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("normalized_domain", sa.String(length=255), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("provider_rank", sa.Integer(), nullable=True),
        sa.Column("source_type", source_type, nullable=True),
        sa.Column("registration_status", source_candidate_registration_status, nullable=False),
        sa.Column("duplicate_of_candidate_id", sa.Uuid(), nullable=True),
        sa.Column("registered_source_id", sa.Uuid(), nullable=True),
        sa.Column(
            "provider_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["acquisition_request_id"],
            ["research_acquisition_requests.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_candidate_id"],
            ["source_candidates.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["registered_source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("source_candidates")
    op.drop_table("research_acquisition_requests")

    source_candidate_registration_status.drop(op.get_bind(), checkfirst=True)
    acquisition_status.drop(op.get_bind(), checkfirst=True)
