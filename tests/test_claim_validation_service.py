import uuid

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from darwin.db import Base
from darwin.db.models import (
    ClaimEvidenceRelation,
    ClaimHumanValidation,
    ClaimValidationEvaluation,
    ClaimValidationReasonCode,
    ClaimValidationState,
    Claim,
    EvidenceType,
    SourceLineageType,
    SourceType,
)
from darwin.research import InvalidResearchRelationship, ResearchService
from darwin.validation import ClaimValidationService


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_claim(session_factory):
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Validation test",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        claim = service.register_claim(
            research_run_id=research_run.id,
            statement="Darwin validates structure, not truth.",
        )
        session.commit()
        return claim.id


def add_linked_evidence(
    session,
    *,
    claim_id,
    relation: ClaimEvidenceRelation,
    canonical_locator: str,
    origin_source_id=None,
    source_lineage_type=None,
):
    research = ResearchService(session)
    claim = session.get(Claim, claim_id)
    source = research.register_source(
        source_type=SourceType.WEB_PAGE,
        canonical_locator=canonical_locator,
        origin_source_id=origin_source_id,
        source_lineage_type=source_lineage_type,
    )
    evidence = research.register_evidence(
        research_run_id=claim.research_run_id,
        source_id=source.id,
        evidence_type=EvidenceType.EXCERPT,
        statement=f"Evidence from {canonical_locator}",
    )
    return research.link_claim_evidence(
        claim_id=claim_id,
        evidence_id=evidence.id,
        relation=relation,
    )


def assert_reason(result, reason: ClaimValidationReasonCode) -> None:
    assert reason in result.reason_codes


def test_no_evidence_is_insufficient(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        result = ClaimValidationService(session).evaluate_claim(claim_id)

        assert result.validation_state is ClaimValidationState.INSUFFICIENT_EVIDENCE
        assert result.supporting_evidence_count == 0
        assert result.distinct_source_count == 0
        assert_reason(result, ClaimValidationReasonCode.NO_EVIDENCE)


def test_single_support_is_supported(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        add_linked_evidence(
            session,
            claim_id=claim_id,
            relation=ClaimEvidenceRelation.SUPPORTS,
            canonical_locator="https://example.com/support",
        )

        result = ClaimValidationService(session).evaluate_claim(claim_id)

        assert result.validation_state is ClaimValidationState.SUPPORTED
        assert result.supporting_evidence_count == 1
        assert result.independent_supporting_source_count == 1
        assert result.independent_corroboration_exists is False
        assert_reason(result, ClaimValidationReasonCode.SINGLE_SUPPORTING_SOURCE)


def test_independent_corroboration_requires_two_independent_sources(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        add_linked_evidence(
            session,
            claim_id=claim_id,
            relation=ClaimEvidenceRelation.SUPPORTS,
            canonical_locator="https://example.com/support-a",
        )
        add_linked_evidence(
            session,
            claim_id=claim_id,
            relation=ClaimEvidenceRelation.SUPPORTS,
            canonical_locator="https://independent.example/support-b",
        )

        result = ClaimValidationService(session).evaluate_claim(claim_id)

        assert result.validation_state is ClaimValidationState.CORROBORATED
        assert result.supporting_evidence_count == 2
        assert result.distinct_source_count == 2
        assert result.independent_supporting_source_count == 2
        assert result.independent_corroboration_exists is True
        assert_reason(result, ClaimValidationReasonCode.MULTIPLE_INDEPENDENT_SUPPORTING_SOURCES)


def test_derived_sources_do_not_create_false_corroboration(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        research = ResearchService(session)
        origin = research.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://origin.example/report",
        )
        origin_evidence = research.register_evidence(
            research_run_id=session.get(Claim, claim_id).research_run_id,
            source_id=origin.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Origin report.",
        )
        research.link_claim_evidence(
            claim_id=claim_id,
            evidence_id=origin_evidence.id,
            relation=ClaimEvidenceRelation.SUPPORTS,
        )
        add_linked_evidence(
            session,
            claim_id=claim_id,
            relation=ClaimEvidenceRelation.SUPPORTS,
            canonical_locator="https://republisher.example/report",
            origin_source_id=origin.id,
            source_lineage_type=SourceLineageType.REPUBLISHED_FROM,
        )

        result = ClaimValidationService(session).evaluate_claim(claim_id)

        assert result.validation_state is ClaimValidationState.SUPPORTED
        assert result.supporting_evidence_count == 2
        assert result.distinct_source_count == 2
        assert result.independent_supporting_source_count == 1
        assert result.independent_corroboration_exists is False
        assert_reason(result, ClaimValidationReasonCode.DERIVED_SOURCES_NOT_COUNTED_AS_INDEPENDENT)


def test_support_plus_contradiction_is_contested(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        add_linked_evidence(
            session,
            claim_id=claim_id,
            relation=ClaimEvidenceRelation.SUPPORTS,
            canonical_locator="https://example.com/support",
        )
        add_linked_evidence(
            session,
            claim_id=claim_id,
            relation=ClaimEvidenceRelation.CONTRADICTS,
            canonical_locator="https://example.com/contradiction",
        )

        result = ClaimValidationService(session).evaluate_claim(claim_id)

        assert result.validation_state is ClaimValidationState.CONTESTED
        assert result.contradiction_exists is True
        assert result.contradicting_evidence_count == 1
        assert_reason(result, ClaimValidationReasonCode.CONTRADICTORY_EVIDENCE_PRESENT)


def test_only_contradiction_is_contradicted(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        add_linked_evidence(
            session,
            claim_id=claim_id,
            relation=ClaimEvidenceRelation.CONTRADICTS,
            canonical_locator="https://example.com/contradiction",
        )

        result = ClaimValidationService(session).evaluate_claim(claim_id)

        assert result.validation_state is ClaimValidationState.CONTRADICTED
        assert result.contradicting_evidence_count == 1
        assert_reason(result, ClaimValidationReasonCode.ONLY_CONTRADICTING_EVIDENCE)


def test_contextual_evidence_alone_is_not_support(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        add_linked_evidence(
            session,
            claim_id=claim_id,
            relation=ClaimEvidenceRelation.CONTEXTUALIZES,
            canonical_locator="https://example.com/context",
        )

        result = ClaimValidationService(session).evaluate_claim(claim_id)

        assert result.validation_state is ClaimValidationState.INSUFFICIENT_EVIDENCE
        assert result.contextual_evidence_count == 1
        assert result.supporting_evidence_count == 0
        assert_reason(result, ClaimValidationReasonCode.ONLY_CONTEXTUAL_EVIDENCE)


def test_human_review_request_is_explicit_and_audited(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        result = ClaimValidationService(session).request_human_review(
            claim_id,
            validator_label="review-board",
            note="Ambiguity requires human review.",
        )

        event_count = session.scalar(select(func.count()).select_from(ClaimHumanValidation))

        assert result.validation_state is ClaimValidationState.HUMAN_REVIEW_PENDING
        assert result.human_review_requested is True
        assert event_count == 1
        assert_reason(result, ClaimValidationReasonCode.HUMAN_REVIEW_REQUIRED)


def test_human_validation_is_explicit_and_history_is_auditable(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        service = ClaimValidationService(session, method_version="validation-test")
        service.evaluate_claim(claim_id)
        result = service.record_human_validation(
            claim_id,
            validator_label="domain-reviewer",
            note="Validated after manual review.",
        )
        service.evaluate_claim(claim_id)

        evaluation_count = session.scalar(
            select(func.count()).select_from(ClaimValidationEvaluation)
        )
        event_count = session.scalar(select(func.count()).select_from(ClaimHumanValidation))

        assert result.validation_state is ClaimValidationState.HUMAN_VALIDATED
        assert result.human_validation_present is True
        assert result.validation_method_version == "validation-test"
        assert evaluation_count == 3
        assert event_count == 1
        assert_reason(result, ClaimValidationReasonCode.HUMAN_VALIDATION_PRESENT)


def test_validation_records_method_version(session_factory) -> None:
    claim_id = create_claim(session_factory)

    with session_factory() as session:
        result = ClaimValidationService(
            session,
            method_version="claim-validation-test",
        ).evaluate_claim(claim_id)

        assert result.validation_method_version == "claim-validation-test"


def test_failed_validation_does_not_persist_partial_history(session_factory) -> None:
    missing_claim_id = uuid.uuid4()

    with pytest.raises(InvalidResearchRelationship):
        with session_factory.begin() as session:
            ClaimValidationService(session).evaluate_claim(missing_claim_id)

    with session_factory() as session:
        evaluation_count = session.scalar(
            select(func.count()).select_from(ClaimValidationEvaluation)
        )
        event_count = session.scalar(select(func.count()).select_from(ClaimHumanValidation))

    assert evaluation_count == 0
    assert event_count == 0
