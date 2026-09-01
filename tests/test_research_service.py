import uuid
from datetime import UTC, datetime

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


def test_list_research_runs_returns_ordered_summaries_with_counts_and_limit(
    session_factory,
) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        first_run = service.create_research_run(
            title="Older run",
            public_id="RUN-OLD",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        second_run = service.create_research_run(
            title="Newer run",
            public_id="RUN-NEW",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/list-runs",
        )
        first_evidence = service.register_evidence(
            research_run_id=first_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="First item of list evidence.",
        )
        service.register_evidence(
            research_run_id=first_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.SUMMARY,
            statement="Second item of list evidence.",
        )
        claim = service.register_claim(
            research_run_id=first_run.id,
            statement="Listing summaries preserve traceability counts.",
        )
        service.link_claim_evidence(
            claim_id=claim.id,
            evidence_id=first_evidence.id,
            relation=ClaimEvidenceRelation.SUPPORTS,
        )
        service.register_conclusion(
            research_run_id=first_run.id,
            statement="The summary includes conclusion counts.",
        )
        first_run.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
        second_run.updated_at = datetime(2026, 1, 2, tzinfo=UTC)
        session.flush()

        summaries = service.list_research_runs(limit=2)
        limited = service.list_research_runs(limit=1)

        assert [summary.public_id for summary in summaries] == ["RUN-NEW", "RUN-OLD"]
        assert [summary.public_id for summary in limited] == ["RUN-NEW"]
        older_summary = summaries[1]
        assert older_summary.id == first_run.id
        assert older_summary.status is ResearchRunStatus.PENDING
        assert older_summary.source_count == 1
        assert older_summary.evidence_count == 2
        assert older_summary.claim_count == 1
        assert older_summary.conclusion_count == 1


def test_list_research_runs_filters_status_and_validates_input(session_factory) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        pending_run = service.create_research_run(
            title="Pending run",
            public_id="RUN-PENDING",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        completed_run = service.create_research_run(
            title="Completed run",
            public_id="RUN-COMPLETED",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        service.mark_started(completed_run.id)
        service.mark_completed(completed_run.id)
        run_count_before = session.scalar(select(func.count()).select_from(ResearchRun))

        completed = service.list_research_runs(status="completed")
        pending = service.list_research_runs(status=ResearchRunStatus.PENDING)
        in_progress = service.list_research_runs(status="in-progress")
        run_count_after = session.scalar(select(func.count()).select_from(ResearchRun))

        assert [summary.public_id for summary in completed] == ["RUN-COMPLETED"]
        assert [summary.public_id for summary in pending] == [pending_run.public_id]
        assert in_progress == []
        assert run_count_after == run_count_before
        with pytest.raises(ValueError, match="Unsupported research run status"):
            service.list_research_runs(status="unknown")
        with pytest.raises(ValueError, match="between 1 and 200"):
            service.list_research_runs(limit=0)


def test_export_research_record_returns_envelope_counts_and_does_not_mutate(
    session_factory,
) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Export test",
            public_id="rrn_export",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/export",
        )
        evidence = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Exported evidence remains traceable.",
        )
        claim = service.register_claim(
            research_run_id=research_run.id,
            statement="Research exports are traceable.",
        )
        service.link_claim_evidence(
            claim_id=claim.id,
            evidence_id=evidence.id,
            relation=ClaimEvidenceRelation.SUPPORTS,
        )
        service.register_conclusion(
            research_run_id=research_run.id,
            statement="The export envelope includes conclusions.",
            status=ConclusionStatus.DRAFT,
        )
        run_count_before = session.scalar(select(func.count()).select_from(ResearchRun))

        exported = service.export_research_record("rrn_export")
        run_count_after = session.scalar(select(func.count()).select_from(ResearchRun))

        assert exported.schema_version == "research-record-export.v1"
        assert exported.exported_at is not None
        assert exported.research_run.id == research_run.id
        assert exported.sources[0].id == source.id
        assert exported.evidence[0].id == evidence.id
        assert exported.claims[0].id == claim.id
        assert exported.conclusions[0].research_run_id == research_run.id
        assert exported.summary.source_count == 1
        assert exported.summary.evidence_count == 1
        assert exported.summary.claim_count == 1
        assert exported.summary.claim_evidence_count == 1
        assert exported.summary.conclusion_count == 1
        assert run_count_after == run_count_before


def test_research_record_integrity_report_identifies_healthy_record_without_mutation(
    session_factory,
) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Integrity healthy test",
            public_id="rrn_integrity_healthy",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/integrity-healthy",
        )
        evidence = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Integrity report evidence is linked.",
        )
        claim = service.register_claim(
            research_run_id=research_run.id,
            statement="Integrity report can identify healthy records.",
        )
        service.link_claim_evidence(
            claim_id=claim.id,
            evidence_id=evidence.id,
            relation=ClaimEvidenceRelation.SUPPORTS,
        )
        service.register_conclusion(
            research_run_id=research_run.id,
            statement="The record is structurally complete.",
            status=ConclusionStatus.DRAFT,
        )
        run_count_before = session.scalar(select(func.count()).select_from(ResearchRun))

        report = service.report_research_record_integrity("rrn_integrity_healthy")
        run_count_after = session.scalar(select(func.count()).select_from(ResearchRun))

        assert report.schema_version == "research-record-integrity-report.v1"
        assert report.healthy is True
        assert report.issues == []
        assert report.summary.source_count == 1
        assert report.summary.evidence_count == 1
        assert report.summary.claim_count == 1
        assert report.summary.claim_evidence_count == 1
        assert report.summary.conclusion_count == 1
        assert report.summary.issue_count == 0
        assert run_count_after == run_count_before


def test_research_record_integrity_report_flags_traceability_gaps_and_filters(
    session_factory,
) -> None:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Integrity gap test",
            public_id="rrn_integrity_gaps",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/integrity-gaps",
        )
        service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Unlinked evidence should be visible.",
        )
        service.register_claim(
            research_run_id=research_run.id,
            statement="Unlinked claim should be visible.",
        )

        report = service.report_research_record_integrity(
            "rrn_integrity_gaps",
            min_supporting_sources=2,
        )
        warnings = service.report_research_record_integrity(
            "rrn_integrity_gaps",
            min_supporting_sources=2,
            severity="warning",
        )

        assert report.healthy is False
        assert [issue.code for issue in report.issues] == [
            "CLAIM_WITHOUT_EVIDENCE",
            "EVIDENCE_WITHOUT_CLAIM",
            "LOW_SUPPORTING_SOURCE_DIVERSITY",
            "NO_CONCLUSIONS",
        ]
        assert report.summary.error_count == 1
        assert report.summary.warning_count == 2
        assert report.summary.info_count == 1
        assert [issue.severity for issue in warnings.issues] == ["WARNING", "WARNING"]
        assert [issue.code for issue in warnings.issues] == [
            "EVIDENCE_WITHOUT_CLAIM",
            "LOW_SUPPORTING_SOURCE_DIVERSITY",
        ]
        with pytest.raises(ValueError, match="Unsupported integrity severity"):
            service.report_research_record_integrity("rrn_integrity_gaps", severity="critical")
        with pytest.raises(ValueError, match="Minimum supporting sources"):
            service.report_research_record_integrity("rrn_integrity_gaps", min_supporting_sources=-1)


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
