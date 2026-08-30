import uuid

from sqlalchemy import inspect

from darwin.db import Base
from darwin.db.models import (
    AssistedClaimConstructionRequest,
    AssistedClaimConstructionRequestStatus,
    AssistedEvidenceExtractionRequest,
    AssistedExtractionRequestStatus,
    Claim,
    ClaimCandidateAcceptanceMode,
    ClaimCandidateEvidence,
    ClaimCandidateProposal,
    ClaimCandidateStatus,
    ClaimConstructionEvidence,
    ClaimConstructionMethod,
    ClaimConstructionRecord,
    ClaimEvidence,
    ClaimEvidenceRelation,
    ClaimHumanValidation,
    ClaimStatus,
    ClaimType,
    ClaimValidationEvaluation,
    ClaimValidationReasonCode,
    ClaimValidationState,
    Conclusion,
    ConclusionClaim,
    ConclusionClaimRelation,
    ConclusionStatus,
    Evidence,
    EvidenceCandidateAcceptanceMode,
    EvidenceCandidateProposal,
    EvidenceCandidateStatus,
    EvidenceType,
    HumanValidationType,
    NarrativeResearchReport,
    NarrativeSynthesisFinding,
    NarrativeSynthesisProposal,
    NarrativeSynthesisProposalStatus,
    NarrativeSynthesisRequest,
    NarrativeSynthesisRequestStatus,
    ResearchCompletionAssessment,
    ResearchFraming,
    ResearchPlanItem,
    ResearchPlanItemStatus,
    ResearchPlanPriority,
    ResearchRun,
    ResearchRunStatus,
    ResearchSynthesisRecord,
    Source,
    SourceLineageType,
    SourceType,
)


def test_model_imports() -> None:
    assert ResearchRun.__tablename__ == "research_runs"
    assert Source.__tablename__ == "sources"
    assert Evidence.__tablename__ == "evidence"
    assert Claim.__tablename__ == "claims"
    assert ClaimEvidence.__tablename__ == "claim_evidence"
    assert Conclusion.__tablename__ == "conclusions"
    assert ClaimConstructionRecord.__tablename__ == "claim_construction_records"
    assert ClaimConstructionEvidence.__tablename__ == "claim_construction_evidence"
    assert ConclusionClaim.__tablename__ == "conclusion_claims"
    assert AssistedEvidenceExtractionRequest.__tablename__ == "assisted_evidence_extraction_requests"
    assert EvidenceCandidateProposal.__tablename__ == "evidence_candidate_proposals"
    assert ClaimValidationEvaluation.__tablename__ == "claim_validation_evaluations"
    assert ClaimHumanValidation.__tablename__ == "claim_human_validations"
    assert ResearchFraming.__tablename__ == "research_framings"
    assert ResearchPlanItem.__tablename__ == "research_plan_items"
    assert ResearchSynthesisRecord.__tablename__ == "research_synthesis_records"
    assert AssistedClaimConstructionRequest.__tablename__ == "assisted_claim_construction_requests"
    assert ClaimCandidateProposal.__tablename__ == "claim_candidate_proposals"
    assert ClaimCandidateEvidence.__tablename__ == "claim_candidate_evidence"
    assert NarrativeSynthesisRequest.__tablename__ == "narrative_synthesis_requests"
    assert NarrativeSynthesisProposal.__tablename__ == "narrative_synthesis_proposals"
    assert NarrativeSynthesisFinding.__tablename__ == "narrative_synthesis_findings"
    assert NarrativeResearchReport.__tablename__ == "narrative_research_reports"


def test_metadata_contains_expected_tables() -> None:
    assert {
        "research_runs",
        "sources",
        "evidence",
        "claims",
        "claim_evidence",
        "conclusions",
        "claim_construction_records",
        "claim_construction_evidence",
        "conclusion_claims",
        "claim_validation_evaluations",
        "claim_human_validations",
        "research_framings",
        "research_plan_items",
        "research_synthesis_records",
        "assisted_evidence_extraction_requests",
        "evidence_candidate_proposals",
        "assisted_claim_construction_requests",
        "claim_candidate_proposals",
        "claim_candidate_evidence",
        "narrative_synthesis_requests",
        "narrative_synthesis_proposals",
        "narrative_synthesis_findings",
        "narrative_research_reports",
    }.issubset(Base.metadata.tables)


def test_required_fields_are_not_nullable() -> None:
    expected_required_columns = {
        ResearchRun: {
            "id",
            "public_id",
            "title",
            "status",
            "created_at",
            "updated_at",
            "research_method_version",
            "darwin_version",
            "context",
        },
        Source: {"id", "source_type", "canonical_locator", "retrieved_at", "metadata", "created_at"},
        Evidence: {
            "id",
            "research_run_id",
            "source_id",
            "evidence_type",
            "statement",
            "captured_at",
            "metadata",
        },
        Claim: {"id", "research_run_id", "statement", "claim_type", "status", "created_at", "updated_at"},
        ClaimEvidence: {"id", "claim_id", "evidence_id", "relation", "created_at"},
        Conclusion: {"id", "research_run_id", "statement", "status", "created_at", "updated_at"},
        ClaimConstructionRecord: {
            "id",
            "research_run_id",
            "claim_id",
            "construction_method",
            "construction_method_version",
            "claim_statement",
            "evidence_count",
            "warning_count",
            "warnings",
            "metadata",
            "created_at",
        },
        ClaimConstructionEvidence: {
            "id",
            "claim_construction_record_id",
            "evidence_id",
            "relation",
            "created_at",
        },
        ConclusionClaim: {"id", "conclusion_id", "claim_id", "relation", "created_at", "metadata"},
        ClaimValidationEvaluation: {
            "id",
            "claim_id",
            "validation_state",
            "supporting_evidence_count",
            "contradicting_evidence_count",
            "contextual_evidence_count",
            "distinct_source_count",
            "independent_supporting_source_count",
            "independent_contradicting_source_count",
            "independent_corroboration_exists",
            "contradiction_exists",
            "human_review_requested",
            "human_validation_present",
            "reason_codes",
            "evaluated_at",
            "validation_method_version",
        },
        ClaimHumanValidation: {"id", "claim_id", "validation_type", "created_at"},
        ResearchFraming: {
            "id",
            "research_run_id",
            "original_question",
            "normalized_question",
            "objective",
            "scope",
            "exclusions",
            "key_decision_criteria",
            "assumptions",
            "required_evidence_categories",
            "completion_criteria",
            "metadata",
            "created_at",
        },
        ResearchPlanItem: {
            "id",
            "research_run_id",
            "item_key",
            "requirement",
            "category",
            "priority",
            "is_required",
            "status",
            "created_at",
            "updated_at",
        },
        ResearchSynthesisRecord: {
            "id",
            "research_run_id",
            "research_method_version",
            "completion_assessment",
            "source_count",
            "evidence_count",
            "claim_count",
            "conclusion_count",
            "evidence_gaps",
            "unresolved_contradictions",
            "warnings",
            "payload",
            "created_at",
        },
        AssistedClaimConstructionRequest: {
            "id",
            "research_run_id",
            "research_plan_item_id",
            "evidence_ids",
            "research_objective",
            "construction_instruction",
            "max_candidate_count",
            "provider_id",
            "construction_method_version",
            "schema_version",
            "status",
            "candidate_count",
            "accepted_candidate_count",
            "warning_count",
            "error_count",
            "warnings",
            "errors",
            "request_payload",
            "validation_result",
            "provider_metadata",
            "usage_metadata",
            "cost_metadata",
            "metadata",
            "created_at",
        },
        ClaimCandidateProposal: {
            "id",
            "construction_request_id",
            "research_run_id",
            "research_plan_item_id",
            "candidate_key",
            "proposed_claim_text",
            "proposed_claim_type",
            "qualifiers",
            "assumptions",
            "construction_rationale",
            "status",
            "provider_warnings",
            "validation_result",
            "provider_metadata",
            "created_at",
        },
        ClaimCandidateEvidence: {
            "id",
            "claim_candidate_id",
            "evidence_id",
            "relation",
            "created_at",
        },
        NarrativeSynthesisRequest: {
            "id",
            "research_run_id",
            "report_purpose",
            "intended_audience",
            "requested_report_format",
            "focus_areas",
            "include_sections",
            "exclude_sections",
            "tone_style",
            "provider_id",
            "synthesis_method_version",
            "schema_version",
            "status",
            "proposal_count",
            "warning_count",
            "error_count",
            "warnings",
            "errors",
            "request_payload",
            "context_payload",
            "validation_result",
            "provider_metadata",
            "usage_metadata",
            "cost_metadata",
            "metadata",
            "created_at",
        },
        NarrativeSynthesisProposal: {
            "id",
            "synthesis_request_id",
            "research_run_id",
            "provider_id",
            "synthesis_method_version",
            "schema_version",
            "status",
            "proposal_payload",
            "referenced_claim_ids",
            "referenced_conclusion_ids",
            "referenced_evidence_ids",
            "validation_result",
            "warning_count",
            "error_count",
            "warnings",
            "errors",
            "provider_metadata",
            "created_at",
        },
        NarrativeSynthesisFinding: {
            "id",
            "proposal_id",
            "research_run_id",
            "finding_key",
            "section",
            "text",
            "claim_ids",
            "conclusion_ids",
            "evidence_ids",
            "validation_summary",
            "warnings",
            "created_at",
        },
        NarrativeResearchReport: {
            "id",
            "proposal_id",
            "research_run_id",
            "report_version",
            "artifact_path",
            "artifact_sha256",
            "artifact_size_bytes",
            "generated_at",
            "metadata",
        },
    }

    for model, column_names in expected_required_columns.items():
        columns = {column.name: column for column in inspect(model).columns}
        for column_name in column_names:
            assert columns[column_name].nullable is False


def test_core_enums_are_small_and_explicit() -> None:
    assert ResearchRunStatus.PENDING.value == "PENDING"
    assert ResearchRunStatus.COMPLETED.value == "COMPLETED"
    assert ClaimEvidenceRelation.SUPPORTS.value == "SUPPORTS"
    assert ClaimEvidenceRelation.CONTRADICTS.value == "CONTRADICTS"
    assert ClaimEvidenceRelation.CONTEXTUALIZES.value == "CONTEXTUALIZES"
    assert ClaimEvidenceRelation.RELATED.value == "RELATED"
    assert ClaimConstructionMethod.MANUAL_EXPLICIT.value == "MANUAL_EXPLICIT"
    assert ClaimStatus.PROPOSED.value == "PROPOSED"
    assert ClaimType.PROPOSITION.value == "PROPOSITION"
    assert SourceType.WEB_PAGE.value == "WEB_PAGE"
    assert SourceLineageType.DERIVED_FROM.value == "DERIVED_FROM"
    assert EvidenceType.EXCERPT.value == "EXCERPT"
    assert ConclusionStatus.DRAFT.value == "DRAFT"
    assert ConclusionClaimRelation.SUPPORTS_CONCLUSION.value == "SUPPORTS_CONCLUSION"
    assert ClaimValidationState.CORROBORATED.value == "CORROBORATED"
    assert ClaimValidationReasonCode.NO_EVIDENCE.value == "NO_EVIDENCE"
    assert HumanValidationType.VALIDATED.value == "VALIDATED"
    assert ResearchPlanItemStatus.SATISFIED.value == "SATISFIED"
    assert ResearchPlanPriority.HIGH.value == "HIGH"
    assert ResearchCompletionAssessment.COMPLETE.value == "COMPLETE"
    assert AssistedClaimConstructionRequestStatus.COMPLETED.value == "COMPLETED"
    assert ClaimCandidateStatus.REJECTED_INVALID_PROVENANCE.value == "REJECTED_INVALID_PROVENANCE"
    assert ClaimCandidateAcceptanceMode.MANUAL.value == "MANUAL"
    assert NarrativeSynthesisRequestStatus.COMPLETED.value == "COMPLETED"
    assert NarrativeSynthesisProposalStatus.PUBLISHED.value == "PUBLISHED"


def test_relationships_preserve_research_provenance() -> None:
    research_run = ResearchRun(
        id=uuid.uuid4(),
        public_id="rrn_test",
        title="What is the status of Darwin?",
        status=ResearchRunStatus.IN_PROGRESS,
        research_method_version="0.1.0",
        darwin_version="0.1.0",
    )
    source = Source(
        id=uuid.uuid4(),
        source_type=SourceType.WEB_PAGE,
        canonical_locator="https://example.com/source",
    )
    evidence = Evidence(
        id=uuid.uuid4(),
        research_run=research_run,
        source=source,
        evidence_type=EvidenceType.EXCERPT,
        statement="Darwin has a Phase 1.8B data model foundation.",
        source_locator="section-1",
    )
    claim = Claim(
        id=uuid.uuid4(),
        research_run=research_run,
        statement="Darwin can store traceable research evidence.",
        claim_type=ClaimType.PROPOSITION,
        status=ClaimStatus.UNDER_REVIEW,
    )
    claim_evidence = ClaimEvidence(
        id=uuid.uuid4(),
        claim=claim,
        evidence=evidence,
        relation=ClaimEvidenceRelation.SUPPORTS,
    )
    conclusion = Conclusion(
        id=uuid.uuid4(),
        research_run=research_run,
        statement="The foundation supports provenance-preserving storage.",
        status=ConclusionStatus.DRAFT,
    )
    construction_record = ClaimConstructionRecord(
        research_run=research_run,
        claim=claim,
        construction_method=ClaimConstructionMethod.MANUAL_EXPLICIT,
        construction_method_version="manual-explicit-test",
        claim_statement=claim.statement,
        evidence_count=1,
    )
    construction_evidence = ClaimConstructionEvidence(
        construction_record=construction_record,
        evidence=evidence,
        relation=ClaimEvidenceRelation.SUPPORTS,
    )
    conclusion_claim = ConclusionClaim(
        conclusion=conclusion,
        claim=claim,
        relation=ConclusionClaimRelation.SUPPORTS_CONCLUSION,
    )

    assert evidence.source is source
    assert evidence.research_run is research_run
    assert claim.research_run is research_run
    assert claim_evidence.claim is claim
    assert claim_evidence.evidence is evidence
    assert claim_evidence.relation is ClaimEvidenceRelation.SUPPORTS
    assert conclusion.research_run is research_run
    assert construction_record.claim is claim
    assert construction_evidence.evidence is evidence
    assert conclusion_claim.conclusion is conclusion
    assert conclusion_claim.claim is claim


def test_confidence_is_nullable_and_range_constrained() -> None:
    claim_constraints = {constraint.name for constraint in Claim.__table__.constraints}
    conclusion_constraints = {constraint.name for constraint in Conclusion.__table__.constraints}

    assert Claim.__table__.c.confidence.nullable is True
    assert Conclusion.__table__.c.confidence.nullable is True
    assert "ck_claims_confidence_range" in claim_constraints
    assert "ck_conclusions_confidence_range" in conclusion_constraints
