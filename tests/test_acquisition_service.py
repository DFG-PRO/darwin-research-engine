from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import event, func, select
from sqlalchemy.orm import sessionmaker

from darwin.acquisition import (
    AcquisitionProviderError,
    AcquisitionProviderTimeout,
    AcquisitionRequest,
    AcquisitionService,
    FakeResearchProvider,
    ProviderSearchResult,
    ProviderSourceCandidate,
)
from darwin.acquisition.normalization import normalize_locator
from darwin.db.models import (
    AcquisitionStatus,
    Claim,
    Evidence,
    ResearchAcquisitionRequest,
    ResearchRun,
    ResearchRunStatus,
    Source,
    SourceCandidate,
    SourceCandidateRegistrationStatus,
    SourceType,
)
from darwin.research import ResearchService


@pytest.fixture()
def research_run(session_factory: sessionmaker) -> ResearchRun:
    with session_factory() as session:
        research_run = ResearchService(session).create_research_run(
            title="Acquisition test run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        session.commit()
        return research_run


def test_acquisition_request_validation(research_run: ResearchRun) -> None:
    request = AcquisitionRequest(research_run_id=research_run.id, query=" Darwin sources ")

    assert request.query == "Darwin sources"

    with pytest.raises(ValidationError):
        AcquisitionRequest(research_run_id=research_run.id, query=" ")

    with pytest.raises(ValidationError):
        AcquisitionRequest(
            research_run_id=research_run.id,
            query="Darwin sources",
            freshness_start="2026-02-01",
            freshness_end="2026-01-01",
        )


def test_successful_acquisition_persists_provenance_and_source_traceability(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    provider = FakeResearchProvider(
        candidates=[
            ProviderSourceCandidate(
                canonical_locator="https://example.com/report?utm_source=newsletter",
                title="Report",
                snippet="Provider snippet is discovery material only.",
                provider_rank=1,
                provider_candidate_id="provider-candidate-1",
                provider_metadata={"safe": True},
            )
        ]
    )

    with session_factory() as session:
        result = AcquisitionService(session, provider).acquire(
            AcquisitionRequest(
                research_run_id=research_run.id,
                query="external source discovery",
                metadata={"request_id": "manual-test"},
            )
        )
        session.commit()

        candidate = session.get(SourceCandidate, result.candidates[0].candidate_id)
        source = session.get(Source, result.candidates[0].registered_source_id)

        assert result.status is AcquisitionStatus.SUCCESS
        assert result.provider_id == "fake"
        assert result.query == "external source discovery"
        assert result.candidate_count == 1
        assert result.registered_source_count == 1
        assert candidate is not None
        assert source is not None
        assert candidate.registered_source_id == source.id
        assert candidate.snippet == "Provider snippet is discovery material only."
        assert source.canonical_locator == "https://example.com/report"


def test_provider_timeout_and_error_are_persisted_as_failed_acquisitions(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    class TimeoutProvider:
        identifier = "timeout-provider"

        def search(self, request: AcquisitionRequest) -> ProviderSearchResult:
            raise AcquisitionProviderTimeout("timeout after 1 second")

    class ErrorProvider:
        identifier = "error-provider"

        def search(self, request: AcquisitionRequest) -> ProviderSearchResult:
            raise AcquisitionProviderError("upstream unavailable")

    with session_factory() as session:
        timeout_result = AcquisitionService(session, TimeoutProvider()).acquire(
            AcquisitionRequest(research_run_id=research_run.id, query="timeout")
        )
        error_result = AcquisitionService(session, ErrorProvider()).acquire(
            AcquisitionRequest(research_run_id=research_run.id, query="error")
        )
        session.commit()

        assert timeout_result.status is AcquisitionStatus.FAILED
        assert timeout_result.errors == ["timeout after 1 second"]
        assert error_result.status is AcquisitionStatus.FAILED
        assert error_result.errors == ["upstream unavailable"]


def test_unexpected_provider_exception_is_mapped_to_failed_audit_record(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    class BrokenProvider:
        identifier = "broken-provider"

        def search(self, request: AcquisitionRequest) -> ProviderSearchResult:
            raise RuntimeError("boom")

    with session_factory() as session:
        result = AcquisitionService(session, BrokenProvider()).acquire(
            AcquisitionRequest(research_run_id=research_run.id, query="unexpected failure")
        )
        session.commit()

        assert result.status is AcquisitionStatus.FAILED
        assert result.errors == ["unexpected provider failure: RuntimeError"]


def test_partial_results_remain_auditable(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    provider = FakeResearchProvider(
        status=AcquisitionStatus.PARTIAL,
        candidates=[
            ProviderSourceCandidate(
                canonical_locator="https://example.com/partial",
                title="Partial",
            )
        ],
        warnings=["provider returned partial results"],
        errors=["one provider shard failed"],
    )

    with session_factory() as session:
        result = AcquisitionService(session, provider).acquire(
            AcquisitionRequest(research_run_id=research_run.id, query="partial")
        )
        session.commit()
        record = session.get(ResearchAcquisitionRequest, result.acquisition_id)

        assert result.status is AcquisitionStatus.PARTIAL
        assert result.candidate_count == 1
        assert result.registered_source_count == 1
        assert record is not None
        assert record.warning_count == 1
        assert record.error_count == 1


def test_normalization_and_conservative_deduplication(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    provider = FakeResearchProvider(
        candidates=[
            ProviderSourceCandidate(
                canonical_locator="https://Example.com/a/?utm_source=x&b=2",
                title="Same",
            ),
            ProviderSourceCandidate(
                canonical_locator="https://example.com/a?b=2&utm_campaign=y",
                title="Same",
            ),
            ProviderSourceCandidate(
                canonical_locator="https://example.com/b",
                title="Same",
            ),
        ]
    )

    with session_factory() as session:
        result = AcquisitionService(session, provider).acquire(
            AcquisitionRequest(research_run_id=research_run.id, query="dedup")
        )
        session.commit()

        statuses = [candidate.registration_status for candidate in result.candidates]
        source_ids = [candidate.registered_source_id for candidate in result.candidates]

        assert normalize_locator("https://Example.com/a/?utm_source=x&b=2")[0] == (
            "https://example.com/a?b=2"
        )
        assert statuses == [
            SourceCandidateRegistrationStatus.REGISTERED_NEW_SOURCE,
            SourceCandidateRegistrationStatus.DUPLICATE_CANDIDATE,
            SourceCandidateRegistrationStatus.REGISTERED_NEW_SOURCE,
        ]
        assert result.registered_source_count == 2
        assert source_ids[0] is not None
        assert source_ids[1] is None
        assert source_ids[2] != source_ids[0]


def test_missing_metadata_remains_null_or_unknown(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    provider = FakeResearchProvider(
        candidates=[
            ProviderSourceCandidate(
                canonical_locator="catalog-record:123",
                title=None,
                publisher=None,
                source_type=None,
            )
        ]
    )

    with session_factory() as session:
        result = AcquisitionService(session, provider).acquire(
            AcquisitionRequest(research_run_id=research_run.id, query="unknown metadata")
        )
        session.commit()
        candidate = session.get(SourceCandidate, result.candidates[0].candidate_id)

        assert candidate is not None
        assert candidate.publisher is None
        assert candidate.normalized_domain is None
        assert candidate.source_type is None
        assert candidate.registration_status is SourceCandidateRegistrationStatus.NOT_REGISTERED
        assert result.registered_source_count == 0


def test_source_candidate_does_not_create_evidence_or_claim(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    with session_factory() as session:
        AcquisitionService(session, FakeResearchProvider()).acquire(
            AcquisitionRequest(research_run_id=research_run.id, query="boundary")
        )
        session.commit()

        assert session.scalar(select(func.count()).select_from(Evidence)) == 0
        assert session.scalar(select(func.count()).select_from(Claim)) == 0


def test_failed_acquisition_does_not_corrupt_research_run(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    with session_factory() as session:
        result = AcquisitionService(
            session,
            FakeResearchProvider(status=AcquisitionStatus.FAILED, errors=["provider failed"]),
        ).acquire(AcquisitionRequest(research_run_id=research_run.id, query="failure"))
        session.commit()
        stored_run = session.get(ResearchRun, research_run.id)

        assert result.status is AcquisitionStatus.FAILED
        assert stored_run is not None
        assert stored_run.status is ResearchRunStatus.PENDING


def test_provider_credentials_are_redacted_from_persisted_metadata(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    provider = FakeResearchProvider(
        candidates=[
            ProviderSourceCandidate(
                canonical_locator="https://example.com/security",
                provider_metadata={"api_token": "secret-value", "nested": {"password": "pw"}},
            )
        ]
    )

    with session_factory() as session:
        result = AcquisitionService(session, provider).acquire(
            AcquisitionRequest(
                research_run_id=research_run.id,
                query="security",
                metadata={"api_key": "secret-key", "safe": "ok"},
            )
        )
        session.commit()
        record = session.get(ResearchAcquisitionRequest, result.acquisition_id)
        candidate = session.get(SourceCandidate, result.candidates[0].candidate_id)

        assert record is not None
        assert candidate is not None
        assert record.request_metadata["api_key"] == "[REDACTED]"
        assert record.request_metadata["safe"] == "ok"
        assert candidate.provider_metadata["api_token"] == "[REDACTED]"
        assert candidate.provider_metadata["nested"]["password"] == "[REDACTED]"


def test_persistence_failure_rolls_back_acquisition_records(
    session_factory: sessionmaker,
    research_run: ResearchRun,
) -> None:
    def fail_candidate_insert(_mapper, _connection, _target) -> None:
        raise RuntimeError("forced persistence failure")

    event.listen(SourceCandidate, "before_insert", fail_candidate_insert)
    try:
        with session_factory() as session:
            with pytest.raises(RuntimeError):
                with session.begin():
                    AcquisitionService(session, FakeResearchProvider()).acquire(
                        AcquisitionRequest(research_run_id=research_run.id, query="rollback")
                    )

            assert session.scalar(select(func.count()).select_from(ResearchAcquisitionRequest)) == 0
            assert session.scalar(select(func.count()).select_from(SourceCandidate)) == 0
    finally:
        event.remove(SourceCandidate, "before_insert", fail_candidate_insert)


def test_unknown_research_run_rejected(session_factory: sessionmaker) -> None:
    with session_factory() as session:
        with pytest.raises(Exception, match="Research run not found"):
            AcquisitionService(session, FakeResearchProvider()).acquire(
                AcquisitionRequest(research_run_id=uuid.uuid4(), query="missing run")
            )
