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


class ResearchPlanProposalStatus(str, enum.Enum):
    """Approval lifecycle for generated research plan proposals."""

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ResearchPlanApprovalMode(str, enum.Enum):
    """Auditable mode used to approve a planning proposal."""

    MANUAL = "MANUAL"
    AUTO_APPROVED = "AUTO_APPROVED"


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


class AssistedExtractionRequestStatus(str, enum.Enum):
    """Execution state for assisted evidence candidate extraction."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvidenceCandidateStatus(str, enum.Enum):
    """Lifecycle state for assisted evidence candidate proposals."""

    VALIDATED = "VALIDATED"
    REJECTED_INVALID_GROUNDING = "REJECTED_INVALID_GROUNDING"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"


class EvidenceCandidateAcceptanceMode(str, enum.Enum):
    """Auditable mode used to accept an evidence candidate."""

    MANUAL = "MANUAL"
    AUTO_ACCEPTED = "AUTO_ACCEPTED"


class ClaimConstructionMethod(str, enum.Enum):
    """Method used to construct a claim from evidence."""

    MANUAL_EXPLICIT = "MANUAL_EXPLICIT"


class AssistedClaimConstructionRequestStatus(str, enum.Enum):
    """Execution state for assisted claim candidate construction."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ClaimCandidateStatus(str, enum.Enum):
    """Lifecycle state for assisted claim candidate proposals."""

    VALIDATED = "VALIDATED"
    REJECTED_INVALID_PROVENANCE = "REJECTED_INVALID_PROVENANCE"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"


class ClaimCandidateAcceptanceMode(str, enum.Enum):
    """Auditable mode used to accept a claim candidate."""

    MANUAL = "MANUAL"
    AUTO_ACCEPTED = "AUTO_ACCEPTED"


class NarrativeSynthesisRequestStatus(str, enum.Enum):
    """Execution state for assisted narrative synthesis requests."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NarrativeSynthesisProposalStatus(str, enum.Enum):
    """Lifecycle state for assisted narrative synthesis proposals."""

    VALIDATED = "VALIDATED"
    REJECTED_INVALID_GROUNDING = "REJECTED_INVALID_GROUNDING"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"


class ResearchLoopExecutionMode(str, enum.Enum):
    """Control mode for bounded research loop execution."""

    MANUAL_GATE = "MANUAL_GATE"
    AUTO_GROUNDED = "AUTO_GROUNDED"
    DRY_RUN = "DRY_RUN"


class ResearchLoopState(str, enum.Enum):
    """Persistent state for a controlled research loop execution."""

    PENDING = "PENDING"
    PLANNING = "PLANNING"
    ACQUIRING = "ACQUIRING"
    FETCHING_CONTENT = "FETCHING_CONTENT"
    EXTRACTING_EVIDENCE = "EXTRACTING_EVIDENCE"
    WAITING_EVIDENCE_APPROVAL = "WAITING_EVIDENCE_APPROVAL"
    CONSTRUCTING_CLAIMS = "CONSTRUCTING_CLAIMS"
    WAITING_CLAIM_APPROVAL = "WAITING_CLAIM_APPROVAL"
    VALIDATING = "VALIDATING"
    ASSESSING_COMPLETION = "ASSESSING_COMPLETION"
    ITERATING = "ITERATING"
    SYNTHESIZING = "SYNTHESIZING"
    WAITING_SYNTHESIS_PUBLICATION = "WAITING_SYNTHESIS_PUBLICATION"
    COMPLETED = "COMPLETED"
    STOPPED_NEEDS_EVIDENCE = "STOPPED_NEEDS_EVIDENCE"
    STOPPED_CONTRADICTION = "STOPPED_CONTRADICTION"
    STOPPED_HUMAN_REVIEW = "STOPPED_HUMAN_REVIEW"
    STOPPED_BUDGET = "STOPPED_BUDGET"
    FAILED = "FAILED"


class ResearchLoopStopReason(str, enum.Enum):
    """Explicit stop reason for a controlled research loop execution."""

    SUCCESS_COMPLETE = "SUCCESS_COMPLETE"
    NEEDS_EVIDENCE_NO_BUDGET = "NEEDS_EVIDENCE_NO_BUDGET"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    UNRESOLVED_CONTRADICTION = "UNRESOLVED_CONTRADICTION"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    WAITING_EVIDENCE_APPROVAL = "WAITING_EVIDENCE_APPROVAL"
    WAITING_CLAIM_APPROVAL = "WAITING_CLAIM_APPROVAL"
    WAITING_SYNTHESIS_PUBLICATION = "WAITING_SYNTHESIS_PUBLICATION"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    TIME_BUDGET_EXCEEDED = "TIME_BUDGET_EXCEEDED"
    NO_USABLE_SOURCES = "NO_USABLE_SOURCES"
    NO_CANONICAL_EVIDENCE = "NO_CANONICAL_EVIDENCE"
    NO_CANONICAL_CLAIMS = "NO_CANONICAL_CLAIMS"
    FATAL_INTEGRITY_ERROR = "FATAL_INTEGRITY_ERROR"
    DRY_RUN_COMPLETE = "DRY_RUN_COMPLETE"


class ConclusionClaimRelation(str, enum.Enum):
    """Explicit relationship between a claim and a conclusion."""

    SUPPORTS_CONCLUSION = "SUPPORTS_CONCLUSION"
    CONTRADICTS_CONCLUSION = "CONTRADICTS_CONCLUSION"
    CONTEXTUALIZES_CONCLUSION = "CONTEXTUALIZES_CONCLUSION"


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
    claim_construction_records: Mapped[list[ClaimConstructionRecord]] = relationship(
        back_populates="research_run",
    )
    approved_plan_proposals: Mapped[list[ResearchPlanProposal]] = relationship(
        back_populates="research_run",
    )
    assisted_extraction_requests: Mapped[list[AssistedEvidenceExtractionRequest]] = relationship(
        back_populates="research_run",
    )
    assisted_claim_construction_requests: Mapped[list[AssistedClaimConstructionRequest]] = relationship(
        back_populates="research_run",
    )
    narrative_synthesis_requests: Mapped[list[NarrativeSynthesisRequest]] = relationship(
        back_populates="research_run",
    )
    narrative_synthesis_proposals: Mapped[list[NarrativeSynthesisProposal]] = relationship(
        back_populates="research_run",
    )
    narrative_research_reports: Mapped[list[NarrativeResearchReport]] = relationship(
        back_populates="research_run",
    )
    research_loop_executions: Mapped[list[ResearchLoopExecution]] = relationship(
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
    construction_evidence_links: Mapped[list[ClaimConstructionEvidence]] = relationship(
        back_populates="evidence",
    )
    accepted_candidate: Mapped[EvidenceCandidateProposal | None] = relationship(
        back_populates="evidence",
    )
    claim_candidate_links: Mapped[list[ClaimCandidateEvidence]] = relationship(
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
    construction_records: Mapped[list[ClaimConstructionRecord]] = relationship(
        back_populates="claim",
    )
    conclusion_links: Mapped[list[ConclusionClaim]] = relationship(back_populates="claim")
    accepted_candidate: Mapped[ClaimCandidateProposal | None] = relationship(back_populates="claim")


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
    claim_links: Mapped[list[ConclusionClaim]] = relationship(back_populates="conclusion")


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
    assisted_extraction_requests: Mapped[list[AssistedEvidenceExtractionRequest]] = relationship(
        back_populates="research_plan_item",
    )
    assisted_claim_construction_requests: Mapped[list[AssistedClaimConstructionRequest]] = relationship(
        back_populates="research_plan_item",
    )


class ResearchPlanProposal(Base):
    """Append-only planning proposal generated before research execution."""

    __tablename__ = "research_plan_proposals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
    )
    original_question: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_question: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    exclusions: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    assumptions: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    research_categories: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    expected_evidence_types: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    suggested_source_types: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    status: Mapped[ResearchPlanProposalStatus] = mapped_column(
        Enum(ResearchPlanProposalStatus, name="research_plan_proposal_status"),
        nullable=False,
        default=ResearchPlanProposalStatus.PROPOSED,
    )
    approval_mode: Mapped[ResearchPlanApprovalMode | None] = mapped_column(
        Enum(ResearchPlanApprovalMode, name="research_plan_approval_mode"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_model: Mapped[str | None] = mapped_column(String(256))
    provider_response_id: Mapped[str | None] = mapped_column(String(256))
    planner_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    planning_request: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False)
    proposal_payload: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False)
    validation_result: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    usage_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    cost_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    planning_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    research_run: Mapped[ResearchRun | None] = relationship(back_populates="approved_plan_proposals")
    items: Mapped[list[ResearchPlanProposalItem]] = relationship(back_populates="proposal")


class ResearchPlanProposalItem(Base):
    """One proposed research plan item before approval."""

    __tablename__ = "research_plan_proposal_items"
    __table_args__ = (
        UniqueConstraint("proposal_id", "item_key", name="uq_research_plan_proposal_items_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_plan_proposals.id", ondelete="RESTRICT"),
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
    expected_evidence_types: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    suggested_source_types: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    completion_criteria: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    item_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    proposal: Mapped[ResearchPlanProposal] = relationship(back_populates="items")


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
    assisted_extraction_requests: Mapped[list[AssistedEvidenceExtractionRequest]] = relationship(
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
    evidence_candidate_proposals: Mapped[list[EvidenceCandidateProposal]] = relationship(
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


class AssistedEvidenceExtractionRequest(Base):
    """Audit record for one assisted evidence candidate extraction attempt."""

    __tablename__ = "assisted_evidence_extraction_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_plan_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_plan_items.id", ondelete="RESTRICT"),
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
    segment_ids: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    research_objective: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    expected_evidence_type: Mapped[EvidenceType | None] = mapped_column(
        Enum(EvidenceType, name="evidence_type"),
    )
    extraction_instructions: Mapped[str | None] = mapped_column(Text)
    freshness_start: Mapped[date | None] = mapped_column(Date)
    freshness_end: Mapped[date | None] = mapped_column(Date)
    max_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_model: Mapped[str | None] = mapped_column(String(256))
    provider_response_id: Mapped[str | None] = mapped_column(String(256))
    extraction_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[AssistedExtractionRequestStatus] = mapped_column(
        Enum(AssistedExtractionRequestStatus, name="assisted_extraction_request_status"),
        nullable=False,
    )
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    request_payload: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False)
    validation_result: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    usage_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    cost_metadata: Mapped[dict[str, Any]] = mapped_column(
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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    research_run: Mapped[ResearchRun] = relationship(back_populates="assisted_extraction_requests")
    research_plan_item: Mapped[ResearchPlanItem] = relationship(
        back_populates="assisted_extraction_requests",
    )
    source: Mapped[Source] = relationship()
    snapshot: Mapped[SourceContentSnapshot] = relationship(
        back_populates="assisted_extraction_requests",
    )
    candidates: Mapped[list[EvidenceCandidateProposal]] = relationship(back_populates="request")


class EvidenceCandidateProposal(Base):
    """Provider-proposed evidence candidate grounded in stored source content."""

    __tablename__ = "evidence_candidate_proposals"
    __table_args__ = (
        UniqueConstraint("extraction_request_id", "candidate_key", name="uq_evidence_candidate_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    extraction_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assisted_evidence_extraction_requests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_plan_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_plan_items.id", ondelete="RESTRICT"),
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
    source_content_segment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_content_segments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"),
    )
    candidate_key: Mapped[str] = mapped_column(String(64), nullable=False)
    exact_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, name="evidence_type"),
        nullable=False,
    )
    relevance_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    supports_research_task: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    temporal_applicability: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EvidenceCandidateStatus] = mapped_column(
        Enum(EvidenceCandidateStatus, name="evidence_candidate_status"),
        nullable=False,
    )
    acceptance_mode: Mapped[EvidenceCandidateAcceptanceMode | None] = mapped_column(
        Enum(EvidenceCandidateAcceptanceMode, name="evidence_candidate_acceptance_mode"),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    provider_warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    structural_validation: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    grounding_validation: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
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

    request: Mapped[AssistedEvidenceExtractionRequest] = relationship(back_populates="candidates")
    research_run: Mapped[ResearchRun] = relationship()
    research_plan_item: Mapped[ResearchPlanItem] = relationship()
    source: Mapped[Source] = relationship()
    snapshot: Mapped[SourceContentSnapshot] = relationship()
    segment: Mapped[SourceContentSegment] = relationship(back_populates="evidence_candidate_proposals")
    evidence: Mapped[Evidence | None] = relationship(back_populates="accepted_candidate")


class ClaimConstructionRecord(Base):
    """Append-friendly audit record for explicit evidence-to-claim construction."""

    __tablename__ = "claim_construction_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="RESTRICT"),
        nullable=False,
    )
    construction_method: Mapped[ClaimConstructionMethod] = mapped_column(
        Enum(ClaimConstructionMethod, name="claim_construction_method"),
        nullable=False,
    )
    construction_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_statement: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    construction_metadata: Mapped[dict[str, Any]] = mapped_column(
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

    research_run: Mapped[ResearchRun] = relationship(back_populates="claim_construction_records")
    claim: Mapped[Claim] = relationship(back_populates="construction_records")
    evidence_selections: Mapped[list[ClaimConstructionEvidence]] = relationship(
        back_populates="construction_record",
    )


class ClaimConstructionEvidence(Base):
    """Evidence selected for an explicit claim construction record."""

    __tablename__ = "claim_construction_evidence"
    __table_args__ = (
        UniqueConstraint(
            "claim_construction_record_id",
            "evidence_id",
            name="uq_claim_construction_evidence_record_evidence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_construction_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claim_construction_records.id", ondelete="RESTRICT"),
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

    construction_record: Mapped[ClaimConstructionRecord] = relationship(
        back_populates="evidence_selections",
    )
    evidence: Mapped[Evidence] = relationship(back_populates="construction_evidence_links")


class AssistedClaimConstructionRequest(Base):
    """Audit record for one assisted claim candidate construction attempt."""

    __tablename__ = "assisted_claim_construction_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_plan_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_plan_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_ids: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    research_objective: Mapped[str] = mapped_column(Text, nullable=False)
    construction_instruction: Mapped[str] = mapped_column(Text, nullable=False)
    expected_claim_type: Mapped[ClaimType | None] = mapped_column(
        Enum(ClaimType, name="claim_type"),
    )
    temporal_scope: Mapped[str | None] = mapped_column(Text)
    max_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_model: Mapped[str | None] = mapped_column(String(256))
    provider_response_id: Mapped[str | None] = mapped_column(String(256))
    construction_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[AssistedClaimConstructionRequestStatus] = mapped_column(
        Enum(
            AssistedClaimConstructionRequestStatus,
            name="assisted_claim_construction_request_status",
        ),
        nullable=False,
    )
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    request_payload: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False)
    validation_result: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    usage_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    cost_metadata: Mapped[dict[str, Any]] = mapped_column(
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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    research_run: Mapped[ResearchRun] = relationship(
        back_populates="assisted_claim_construction_requests",
    )
    research_plan_item: Mapped[ResearchPlanItem] = relationship(
        back_populates="assisted_claim_construction_requests",
    )
    candidates: Mapped[list[ClaimCandidateProposal]] = relationship(back_populates="request")


class ClaimCandidateProposal(Base):
    """Provider-proposed Claim candidate grounded in canonical Evidence."""

    __tablename__ = "claim_candidate_proposals"
    __table_args__ = (
        UniqueConstraint("construction_request_id", "candidate_key", name="uq_claim_candidate_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    construction_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assisted_claim_construction_requests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_plan_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_plan_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("claims.id", ondelete="RESTRICT"),
    )
    candidate_key: Mapped[str] = mapped_column(String(64), nullable=False)
    proposed_claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_claim_type: Mapped[ClaimType] = mapped_column(
        Enum(ClaimType, name="claim_type"),
        nullable=False,
    )
    temporal_scope: Mapped[str | None] = mapped_column(Text)
    qualifiers: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    assumptions: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    construction_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ClaimCandidateStatus] = mapped_column(
        Enum(ClaimCandidateStatus, name="claim_candidate_status"),
        nullable=False,
    )
    acceptance_mode: Mapped[ClaimCandidateAcceptanceMode | None] = mapped_column(
        Enum(ClaimCandidateAcceptanceMode, name="claim_candidate_acceptance_mode"),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    provider_warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    validation_result: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
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

    request: Mapped[AssistedClaimConstructionRequest] = relationship(back_populates="candidates")
    research_run: Mapped[ResearchRun] = relationship()
    research_plan_item: Mapped[ResearchPlanItem] = relationship()
    claim: Mapped[Claim | None] = relationship(back_populates="accepted_candidate")
    evidence_links: Mapped[list[ClaimCandidateEvidence]] = relationship(back_populates="candidate")


class ClaimCandidateEvidence(Base):
    """Evidence selected by a claim candidate with Darwin relationship semantics."""

    __tablename__ = "claim_candidate_evidence"
    __table_args__ = (
        UniqueConstraint("claim_candidate_id", "evidence_id", name="uq_claim_candidate_evidence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claim_candidate_proposals.id", ondelete="RESTRICT"),
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

    candidate: Mapped[ClaimCandidateProposal] = relationship(back_populates="evidence_links")
    evidence: Mapped[Evidence] = relationship(back_populates="claim_candidate_links")


class NarrativeSynthesisRequest(Base):
    """Audit record for one assisted narrative synthesis attempt."""

    __tablename__ = "narrative_synthesis_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    report_purpose: Mapped[str] = mapped_column(Text, nullable=False)
    intended_audience: Mapped[str] = mapped_column(Text, nullable=False)
    requested_report_format: Mapped[str] = mapped_column(String(64), nullable=False)
    focus_areas: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    maximum_length: Mapped[int | None] = mapped_column(Integer)
    include_sections: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    exclude_sections: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    tone_style: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False, default=dict)
    temporal_framing: Mapped[str | None] = mapped_column(Text)
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_model: Mapped[str | None] = mapped_column(String(256))
    provider_response_id: Mapped[str | None] = mapped_column(String(256))
    synthesis_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[NarrativeSynthesisRequestStatus] = mapped_column(
        Enum(NarrativeSynthesisRequestStatus, name="narrative_synthesis_request_status"),
        nullable=False,
    )
    proposal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    request_payload: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False)
    context_payload: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False, default=dict)
    validation_result: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    usage_metadata: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    cost_metadata: Mapped[dict[str, Any]] = mapped_column(
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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    research_run: Mapped[ResearchRun] = relationship(back_populates="narrative_synthesis_requests")
    proposals: Mapped[list[NarrativeSynthesisProposal]] = relationship(back_populates="request")


class NarrativeSynthesisProposal(Base):
    """Validated or rejected structured narrative proposal from a bounded context."""

    __tablename__ = "narrative_synthesis_proposals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    synthesis_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("narrative_synthesis_requests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_model: Mapped[str | None] = mapped_column(String(256))
    provider_response_id: Mapped[str | None] = mapped_column(String(256))
    synthesis_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[NarrativeSynthesisProposalStatus] = mapped_column(
        Enum(NarrativeSynthesisProposalStatus, name="narrative_synthesis_proposal_status"),
        nullable=False,
    )
    proposal_payload: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False)
    referenced_claim_ids: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    referenced_conclusion_ids: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    referenced_evidence_ids: Mapped[list[str]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=list,
    )
    validation_result: Mapped[dict[str, Any]] = mapped_column(
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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

    request: Mapped[NarrativeSynthesisRequest] = relationship(back_populates="proposals")
    research_run: Mapped[ResearchRun] = relationship(back_populates="narrative_synthesis_proposals")
    findings: Mapped[list[NarrativeSynthesisFinding]] = relationship(back_populates="proposal")
    report: Mapped[NarrativeResearchReport | None] = relationship(back_populates="proposal")


class NarrativeSynthesisFinding(Base):
    """Material narrative finding with canonical Darwin references."""

    __tablename__ = "narrative_synthesis_findings"
    __table_args__ = (
        UniqueConstraint("proposal_id", "section", "finding_key", name="uq_narrative_finding_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("narrative_synthesis_proposals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    finding_key: Mapped[str] = mapped_column(String(64), nullable=False)
    section: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_ids: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    conclusion_ids: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    evidence_ids: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    validation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    proposal: Mapped[NarrativeSynthesisProposal] = relationship(back_populates="findings")
    research_run: Mapped[ResearchRun] = relationship()


class NarrativeResearchReport(Base):
    """Immutable/versioned user-readable research report artifact."""

    __tablename__ = "narrative_research_reports"
    __table_args__ = (UniqueConstraint("proposal_id", name="uq_narrative_report_proposal"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("narrative_synthesis_proposals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    report_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    report_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )

    proposal: Mapped[NarrativeSynthesisProposal] = relationship(back_populates="report")
    research_run: Mapped[ResearchRun] = relationship(back_populates="narrative_research_reports")


class ResearchLoopExecution(Base):
    """Top-level durable execution record for a controlled research loop."""

    __tablename__ = "research_loop_executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
    )
    execution_mode: Mapped[ResearchLoopExecutionMode] = mapped_column(
        Enum(ResearchLoopExecutionMode, name="research_loop_execution_mode"),
        nullable=False,
    )
    state: Mapped[ResearchLoopState] = mapped_column(
        Enum(ResearchLoopState, name="research_loop_state"),
        nullable=False,
        default=ResearchLoopState.PENDING,
    )
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    iteration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_payload: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False)
    budget_payload: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False)
    counters: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False, default=dict)
    provider_payload: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False, default=dict)
    stop_reason: Mapped[ResearchLoopStopReason | None] = mapped_column(
        Enum(ResearchLoopStopReason, name="research_loop_stop_reason"),
    )
    completion_assessment: Mapped[ResearchCompletionAssessment | None] = mapped_column(
        Enum(ResearchCompletionAssessment, name="research_completion_assessment"),
    )
    plan_proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_plan_proposals.id", ondelete="RESTRICT"),
    )
    structured_synthesis_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_synthesis_records.id", ondelete="RESTRICT"),
    )
    narrative_synthesis_proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("narrative_synthesis_proposals.id", ondelete="RESTRICT"),
    )
    narrative_report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("narrative_research_reports.id", ondelete="RESTRICT"),
    )
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    resume_metadata: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False, default=dict)
    loop_method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    research_run: Mapped[ResearchRun | None] = relationship(back_populates="research_loop_executions")
    events: Mapped[list[ResearchLoopEvent]] = relationship(back_populates="execution")
    queries: Mapped[list[ResearchLoopQuery]] = relationship(back_populates="execution")


class ResearchLoopEvent(Base):
    """Append-only audit event for controlled research loop behavior."""

    __tablename__ = "research_loop_events"
    __table_args__ = (
        UniqueConstraint("execution_id", "sequence", name="uq_research_loop_event_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_loop_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[ResearchLoopState] = mapped_column(
        Enum(ResearchLoopState, name="research_loop_state"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(String(128))
    linked_object_ids: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False, default=dict)
    counters: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False, default=dict)
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(jsonb_metadata_type, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(jsonb_metadata_type, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    execution: Mapped[ResearchLoopExecution] = relationship(back_populates="events")


class ResearchLoopQuery(Base):
    """Transparent bounded acquisition query generated by a research loop."""

    __tablename__ = "research_loop_queries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_loop_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_plan_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_plan_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    acquisition_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_acquisition_requests.id", ondelete="RESTRICT"),
    )
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    execution: Mapped[ResearchLoopExecution] = relationship(back_populates="queries")
    research_run: Mapped[ResearchRun] = relationship()
    research_plan_item: Mapped[ResearchPlanItem] = relationship()


class ConclusionClaim(Base):
    """Explicit relationship between a persisted conclusion and claim."""

    __tablename__ = "conclusion_claims"
    __table_args__ = (
        UniqueConstraint("conclusion_id", "claim_id", name="uq_conclusion_claim_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conclusion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conclusions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="RESTRICT"),
        nullable=False,
    )
    relation: Mapped[ConclusionClaimRelation] = mapped_column(
        Enum(ConclusionClaimRelation, name="conclusion_claim_relation"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    relationship_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        jsonb_metadata_type,
        nullable=False,
        default=dict,
    )

    conclusion: Mapped[Conclusion] = relationship(back_populates="claim_links")
    claim: Mapped[Claim] = relationship(back_populates="conclusion_links")
