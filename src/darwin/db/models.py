"""Core research data model foundation."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from darwin.db.base import Base

jsonb_metadata_type = JSONB().with_variant(JSON(), "sqlite")


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def new_research_run_public_id() -> str:
    """Return a stable public identifier for a research run."""

    return f"rrn_{uuid.uuid4().hex}"


class ResearchRunStatus(str, enum.Enum):
    """Lifecycle state for a bounded research investigation."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SourceType(str, enum.Enum):
    """Type of source referenced by research evidence."""

    WEB_PAGE = "WEB_PAGE"
    DOCUMENT = "DOCUMENT"
    DATASET = "DATASET"
    API = "API"
    OTHER = "OTHER"


class EvidenceType(str, enum.Enum):
    """Type of evidence captured from a source."""

    EXCERPT = "EXCERPT"
    SUMMARY = "SUMMARY"
    MEASUREMENT = "MEASUREMENT"
    OBSERVATION = "OBSERVATION"
    OTHER = "OTHER"


class ClaimType(str, enum.Enum):
    """Minimal claim categories for explicit propositions."""

    PROPOSITION = "PROPOSITION"
    ASSUMPTION = "ASSUMPTION"
    FINDING = "FINDING"


class ClaimStatus(str, enum.Enum):
    """Lifecycle state for claims under evaluation."""

    PROPOSED = "PROPOSED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class ClaimEvidenceRelation(str, enum.Enum):
    """Semantic relationship between a claim and an evidence unit."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONTEXTUALIZES = "CONTEXTUALIZES"
    RELATED = "RELATED"


class ConclusionStatus(str, enum.Enum):
    """Lifecycle state for a research-level conclusion."""

    DRAFT = "DRAFT"
    FINAL = "FINAL"
    SUPERSEDED = "SUPERSEDED"


class ResearchRun(Base):
    """One bounded research investigation."""

    __tablename__ = "research_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=new_research_run_public_id,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ResearchRunStatus] = mapped_column(
        Enum(ResearchRunStatus, name="research_run_status"),
        nullable=False,
        default=ResearchRunStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    research_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    darwin_version: Mapped[str] = mapped_column(String(64), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False, default=dict)

    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="research_run")
    claims: Mapped[list[Claim]] = relationship(back_populates="research_run")
    conclusions: Mapped[list[Conclusion]] = relationship(back_populates="research_run")


class Source(Base):
    """A source used during research."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"),
        nullable=False,
    )
    canonical_locator: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    publication_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    content_fingerprint: Mapped[str | None] = mapped_column(String(128))
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="source")


class Evidence(Base):
    """An evidence unit extracted from or derived from a source."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, name="evidence_type"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )

    research_run: Mapped[ResearchRun] = relationship(back_populates="evidence_items")
    source: Mapped[Source] = relationship(back_populates="evidence_items")
    claim_links: Mapped[list[ClaimEvidence]] = relationship(back_populates="evidence")


class Claim(Base):
    """An explicit proposition being evaluated by Darwin."""

    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_claims_confidence_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[ClaimType] = mapped_column(
        Enum(ClaimType, name="claim_type"),
        nullable=False,
        default=ClaimType.PROPOSITION,
    )
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status"),
        nullable=False,
        default=ClaimStatus.PROPOSED,
    )
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    research_run: Mapped[ResearchRun] = relationship(back_populates="claims")
    evidence_links: Mapped[list[ClaimEvidence]] = relationship(back_populates="claim")


class ClaimEvidence(Base):
    """Semantic link between a claim and evidence."""

    __tablename__ = "claim_evidence"
    __table_args__ = (UniqueConstraint("claim_id", "evidence_id", name="uq_claim_evidence_pair"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relation: Mapped[ClaimEvidenceRelation] = mapped_column(
        Enum(ClaimEvidenceRelation, name="claim_evidence_relation"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    claim: Mapped[Claim] = relationship(back_populates="evidence_links")
    evidence: Mapped[Evidence] = relationship(back_populates="claim_links")


class Conclusion(Base):
    """A research-level synthesis or result."""

    __tablename__ = "conclusions"
    __table_args__ = (
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_conclusions_confidence_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    status: Mapped[ConclusionStatus] = mapped_column(
        Enum(ConclusionStatus, name="conclusion_status"),
        nullable=False,
        default=ConclusionStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    research_run: Mapped[ResearchRun] = relationship(back_populates="conclusions")
