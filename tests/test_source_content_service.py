from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import sessionmaker

from darwin.config import Settings
from darwin.content import (
    ArtifactStorageError,
    EvidenceExtractionError,
    FakeSourceFetcher,
    HTTPSourceFetcher,
    SegmentExtractionRequest,
    SourceContentService,
    SourceFetchRequest,
    UnsupportedSourceLocator,
)
from darwin.content.artifacts import ArtifactStore
from darwin.content.hashing import sha256_bytes, sha256_text
from darwin.content.normalization import normalize_content
from darwin.db.models import (
    Claim,
    ClaimValidationEvaluation,
    Evidence,
    EvidenceExtractionRecord,
    EvidenceExtractionStatus,
    ResearchRun,
    ResearchRunStatus,
    Source,
    SourceContentSegment,
    SourceContentSnapshot,
    SourceFetchStatus,
    SourceType,
)
from darwin.research import ResearchService


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        env="test",
        database_url="sqlite+pysqlite:///:memory:",
        artifact_root=tmp_path / "artifacts",
        source_fetch_max_bytes=1024,
        evidence_excerpt_max_chars=80,
    )


@pytest.fixture()
def research_run_and_source(session_factory: sessionmaker) -> tuple[ResearchRun, Source]:
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Content test run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/source",
        )
        session.commit()
        return research_run, source


def test_successful_html_fetch_persists_snapshot_artifacts_and_segments(
    session_factory: sessionmaker,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
) -> None:
    research_run, source = research_run_and_source
    body = (
        b"<html><head><script>bad()</script><style>.x{}</style></head>"
        b"<body><h1>Title</h1><p>Readable text.</p><p>Second paragraph.</p></body></html>"
    )

    with session_factory.begin() as session:
        result = SourceContentService(
            session,
            settings,
            FakeSourceFetcher(body=body, content_type="text/html"),
        ).fetch_source(SourceFetchRequest(research_run_id=research_run.id, source_id=source.id))

    assert result.snapshot.fetch_status is SourceFetchStatus.SUCCESS
    assert result.snapshot.raw_content_fingerprint == sha256_bytes(body)
    assert result.snapshot.normalized_content_fingerprint is not None
    assert result.snapshot.raw_artifact_path is not None
    assert result.snapshot.normalized_artifact_path is not None
    assert [segment.text for segment in result.segments] == [
        "Title",
        "Readable text.",
        "Second paragraph.",
    ]
    assert "bad()" not in "\n".join(segment.text for segment in result.segments)

    raw_path = ArtifactStore(settings.artifact_root).resolve_artifact_path(
        result.snapshot.raw_artifact_path
    )
    normalized_path = ArtifactStore(settings.artifact_root).resolve_artifact_path(
        result.snapshot.normalized_artifact_path
    )
    assert raw_path.read_bytes() == body
    assert normalized_path.read_text() == "Title\n\nReadable text.\n\nSecond paragraph."


def test_successful_plain_text_fetch_normalizes_newlines_deterministically(
    session_factory: sessionmaker,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
) -> None:
    research_run, source = research_run_and_source

    with session_factory.begin() as session:
        result = SourceContentService(
            session,
            settings,
            FakeSourceFetcher(body=b"First line\r\nsecond line\r\n\r\nThird line", content_type="text/plain"),
        ).fetch_source(SourceFetchRequest(research_run_id=research_run.id, source_id=source.id))

    assert [segment.text for segment in result.segments] == ["First line second line", "Third line"]


def test_http_fetcher_success_timeout_error_redirect_unsupported_oversized_and_invalid_scheme(
    monkeypatch,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
) -> None:
    research_run, source = research_run_and_source
    real_httpx_client = httpx.Client

    def make_fetcher(handler):
        transport = httpx.MockTransport(handler)

        def client_factory(*args, **kwargs):
            kwargs["transport"] = transport
            return real_httpx_client(*args, **kwargs)

        monkeypatch.setattr("darwin.content.fetchers.httpx.Client", client_factory)
        return HTTPSourceFetcher(settings)

    def request() -> SourceFetchRequest:
        return SourceFetchRequest(
            research_run_id=research_run.id,
            source_id=source.id,
            canonical_locator="https://example.com/source",
        )

    fetcher = make_fetcher(
        lambda _: httpx.Response(200, headers={"content-type": "text/html"}, text="<p>Hello</p>")
    )
    result = fetcher.fetch(request())
    assert result.fetch_status is SourceFetchStatus.SUCCESS
    assert result.content_fingerprint == sha256_bytes(b"<p>Hello</p>")

    fetcher = make_fetcher(lambda _: (_ for _ in ()).throw(httpx.TimeoutException("timeout")))
    assert fetcher.fetch(request()).errors == ["source fetch timed out"]

    fetcher = make_fetcher(lambda _: httpx.Response(500, headers={"content-type": "text/html"}))
    assert fetcher.fetch(request()).errors == ["http status 500"]

    def redirect_handler(http_request: httpx.Request) -> httpx.Response:
        if str(http_request.url) == "https://example.com/source":
            return httpx.Response(302, headers={"location": "https://example.com/final"})
        return httpx.Response(200, headers={"content-type": "text/plain"}, text="Redirected")

    fetcher = make_fetcher(redirect_handler)
    redirect_result = fetcher.fetch(request())
    assert redirect_result.fetch_status is SourceFetchStatus.SUCCESS
    assert redirect_result.final_locator == "https://example.com/final"

    fetcher = make_fetcher(lambda _: httpx.Response(200, headers={"content-type": "image/png"}))
    assert fetcher.fetch(request()).fetch_status is SourceFetchStatus.UNSUPPORTED_CONTENT_TYPE

    fetcher = make_fetcher(
        lambda _: httpx.Response(200, headers={"content-type": "text/plain"}, content=b"x" * 1025)
    )
    assert fetcher.fetch(request()).fetch_status is SourceFetchStatus.TOO_LARGE

    invalid = SourceFetchRequest(
        research_run_id=research_run.id,
        source_id=source.id,
        canonical_locator="file:///etc/passwd",
    )
    assert HTTPSourceFetcher(settings).fetch(invalid).errors == ["unsupported locator scheme"]


def test_failed_fetch_does_not_corrupt_source_or_research_run(
    session_factory: sessionmaker,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
) -> None:
    research_run, source = research_run_and_source

    with session_factory.begin() as session:
        result = SourceContentService(
            session,
            settings,
            FakeSourceFetcher(status=SourceFetchStatus.FAILED, errors=["network failed"]),
        ).fetch_source(SourceFetchRequest(research_run_id=research_run.id, source_id=source.id))

    with session_factory() as session:
        stored_run = session.get(ResearchRun, research_run.id)
        stored_source = session.get(Source, source.id)
        assert result.snapshot.fetch_status is SourceFetchStatus.FAILED
        assert stored_run.status is ResearchRunStatus.PENDING
        assert stored_source.canonical_locator == source.canonical_locator
        assert session.scalar(select(func.count()).select_from(SourceContentSnapshot)) == 1


def test_snapshot_history_and_repeated_identical_content_remain_auditable(
    session_factory: sessionmaker,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
) -> None:
    research_run, source = research_run_and_source
    body = b"Same content"

    with session_factory.begin() as session:
        service = SourceContentService(
            session,
            settings,
            FakeSourceFetcher(body=body, content_type="text/plain"),
        )
        first = service.fetch_source(SourceFetchRequest(research_run_id=research_run.id, source_id=source.id))
        second = service.fetch_source(SourceFetchRequest(research_run_id=research_run.id, source_id=source.id))

    assert first.snapshot.id != second.snapshot.id
    assert first.snapshot.raw_content_fingerprint == second.snapshot.raw_content_fingerprint


def test_artifact_store_rejects_traversal(settings: Settings) -> None:
    store = ArtifactStore(settings.artifact_root)

    with pytest.raises(ArtifactStorageError):
        store.resolve_artifact_path("../outside")


def test_artifact_write_failure_rolls_back_snapshot(
    session_factory: sessionmaker,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
    monkeypatch,
) -> None:
    research_run, source = research_run_and_source

    def fail_write(*args, **kwargs):
        raise ArtifactStorageError("forced artifact failure")

    monkeypatch.setattr(ArtifactStore, "write_snapshot_artifact", fail_write)

    with session_factory() as session:
        with pytest.raises(ArtifactStorageError):
            with session.begin():
                SourceContentService(
                    session,
                    settings,
                    FakeSourceFetcher(body=b"content", content_type="text/plain"),
                ).fetch_source(SourceFetchRequest(research_run_id=research_run.id, source_id=source.id))

        assert session.scalar(select(func.count()).select_from(SourceContentSnapshot)) == 0
        assert session.scalar(select(func.count()).select_from(SourceContentSegment)) == 0


def test_exact_segment_and_span_extraction_registers_evidence_with_traceability(
    session_factory: sessionmaker,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
) -> None:
    research_run, source = research_run_and_source

    with session_factory.begin() as session:
        service = SourceContentService(
            session,
            settings,
            FakeSourceFetcher(body=b"Alpha paragraph.\n\nBeta paragraph.", content_type="text/plain"),
        )
        fetch_result = service.fetch_source(
            SourceFetchRequest(research_run_id=research_run.id, source_id=source.id)
        )
        segment = fetch_result.segments[1]
        extraction = service.extract_evidence(
            SegmentExtractionRequest(research_run_id=research_run.id, segment_id=segment.id)
        )
        span_extraction = service.extract_evidence(
            SegmentExtractionRequest(
                research_run_id=research_run.id,
                segment_id=segment.id,
                char_start=0,
                char_end=4,
            )
        )

    with session_factory() as session:
        evidence = session.get(Evidence, extraction.evidence_id)
        span_evidence = session.get(Evidence, span_extraction.evidence_id)
        record = session.get(EvidenceExtractionRecord, extraction.extraction_id)

        assert evidence.statement == "Beta paragraph."
        assert span_evidence.statement == "Beta"
        assert evidence.source_id == source.id
        assert evidence.evidence_metadata["content_snapshot_id"] == str(segment.snapshot_id)
        assert evidence.evidence_metadata["source_content_segment_id"] == str(segment.id)
        assert record.extraction_status is EvidenceExtractionStatus.EXTRACTED
        assert record.selected_text_fingerprint == sha256_text("Beta paragraph.")


def test_oversized_evidence_extraction_is_rejected_without_claims(
    session_factory: sessionmaker,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
) -> None:
    research_run, source = research_run_and_source

    with session_factory.begin() as session:
        service = SourceContentService(
            session,
            settings,
            FakeSourceFetcher(body=b"x" * 100, content_type="text/plain"),
        )
        fetch_result = service.fetch_source(
            SourceFetchRequest(research_run_id=research_run.id, source_id=source.id)
        )
        extraction = service.extract_evidence(
            SegmentExtractionRequest(
                research_run_id=research_run.id,
                segment_id=fetch_result.segments[0].id,
            )
        )

    with session_factory() as session:
        assert extraction.extraction_status is EvidenceExtractionStatus.FAILED
        assert extraction.evidence_id is None
        assert session.scalar(select(func.count()).select_from(Evidence)) == 0
        assert session.scalar(select(func.count()).select_from(Claim)) == 0
        assert session.scalar(select(func.count()).select_from(ClaimValidationEvaluation)) == 0


def test_extraction_errors_are_clear_for_bad_span_or_wrong_run(
    session_factory: sessionmaker,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
) -> None:
    research_run, source = research_run_and_source

    with session_factory.begin() as session:
        service = SourceContentService(
            session,
            settings,
            FakeSourceFetcher(body=b"Short text", content_type="text/plain"),
        )
        fetch_result = service.fetch_source(
            SourceFetchRequest(research_run_id=research_run.id, source_id=source.id)
        )
        segment_id = fetch_result.segments[0].id
        other_run = ResearchService(session).create_research_run(
            title="Other run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )

        with pytest.raises(EvidenceExtractionError):
            service.extract_evidence(
                SegmentExtractionRequest(
                    research_run_id=research_run.id,
                    segment_id=segment_id,
                    char_start=0,
                    char_end=100,
                )
            )
        with pytest.raises(EvidenceExtractionError):
            service.extract_evidence(
                SegmentExtractionRequest(research_run_id=other_run.id, segment_id=segment_id)
            )


def test_fetch_rejects_unregistered_source_or_mismatched_locator(
    session_factory: sessionmaker,
    settings: Settings,
    research_run_and_source: tuple[ResearchRun, Source],
) -> None:
    research_run, source = research_run_and_source

    with session_factory() as session:
        service = SourceContentService(session, settings, FakeSourceFetcher())
        with pytest.raises(UnsupportedSourceLocator):
            service.fetch_source(
                SourceFetchRequest(research_run_id=research_run.id, source_id=uuid.uuid4())
            )
        with pytest.raises(UnsupportedSourceLocator):
            service.fetch_source(
                SourceFetchRequest(
                    research_run_id=research_run.id,
                    source_id=source.id,
                    canonical_locator="https://evil.example/other",
                )
            )


def test_source_type_unsupported_for_fetch_is_audited(
    session_factory: sessionmaker,
    settings: Settings,
) -> None:
    with session_factory.begin() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Unsupported source type",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.DOCUMENT,
            canonical_locator="fixture://document",
        )
        result = SourceContentService(session, settings, FakeSourceFetcher()).fetch_source(
            SourceFetchRequest(research_run_id=research_run.id, source_id=source.id)
        )

    assert result.snapshot.fetch_status is SourceFetchStatus.UNSUPPORTED_CONTENT_TYPE
    assert result.snapshot.errors == ["source type is not supported for content fetch"]


def test_plain_normalization_preserves_semantic_text() -> None:
    normalized = normalize_content(b" A   B \r\n\r\n C ", "text/plain")

    assert normalized == "A B\n\nC"
