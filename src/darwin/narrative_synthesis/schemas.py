"""Pydantic contracts for controlled narrative research synthesis."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from darwin.db.models import (
    ClaimEvidenceRelation,
    ClaimType,
    ClaimValidationState,
    ConclusionClaimRelation,
    ConclusionStatus,
    EvidenceType,
    NarrativeSynthesisProposalStatus,
    ResearchCompletionAssessment,
    ResearchPlanItemStatus,
    ResearchPlanPriority,
    ResearchRunStatus,
    SourceLineageType,
    SourceType,
)


class NarrativeSynthesisLimits(BaseModel):
    """Bounded controls for narrative synthesis context and report output."""

    max_claims: int = Field(default=25, ge=1)
    max_evidence_items: int = Field(default=60, ge=1)
    max_evidence_chars: int = Field(default=20000, ge=1)
    max_findings: int = Field(default=20, ge=1)
    max_report_chars: int = Field(default=50000, ge=1000)
    max_assumptions: int = Field(default=10, ge=0)
    max_limitations: int = Field(default=10, ge=0)


class NarrativeSynthesisRequest(BaseModel):
    """Caller-controlled request for a narrative proposal."""

    model_config = ConfigDict(str_strip_whitespace=True)

    research_run_id: uuid.UUID
    report_purpose: str = Field(default="Communicate Darwin's canonical research state.", min_length=1)
    intended_audience: str = Field(default="research reviewer", min_length=1)
    requested_report_format: Literal["markdown", "brief", "detailed"] = "markdown"
    focus_areas: list[str] = Field(default_factory=list)
    maximum_length: int | None = Field(default=None, ge=100)
    include_sections: list[str] = Field(default_factory=list)
    exclude_sections: list[str] = Field(default_factory=list)
    tone_style: dict[str, Any] = Field(default_factory=dict)
    temporal_framing: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("focus_areas", "include_sections", "exclude_sections", mode="before")
    @classmethod
    def clean_string_list(cls, value: list[str] | None) -> list[str]:
        return [str(item).strip() for item in value or [] if str(item).strip()]

    @model_validator(mode="after")
    def validate_section_controls(self) -> NarrativeSynthesisRequest:
        overlap = set(self.include_sections).intersection(set(self.exclude_sections))
        if overlap:
            raise ValueError(f"sections cannot be both included and excluded: {sorted(overlap)}")
        return self


class SourceContext(BaseModel):
    """Provider-safe Source metadata."""

    id: uuid.UUID
    source_type: SourceType
    canonical_locator: str
    title: str | None = None
    publisher: str | None = None
    publication_date: date | None = None
    retrieved_at: datetime
    source_lineage_type: SourceLineageType | None = None
    origin_source_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceContext(BaseModel):
    """Provider-safe Evidence payload with source provenance."""

    id: uuid.UUID
    evidence_type: EvidenceType
    statement: str
    source_id: uuid.UUID
    source_locator: str | None = None
    captured_at: datetime
    snapshot_id: uuid.UUID | None = None
    segment_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimEvidenceContext(BaseModel):
    """Claim-to-Evidence relation included in narrative context."""

    evidence_id: uuid.UUID
    relation: ClaimEvidenceRelation


class ClaimContext(BaseModel):
    """Canonical Claim with latest validation and provenance links."""

    id: uuid.UUID
    statement: str
    claim_type: ClaimType
    validation_state: ClaimValidationState
    validation_reason_codes: list[str] = Field(default_factory=list)
    evidence: list[ClaimEvidenceContext] = Field(default_factory=list)
    supporting_evidence_count: int = 0
    contradicting_evidence_count: int = 0
    contextual_evidence_count: int = 0
    independent_source_count: int = 0
    unresolved_contradiction: bool = False
    human_review_requested: bool = False
    human_validation_present: bool = False
    warnings: list[str] = Field(default_factory=list)


class PlanItemContext(BaseModel):
    """Research plan item included in narrative context."""

    id: uuid.UUID
    item_key: str
    requirement: str
    category: str
    priority: ResearchPlanPriority
    is_required: bool
    status: ResearchPlanItemStatus
    expected_source_type: SourceType | None = None
    notes: str | None = None


class FramingContext(BaseModel):
    """Research framing state included in narrative context."""

    original_question: str
    normalized_question: str
    objective: str
    scope: str
    exclusions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    required_evidence_categories: list[str] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)


class ConclusionClaimContext(BaseModel):
    """Conclusion-to-Claim relationship included in narrative context."""

    claim_id: uuid.UUID
    relation: ConclusionClaimRelation
    claim_validation_state: ClaimValidationState


class ConclusionContext(BaseModel):
    """Canonical Conclusion included in narrative context."""

    id: uuid.UUID
    statement: str
    status: ConclusionStatus
    claim_links: list[ConclusionClaimContext] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SynthesisContext(BaseModel):
    """Bounded deterministic context handed to a narrative provider."""

    research_run_id: uuid.UUID
    public_id: str
    research_question: str
    run_status: ResearchRunStatus
    research_method_version: str
    darwin_version: str
    objective: str
    scope: str
    exclusions: list[str]
    assumptions: list[str]
    framing: FramingContext | None
    plan_items: list[PlanItemContext]
    claims: list[ClaimContext]
    evidence: list[EvidenceContext]
    sources: list[SourceContext]
    conclusions: list[ConclusionContext]
    evidence_gaps: list[str]
    unresolved_contradictions: list[uuid.UUID]
    human_review_states: list[uuid.UUID]
    completion_assessment: ResearchCompletionAssessment
    latest_structured_synthesis_record_id: uuid.UUID | None = None
    latest_structured_synthesis_created_at: datetime | None = None
    method_version: str
    schema_version: str
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime


class NarrativeFinding(BaseModel):
    """Provider-proposed material finding with canonical references."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    finding_key: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1)
    claim_ids: list[uuid.UUID] = Field(default_factory=list)
    conclusion_ids: list[uuid.UUID] = Field(default_factory=list)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    validation_summary: str = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_grounding_shape(self) -> NarrativeFinding:
        if not self.claim_ids and not self.conclusion_ids:
            raise ValueError("material findings require at least one Claim or Conclusion reference")
        return self


class NarrativeProposal(BaseModel):
    """Strict structured proposal rendered deterministically by Darwin."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1)
    executive_summary: str = Field(min_length=1)
    executive_summary_claim_ids: list[uuid.UUID] = Field(default_factory=list)
    executive_summary_conclusion_ids: list[uuid.UUID] = Field(default_factory=list)
    research_question: str = Field(min_length=1)
    scope_method: str = Field(min_length=1)
    key_findings: list[NarrativeFinding] = Field(default_factory=list)
    claim_based_findings: list[NarrativeFinding] = Field(default_factory=list)
    contradictions: list[NarrativeFinding] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    conclusions: list[NarrativeFinding] = Field(default_factory=list)
    completion_assessment: ResearchCompletionAssessment
    next_research_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_executive_summary_grounding(self) -> NarrativeProposal:
        if self.executive_summary and not (
            self.executive_summary_claim_ids or self.executive_summary_conclusion_ids
        ):
            raise ValueError("executive summary requires canonical Claim or Conclusion references")
        return self

    def all_findings(self) -> list[tuple[str, NarrativeFinding]]:
        findings: list[tuple[str, NarrativeFinding]] = []
        for section, section_findings in [
            ("key_findings", self.key_findings),
            ("claim_based_findings", self.claim_based_findings),
            ("contradictions", self.contradictions),
            ("conclusions", self.conclusions),
        ]:
            findings.extend((section, finding) for finding in section_findings)
        return findings


class ProviderNarrativeSynthesisResult(BaseModel):
    """Provider envelope around a structured narrative proposal."""

    provider_id: str
    provider_model: str | None = None
    provider_response_id: str | None = None
    proposal: NarrativeProposal | dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    usage_metadata: dict[str, Any] = Field(default_factory=dict)
    cost_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class NarrativeProposalRead(BaseModel):
    """Read model for persisted narrative proposal state."""

    id: uuid.UUID
    synthesis_request_id: uuid.UUID
    research_run_id: uuid.UUID
    provider_id: str
    provider_model: str | None
    status: NarrativeSynthesisProposalStatus
    proposal: NarrativeProposal
    referenced_claim_ids: list[uuid.UUID]
    referenced_conclusion_ids: list[uuid.UUID]
    referenced_evidence_ids: list[uuid.UUID]
    validation_result: dict[str, Any]
    warnings: list[str]
    errors: list[str]
    rejection_reason: str | None
    published_at: datetime | None
    created_at: datetime


class NarrativeSynthesisResult(BaseModel):
    """Result returned after narrative proposal persistence."""

    synthesis_request_id: uuid.UUID
    proposal_id: uuid.UUID | None
    provider_id: str
    provider_model: str | None
    status: NarrativeSynthesisProposalStatus | None
    warnings: list[str]
    errors: list[str]


class NarrativePublicationResult(BaseModel):
    """Result returned after explicit report publication."""

    proposal_id: uuid.UUID
    report_id: uuid.UUID
    status: NarrativeSynthesisProposalStatus
    artifact_path: str
    artifact_sha256: str
    artifact_size_bytes: int


class NarrativeRejectionResult(BaseModel):
    """Result returned after explicit proposal rejection."""

    proposal_id: uuid.UUID
    status: NarrativeSynthesisProposalStatus
    rejection_reason: str
