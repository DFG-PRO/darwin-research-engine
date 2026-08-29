import uuid

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from darwin.db import Base
from darwin.db.models import (
    ClaimEvidence,
    ClaimEvidenceRelation,
    ClaimStatus,
    ClaimType,
    ConclusionStatus,
    EvidenceType,
    ResearchRun,
    ResearchRunStatus,
    SourceType,
)
from darwin.research import (
    DuplicateResearchRelationship,
    InvalidResearchRelationship,
    InvalidResearchRunTransition,
    ResearchService,
    ResearchRunNotFound,
)


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_research_run_creation_and_retrieval(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Can Darwin persist research?",
            public_id="rrn_service_test",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )

        assert research_run.status is ResearchRunStatus.PENDING
        assert service.get_research_run(research_run.id) is research_run
        assert service.get_research_run("rrn_service_test") is research_run


def test_research_run_lifecycle_transitions(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Lifecycle test",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )

        service.mark_started(research_run.id)
        assert research_run.status is ResearchRunStatus.IN_PROGRESS

        service.mark_completed(research_run.id)
        assert research_run.status is ResearchRunStatus.COMPLETED
        assert research_run.completed_at is not None


def test_invalid_research_run_lifecycle_transition(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Invalid transition test",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )

        with pytest.raises(InvalidResearchRunTransition):
            service.mark_completed(research_run.id)


def test_research_run_failure_behavior(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Failure test",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )

        service.mark_failed(research_run.id)

        assert research_run.status is ResearchRunStatus.FAILED
        assert research_run.completed_at is not None


def test_missing_research_run_raises(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)

        with pytest.raises(ResearchRunNotFound):
            service.get_research_run(uuid.uuid4())


def test_source_registration_reuses_deterministic_duplicates(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        first = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/a",
            content_fingerprint="sha256:abc",
        )
        second = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/other-copy",
            content_fingerprint="sha256:abc",
        )
        third = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/a",
        )
        fourth = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/b",
        )

        assert second is first
        assert third is first
        assert fourth.id != first.id


def test_evidence_registration_requires_research_run_and_source(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Evidence test",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.DOCUMENT,
            canonical_locator="doc://foundation",
        )

        evidence = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Evidence remains linked to source and run.",
        )

        assert evidence.research_run is research_run
        assert evidence.source is source

        with pytest.raises(InvalidResearchRelationship):
            service.register_evidence(
                research_run_id=research_run.id,
                source_id=uuid.uuid4(),
                evidence_type=EvidenceType.EXCERPT,
                statement="Missing source",
            )

        with pytest.raises(InvalidResearchRelationship):
            service.register_evidence(
                research_run_id=uuid.uuid4(),
                source_id=source.id,
                evidence_type=EvidenceType.EXCERPT,
                statement="Missing run",
            )


def test_claim_registration_and_research_run_link(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Claim test",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )

        claim = service.register_claim(
            research_run_id=research_run.id,
            statement="Claims are explicit propositions.",
            claim_type=ClaimType.PROPOSITION,
            status=ClaimStatus.UNDER_REVIEW,
            confidence=None,
        )

        assert claim.research_run is research_run
        assert claim.confidence is None


def test_claim_evidence_relationships_and_duplicate_protection(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Claim evidence test",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/evidence",
        )
        evidence = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="This evidence supports a claim.",
        )
        claim = service.register_claim(
            research_run_id=research_run.id,
            statement="The relationship is explicit.",
        )

        supports = service.link_claim_evidence(
            claim_id=claim.id,
            evidence_id=evidence.id,
            relation=ClaimEvidenceRelation.SUPPORTS,
        )

        assert supports.relation is ClaimEvidenceRelation.SUPPORTS

        with pytest.raises(DuplicateResearchRelationship):
            service.link_claim_evidence(
                claim_id=claim.id,
                evidence_id=evidence.id,
                relation=ClaimEvidenceRelation.CONTRADICTS,
            )


def test_claim_evidence_rejects_cross_run_relationship(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        first_run = service.create_research_run(
            title="First run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        second_run = service.create_research_run(
            title="Second run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/cross-run",
        )
        evidence = service.register_evidence(
            research_run_id=second_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Evidence belongs to another run.",
        )
        claim = service.register_claim(
            research_run_id=first_run.id,
            statement="This claim belongs to the first run.",
        )

        with pytest.raises(InvalidResearchRelationship):
            service.link_claim_evidence(
                claim_id=claim.id,
                evidence_id=evidence.id,
                relation=ClaimEvidenceRelation.CONTRADICTS,
            )


def test_conclusion_registration_and_research_run_link(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Conclusion test",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )

        conclusion = service.register_conclusion(
            research_run_id=research_run.id,
            statement="Conclusions are persisted explicitly.",
            status=ConclusionStatus.DRAFT,
        )

        assert conclusion.research_run is research_run


def test_research_record_retrieval_preserves_traceability(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Retrieval test",
            public_id="rrn_traceability",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/traceability",
        )
        evidence = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Evidence has a source.",
        )
        claim = service.register_claim(
            research_run_id=research_run.id,
            statement="Traceability is preserved.",
        )
        link = service.link_claim_evidence(
            claim_id=claim.id,
            evidence_id=evidence.id,
            relation=ClaimEvidenceRelation.SUPPORTS,
        )
        conclusion = service.register_conclusion(
            research_run_id=research_run.id,
            statement="The record can be assembled.",
            status=ConclusionStatus.DRAFT,
        )

        record = service.get_research_record("rrn_traceability")

        assert record.research_run.id == research_run.id
        assert record.sources[0].id == source.id
        assert record.evidence[0].source_id == source.id
        assert record.evidence[0].research_run_id == research_run.id
        assert record.claims[0].id == claim.id
        assert record.claim_evidence[0].id == link.id
        assert record.claim_evidence[0].claim_id == claim.id
        assert record.claim_evidence[0].evidence_id == evidence.id
        assert record.conclusions[0].id == conclusion.id


def test_failed_transaction_does_not_leave_partial_research_run(session_factory) -> None:
    with pytest.raises(InvalidResearchRelationship):
        with session_factory.begin() as session:
            service = ResearchService(session)
            research_run = service.create_research_run(
                title="Rollback test",
                research_method_version="0.1.0",
                darwin_version="0.1.0",
            )
            service.register_evidence(
                research_run_id=research_run.id,
                source_id=uuid.uuid4(),
                evidence_type=EvidenceType.EXCERPT,
                statement="This write should fail before commit.",
            )

    with session_factory() as session:
        persisted_runs = session.scalar(select(func.count()).select_from(ResearchRun))
        persisted_links = session.scalar(select(func.count()).select_from(ClaimEvidence))

    assert persisted_runs == 0
    assert persisted_links == 0
