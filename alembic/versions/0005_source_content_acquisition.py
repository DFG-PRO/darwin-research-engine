"""add source content snapshots and evidence extraction records

Revision ID: 0005_source_content_acquisition
Revises: 0004_external_research_acquisition
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_source_content_acquisition"
down_revision: str | Sequence[str] | None = "0004_external_research_acquisition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

source_fetch_status = postgresql.ENUM(
    "SUCCESS",
    "FAILED",
    "UNSUPPORTED_CONTENT_TYPE",
    "TOO_LARGE",
    "ACCESS_DENIED",
    name="source_fetch_status",
    create_type=False,
)
evidence_extraction_status = postgresql.ENUM(
    "EXTRACTED",
    "FAILED",
    name="evidence_extraction_status",
    create_type=False,
)


def upgrade() -> None:
    source_fetch_status.create(op.get_bind(), checkfirst=True)
    evidence_extraction_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "source_content_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("requested_locator", sa.Text(), nullable=False),
        sa.Column("final_locator", sa.Text(), nullable=True),
        sa.Column("fetch_status", source_fetch_status, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("raw_content_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("normalized_content_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("retrieval_method_version", sa.String(length=64), nullable=False),
        sa.Column("normalization_method_version", sa.String(length=64), nullable=True),
        sa.Column("raw_body_size", sa.Integer(), nullable=True),
        sa.Column("normalized_body_size", sa.Integer(), nullable=True),
        sa.Column("raw_artifact_path", sa.Text(), nullable=True),
        sa.Column("normalized_artifact_path", sa.Text(), nullable=True),
        sa.Column("segment_count", sa.Integer(), nullable=False),
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
            "response_metadata",
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
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "source_content_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("segment_identifier", sa.String(length=64), nullable=False),
        sa.Column("segment_order", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=False),
        sa.Column("line_end", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["source_content_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "segment_identifier",
            name="uq_source_content_segments_snapshot_identifier",
        ),
    )
    op.create_table(
        "evidence_extraction_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=True),
        sa.Column("extraction_status", evidence_extraction_status, nullable=False),
        sa.Column("extraction_method_version", sa.String(length=64), nullable=False),
        sa.Column("selected_text", sa.Text(), nullable=True),
        sa.Column("selected_text_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("selection_locator", sa.Text(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["research_run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["segment_id"], ["source_content_segments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["source_content_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("evidence_extraction_records")
    op.drop_table("source_content_segments")
    op.drop_table("source_content_snapshots")

    evidence_extraction_status.drop(op.get_bind(), checkfirst=True)
    source_fetch_status.drop(op.get_bind(), checkfirst=True)
