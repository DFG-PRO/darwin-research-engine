"""Core research data model foundation."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
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


class SourceLineageType(str, enum.Enum):
    """Explicit source relationship to an origin source."""

    DERIVED_FROM = "DERIVED_FROM"
    REPUBLISHED_FROM = "REPUBLISHED_FROM"


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


class ClaimValidationState(str, enum.Enum):
    """Structural validation state for a claim."""

    UNASSESSED = "UNASSESSED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SUPPORTED = "SUPPORTED"
    CORROBORATED = "CORROBORATED"
    CONTESTED = "CONTESTED"
    CONTRADICTED = "CONTRADICTED"
    HUMAN_REVIEW_PENDING = "HUMAN_REVIEW_PENDING"
    HUMAN_VALIDATED = "HUMAN_VALIDATED"


class ClaimValidationReasonCode(str, enum.Enum):
    """Machine-readable reasons for a claim validation state."""

    NO_EVIDENCE = "NO_EVIDENCE"
    SINGLE_SUPPORTING_SOURCE = "SINGLE_SUPPORTING_SOURCE"
    MULTIPLE_INDEPENDENT_SUPPORTING_SOURCES = "MULTIPLE_INDEPENDENT_SUPPORTING_SOURCES"
    CONTRADICTORY_EVIDENCE_PRESENT = "CONTRADICTORY_EVIDENCE_PRESENT"
    ONLY_CONTRADICTING_EVIDENCE = "ONLY_CONTRADICTING_EVIDENCE"
    ONLY_CONTEXTUAL_EVIDENCE = "ONLY_CONTEXTUAL_EVIDENCE"
    DERIVED_SOURCES_NOT_COUNTED_AS_INDEPENDENT = "DERIVED_SOURCES_NOT_COUNTED_AS_INDEPENDENT"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    HUMAN_VALIDATION_PRESENT = "HUMAN_VALIDATION_PRESENT"


class HumanValidationType(str, enum.Enum):
    """Explicit human validation event type."""

    REVIEW_REQUESTED = "REVIEW_REQUESTED"
    VALIDATED = "VALIDATED"


class ResearchPlanItemStatus(str, enum.Enum):
    """Lifecycle state for a research plan item."""

    PENDING = "PENDING"
    SATISFIED = "SATISFIED"
    WAIVED = "WAIVED"


class ResearchPlanPriority(str, enum.Enum):
    """Small priority set for research plan items."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ResearchCompletionAssessment(str, enum.Enum):
    """Deterministic completion assessment for a research run."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    UNRESOLVED_CONTRADICTION = "UNRESOLVED_CONTRADICTION"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class AcquisitionStatus(str, enum.Enum):
    """Execution state for an external source acquisition request."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SourceCandidateRegistrationStatus(str, enum.Enum):
    """Registration outcome for an acquired source candidate."""

    REGISTERED_NEW_SOURCE = "REGISTERED_NEW_SOURCE"
    REGISTERED_EXISTING_SOURCE = "REGISTERED_EXISTING_SOURCE"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"
    NOT_REGISTERED = "NOT_REGISTERED"
    REGISTRATION_FAILED = "REGISTRATION_FAILED"


class SourceFetchStatus(str, enum.Enum):
    """Execution state for fetching source content."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNSUPPORTED_CONTENT_TYPE = "UNSUPPORTED_CONTENT_TYPE"
    TOO_LARGE = "TOO_LARGE"
    ACCESS_DENIED = "ACCESS_DENIED"


class EvidenceExtractionStatus(str, enum.Enum):
    """Execution state for deterministic evidence extraction."""

    EXTRACTED = "EXTRACTED"
    FAILED = "FAILED"


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
    framings: Mapped[list[ResearchFraming]] = relationship(back_populates="research_run")
    plan_items: Mapped[list[ResearchPlanItem]] = relationship(back_populates="research_run")
    synthesis_records: Mapped[list[ResearchSynthesisRecord]] = relationship(
        back_populates="research_run",
    )
    acquisition_requests: Mapped[list[ResearchAcquisitionRequest]] = relationship(
        back_populates="research_run",
    )
    content_snapshots: Mapped[list[SourceContentSnapshot]] = relationship(
        back_populates="research_run",
    )


class Source(Base):
    """A source used during research."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            "(origin_source_id is null and source_lineage_type is null) "
            "or (origin_source_id is not null and source_lineage_type is not null)",
            name="ck_sources_lineage_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"),
        nullable=False,
    )
    canonical_locator: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    publication_date: Mapped[date | None] = mapped_column(Date)
    origin_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
    )
    source_lineage_type: Mapped[SourceLineageType | None] = mapped_column(
        Enum(SourceLineageType, name="source_lineage_type"),
    )
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
    origin_source: Mapped[Source | None] = relationship(remote_side=[id])
    acquisition_candidates: Mapped[list[SourceCandidate]] = relationship(
        back_populates="registered_source",
    )
    content_snapshots: Mapped[list[SourceContentSnapshot]] = relationship(
        back_populates="source",
    )


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
    extraction_records: Mapped[list[EvidenceExtractionRecord]] = relationship(
        back_populates="evidence",
    )


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
    validation_evaluations: Mapped[list[ClaimValidationEvaluation]] = relationship(
        back_populates="claim",
    )
    human_validation_events: Mapped[list[ClaimHumanValidation]] = relationship(
        back_populates="claim",
    )


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


class ClaimValidationEvaluation(Base):
    """Auditable structural validation result for a claim."""

    __tablename__ = "claim_validation_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="RESTRICT"),
        nullable=False,
    )
    validation_state: Mapped[ClaimValidationState] = mapped_column(
        Enum(ClaimValidationState, name="claim_validation_state"),
        nullable=False,
    )
    supporting_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    contradicting_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    contextual_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    distinct_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    independent_supporting_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    independent_contradicting_source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    independent_corroboration_exists: Mapped[bool] = mapped_column(Boolean, nullable=False)
    contradiction_exists: Mapped[bool] = mapped_column(Boolean, nullable=False)
    human_review_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    human_validation_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason_codes: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    validation_method_version: Mapped[str] = mapped_column(String(64), nullable=False)

    claim: Mapped[Claim] = relationship(back_populates="validation_evaluations")


class ClaimHumanValidation(Base):
    """Explicit human review or validation event for a claim."""

    __tablename__ = "claim_human_validations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="RESTRICT"),
        nullable=False,
    )
    validation_type: Mapped[HumanValidationType] = mapped_column(
        Enum(HumanValidationType, name="human_validation_type"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    validator_label: Mapped[str | None] = mapped_column(String(128))
    note: Mapped[str | None] = mapped_column(Text)

    claim: Mapped[Claim] = relationship(back_populates="human_validation_events")


class ResearchFraming(Base):
    """Auditable framing record for a research run."""

    __tablename__ = "research_framings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    original_question: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_question: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    exclusions: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    key_decision_criteria: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    assumptions: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    required_evidence_categories: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    completion_criteria: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    framing_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    research_run: Mapped[ResearchRun] = relationship(back_populates="framings")


class ResearchPlanItem(Base):
    """Auditable plan requirement for a research run."""

    __tablename__ = "research_plan_items"
    __table_args__ = (
        UniqueConstraint("research_run_id", "item_key", name="uq_research_plan_items_run_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_key: Mapped[str] = mapped_column(String(64), nullable=False)
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    priority: Mapped[ResearchPlanPriority] = mapped_column(
        Enum(ResearchPlanPriority, name="research_plan_priority"),
        nullable=False,
        default=ResearchPlanPriority.MEDIUM,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[ResearchPlanItemStatus] = mapped_column(
        Enum(ResearchPlanItemStatus, name="research_plan_item_status"),
        nullable=False,
        default=ResearchPlanItemStatus.PENDING,
    )
    expected_source_type: Mapped[SourceType | None] = mapped_column(
        Enum(SourceType, name="source_type"),
    )
    notes: Mapped[str | None] = mapped_column(Text)
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

    research_run: Mapped[ResearchRun] = relationship(back_populates="plan_items")


class ResearchSynthesisRecord(Base):
    """Auditable deterministic synthesis record for a research run."""

    __tablename__ = "research_synthesis_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    completion_assessment: Mapped[ResearchCompletionAssessment] = mapped_column(
        Enum(ResearchCompletionAssessment, name="research_completion_assessment"),
        nullable=False,
    )
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    claim_count: Mapped[int] = mapped_column(Integer, nullable=False)
    conclusion_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_gaps: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    unresolved_contradictions: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    synthesis_payload: Mapped[dict[str, Any]] = mapped_column(
        "payload",
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    research_run: Mapped[ResearchRun] = relationship(back_populates="synthesis_records")


class ResearchAcquisitionRequest(Base):
    """Auditable external source discovery request for a research run."""

    __tablename__ = "research_acquisition_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(256))
    query: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(128))
    requested_source_types: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    freshness_start: Mapped[date | None] = mapped_column(Date)
    freshness_end: Mapped[date | None] = mapped_column(Date)
    domain_constraints: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    result_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AcquisitionStatus] = mapped_column(
        Enum(AcquisitionStatus, name="acquisition_status"),
        nullable=False,
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registered_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_count: Mapped[int | None] = mapped_column(Integer)
    usage_units: Mapped[float | None] = mapped_column(Numeric(12, 4))
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 6))
    actual_cost: Mapped[float | None] = mapped_column(Numeric(12, 6))
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    request_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    rate_limit_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    research_run: Mapped[ResearchRun] = relationship(back_populates="acquisition_requests")
    candidates: Mapped[list[SourceCandidate]] = relationship(
        back_populates="acquisition_request",
    )


class SourceCandidate(Base):
    """Provider-returned source candidate before evidence or claim extraction."""

    __tablename__ = "source_candidates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    acquisition_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_acquisition_requests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_candidate_id: Mapped[str | None] = mapped_column(String(256))
    canonical_locator: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_locator: Mapped[str] = mapped_column(Text, nullable=False)
    deduplication_key: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    normalized_domain: Mapped[str | None] = mapped_column(String(255))
    publication_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    snippet: Mapped[str | None] = mapped_column(Text)
    provider_rank: Mapped[int | None] = mapped_column(Integer)
    source_type: Mapped[SourceType | None] = mapped_column(Enum(SourceType, name="source_type"))
    registration_status: Mapped[SourceCandidateRegistrationStatus] = mapped_column(
        Enum(
            SourceCandidateRegistrationStatus,
            name="source_candidate_registration_status",
        ),
        nullable=False,
        default=SourceCandidateRegistrationStatus.NOT_REGISTERED,
    )
    duplicate_of_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_candidates.id", ondelete="RESTRICT"),
    )
    registered_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
    )
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    acquisition_request: Mapped[ResearchAcquisitionRequest] = relationship(
        back_populates="candidates",
    )
    duplicate_of_candidate: Mapped[SourceCandidate | None] = relationship(remote_side=[id])
    registered_source: Mapped[Source | None] = relationship(
        back_populates="acquisition_candidates",
    )


class SourceContentSnapshot(Base):
    """Auditable content snapshot for one explicit source fetch attempt."""

    __tablename__ = "source_content_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_locator: Mapped[str] = mapped_column(Text, nullable=False)
    final_locator: Mapped[str | None] = mapped_column(Text)
    fetch_status: Mapped[SourceFetchStatus] = mapped_column(
        Enum(SourceFetchStatus, name="source_fetch_status"),
        nullable=False,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    content_type: Mapped[str | None] = mapped_column(String(255))
    response_status: Mapped[int | None] = mapped_column(Integer)
    raw_content_fingerprint: Mapped[str | None] = mapped_column(String(128))
    normalized_content_fingerprint: Mapped[str | None] = mapped_column(String(128))
    retrieval_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    normalization_method_version: Mapped[str | None] = mapped_column(String(64))
    raw_body_size: Mapped[int | None] = mapped_column(Integer)
    normalized_body_size: Mapped[int | None] = mapped_column(Integer)
    raw_artifact_path: Mapped[str | None] = mapped_column(Text)
    normalized_artifact_path: Mapped[str | None] = mapped_column(Text)
    segment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    response_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    request_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    research_run: Mapped[ResearchRun] = relationship(back_populates="content_snapshots")
    source: Mapped[Source] = relationship(back_populates="content_snapshots")
    segments: Mapped[list[SourceContentSegment]] = relationship(back_populates="snapshot")
    extraction_records: Mapped[list[EvidenceExtractionRecord]] = relationship(
        back_populates="snapshot",
    )


class SourceContentSegment(Base):
    """Addressable deterministic segment of normalized source content."""

    __tablename__ = "source_content_segments"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "segment_identifier",
            name="uq_source_content_segments_snapshot_identifier",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_content_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    segment_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    segment_order: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    locator: Mapped[str | None] = mapped_column(Text)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    line_start: Mapped[int] = mapped_column(Integer, nullable=False)
    line_end: Mapped[int] = mapped_column(Integer, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    snapshot: Mapped[SourceContentSnapshot] = relationship(back_populates="segments")
    source: Mapped[Source] = relationship()
    extraction_records: Mapped[list[EvidenceExtractionRecord]] = relationship(
        back_populates="segment",
    )


class EvidenceExtractionRecord(Base):
    """Audit record for explicit segment/span evidence extraction."""

    __tablename__ = "evidence_extraction_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_content_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_content_segments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"),
    )
    extraction_status: Mapped[EvidenceExtractionStatus] = mapped_column(
        Enum(EvidenceExtractionStatus, name="evidence_extraction_status"),
        nullable=False,
    )
    extraction_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_text: Mapped[str | None] = mapped_column(Text)
    selected_text_fingerprint: Mapped[str | None] = mapped_column(String(128))
    selection_locator: Mapped[str | None] = mapped_column(Text)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    extraction_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    research_run: Mapped[ResearchRun] = relationship()
    source: Mapped[Source] = relationship()
    snapshot: Mapped[SourceContentSnapshot] = relationship(back_populates="extraction_records")
    segment: Mapped[SourceContentSegment] = relationship(back_populates="extraction_records")
    evidence: Mapped[Evidence | None] = relationship(back_populates="extraction_records")
