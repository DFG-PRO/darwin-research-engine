"""add controlled narrative synthesis proposals

Revision ID: 0010_narrative_synthesis
Revises: 0009_assisted_claim_construction
Create Date: 2026-08-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010_narrative_synthesis"
down_revision: str | Sequence[str] | None = "0009_assisted_claim_construction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

narrative_synthesis_request_status = postgresql.ENUM(
    "COMPLETED",
    "FAILED",
    name="narrative_synthesis_request_status",
    create_type=False,
)
narrative_synthesis_proposal_status = postgresql.ENUM(
    "VALIDATED",
    "REJECTED_INVALID_GROUNDING",
    "REJECTED",
    "PUBLISHED",
    name="narrative_synthesis_proposal_status",
    create_type=False,
)


def upgrade() -> None:
    narrative_synthesis_request_status.create(op.get_bind(), checkfirst=True)
    narrative_synthesis_proposal_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "narrative_synthesis_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("report_purpose", sa.Text(), nullable=False),
        sa.Column("intended_audience", sa.Text(), nullable=False),
        sa.Column("requested_report_format", sa.String(length=64), nullable=False),
        sa.Column(
            "focus_areas",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("maximum_length", sa.Integer(), nullable=True),
        sa.Column(
            "include_sections",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "exclude_sections",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "tone_style",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("temporal_framing", sa.Text(), nullable=True),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("provider_model", sa.String(length=256), nullable=True),
        sa.Column("provider_response_id", sa.String(length=256), nullable=True),
        sa.Column("synthesis_method_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", narrative_synthesis_request_status, nullable=False),
        sa.Column("proposal_count", sa.Integer(), nullable=False),
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
            "context_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_narrative_synthesis_requests_run",
        "narrative_synthesis_requests",
        ["research_run_id"],
    )

    op.create_table(
        "narrative_synthesis_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("synthesis_request_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("provider_model", sa.String(length=256), nullable=True),
        sa.Column("provider_response_id", sa.String(length=256), nullable=True),
        sa.Column("synthesis_method_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("status", narrative_synthesis_proposal_status, nullable=False),
        sa.Column("proposal_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "referenced_claim_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "referenced_conclusion_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "referenced_evidence_ids",
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
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "provider_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["synthesis_request_id"],
            ["narrative_synthesis_requests.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_narrative_synthesis_proposals_request",
        "narrative_synthesis_proposals",
        ["synthesis_request_id"],
    )
    op.create_index(
        "ix_narrative_synthesis_proposals_run",
        "narrative_synthesis_proposals",
        ["research_run_id"],
    )

    op.create_table(
        "narrative_synthesis_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("finding_key", sa.String(length=64), nullable=False),
        sa.Column("section", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "claim_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "conclusion_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("validation_summary", sa.Text(), nullable=False),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["narrative_synthesis_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "section", "finding_key", name="uq_narrative_finding_key"),
    )
    op.create_index(
        "ix_narrative_synthesis_findings_proposal",
        "narrative_synthesis_findings",
        ["proposal_id"],
    )

    op.create_table(
        "narrative_research_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("report_version", sa.Integer(), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=128), nullable=False),
        sa.Column("artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["narrative_synthesis_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", name="uq_narrative_report_proposal"),
    )
    op.create_index(
        "ix_narrative_research_reports_run",
        "narrative_research_reports",
        ["research_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_narrative_research_reports_run", table_name="narrative_research_reports")
    op.drop_table("narrative_research_reports")
    op.drop_index("ix_narrative_synthesis_findings_proposal", table_name="narrative_synthesis_findings")
    op.drop_table("narrative_synthesis_findings")
    op.drop_index("ix_narrative_synthesis_proposals_run", table_name="narrative_synthesis_proposals")
    op.drop_index("ix_narrative_synthesis_proposals_request", table_name="narrative_synthesis_proposals")
    op.drop_table("narrative_synthesis_proposals")
    op.drop_index("ix_narrative_synthesis_requests_run", table_name="narrative_synthesis_requests")
    op.drop_table("narrative_synthesis_requests")

    narrative_synthesis_proposal_status.drop(op.get_bind(), checkfirst=True)
    narrative_synthesis_request_status.drop(op.get_bind(), checkfirst=True)
