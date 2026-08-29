import uuid

from sqlalchemy import inspect

from darwin.db import Base
from darwin.db.models import (
    Claim,
    ClaimEvidence,
    ClaimEvidenceRelation,
    ClaimStatus,
    ClaimType,
    Conclusion,
    ConclusionStatus,
    Evidence,
    EvidenceType,
    ResearchRun,
    ResearchRunStatus,
    Source,
    SourceType,
)


def test_model_imports() -> None:
    assert ResearchRun.__tablename__ == "research_runs"
    assert Source.__tablename__ == "sources"
    assert Evidence.__tablename__ == "evidence"
    assert Claim.__tablename__ == "claims"
    assert ClaimEvidence.__tablename__ == "claim_evidence"
    assert Conclusion.__tablename__ == "conclusions"


def test_metadata_contains_expected_tables() -> None:
    assert {
        "research_runs",
        "sources",
        "evidence",
        "claims",
        "claim_evidence",
        "conclusions",
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
    assert ClaimStatus.PROPOSED.value == "PROPOSED"
    assert ClaimType.PROPOSITION.value == "PROPOSITION"
    assert SourceType.WEB_PAGE.value == "WEB_PAGE"
    assert EvidenceType.EXCERPT.value == "EXCERPT"
    assert ConclusionStatus.DRAFT.value == "DRAFT"


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

    assert evidence.source is source
    assert evidence.research_run is research_run
    assert claim.research_run is research_run
    assert claim_evidence.claim is claim
    assert claim_evidence.evidence is evidence
    assert claim_evidence.relation is ClaimEvidenceRelation.SUPPORTS
    assert conclusion.research_run is research_run


def test_confidence_is_nullable_and_range_constrained() -> None:
    claim_constraints = {constraint.name for constraint in Claim.__table__.constraints}
    conclusion_constraints = {constraint.name for constraint in Conclusion.__table__.constraints}

    assert Claim.__table__.c.confidence.nullable is True
    assert Conclusion.__table__.c.confidence.nullable is True
    assert "ck_claims_confidence_range" in claim_constraints
    assert "ck_conclusions_confidence_range" in conclusion_constraints
