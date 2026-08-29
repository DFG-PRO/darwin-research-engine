"""Service layer for source content snapshots, segments, and evidence extraction."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from darwin.acquisition.normalization import sanitize_metadata
from darwin.config import Settings
from darwin.content.artifacts import ArtifactStore
from darwin.content.errors import EvidenceExtractionError, UnsupportedSourceLocator
from darwin.content.fetchers import SourceFetcher
from darwin.content.hashing import sha256_text
from darwin.content.normalization import normalize_content
from darwin.content.schemas import (
    EvidenceExtractionResult,
    FetchResult,
    SegmentExtractionRequest,
    SourceContentSegmentRead,
    SourceContentSnapshotRead,
    SourceFetchRequest,
    SourceFetchServiceResult,
    source_type_supported_for_fetch,
)
from darwin.content.segmentation import segment_text
from darwin.db.models import (
    EvidenceExtractionRecord,
    EvidenceExtractionStatus,
    EvidenceType,
    Source,
    SourceContentSegment,
    SourceContentSnapshot,
    SourceFetchStatus,
)
from darwin.research import ResearchService


class SourceContentService:
    """Coordinate source fetches, snapshots, segmentation, and explicit evidence extraction."""

    def __init__(self, session: Session, settings: Settings, fetcher: SourceFetcher) -> None:
        self.session = session
        self.settings = settings
        self.fetcher = fetcher
        self.artifacts = ArtifactStore(settings.artifact_root)
        self.research_service = ResearchService(session)

    def fetch_source(self, request: SourceFetchRequest) -> SourceFetchServiceResult:
        self.research_service.get_research_run(request.research_run_id)
        source = self._get_source(request.source_id)
        requested_locator = self._requested_locator(request, source)

        if not source_type_supported_for_fetch(source.source_type):
            fetch_result = FetchResult(
                source_id=source.id,
                canonical_locator=requested_locator,
                fetch_status=SourceFetchStatus.UNSUPPORTED_CONTENT_TYPE,
                errors=["source type is not supported for content fetch"],
                retrieval_method_version=self.fetcher.retrieval_method_version,
            )
            snapshot = self._persist_snapshot(request, fetch_result)
            return SourceFetchServiceResult(
                snapshot=SourceContentSnapshotRead.model_validate(snapshot),
                segments=[],
            )

        fetch_request = request.model_copy(update={"canonical_locator": requested_locator})
        fetch_result = self.fetcher.fetch(fetch_request)
        fetch_result = self._enforce_raw_body_size(fetch_result)
        snapshot = self._persist_snapshot(request, fetch_result)

        segments: list[SourceContentSegment] = []
        if fetch_result.fetch_status is SourceFetchStatus.SUCCESS and fetch_result.raw_body is not None:
            raw_path = self.artifacts.write_snapshot_artifact(
                research_run_id=request.research_run_id,
                source_id=source.id,
                snapshot_id=snapshot.id,
                filename="raw.bin",
                content=fetch_result.raw_body,
            )
            normalized_text = normalize_content(fetch_result.raw_body, fetch_result.content_type)
            normalized_bytes = normalized_text.encode("utf-8")
            normalized_path = self.artifacts.write_snapshot_artifact(
                research_run_id=request.research_run_id,
                source_id=source.id,
                snapshot_id=snapshot.id,
                filename="normalized.txt",
                content=normalized_bytes,
            )
            snapshot.raw_artifact_path = raw_path
            snapshot.normalized_artifact_path = normalized_path
            snapshot.normalized_content_fingerprint = sha256_text(normalized_text)
            snapshot.normalization_method_version = (
                self.settings.source_content_normalization_method_version
            )
            snapshot.normalized_body_size = len(normalized_bytes)
            segments = self._persist_segments(snapshot, source, normalized_text)
            snapshot.segment_count = len(segments)

        self.session.flush()
        return SourceFetchServiceResult(
            snapshot=SourceContentSnapshotRead.model_validate(snapshot),
            segments=[SourceContentSegmentRead.model_validate(segment) for segment in segments],
        )

    def list_segments(self, snapshot_id: uuid.UUID) -> list[SourceContentSegmentRead]:
        segments = self.session.scalars(
            select(SourceContentSegment)
            .where(SourceContentSegment.snapshot_id == snapshot_id)
            .order_by(SourceContentSegment.segment_order)
        ).all()
        return [SourceContentSegmentRead.model_validate(segment) for segment in segments]

    def extract_evidence(
        self,
        request: SegmentExtractionRequest,
    ) -> EvidenceExtractionResult:
        self.research_service.get_research_run(request.research_run_id)
        segment = self.session.get(SourceContentSegment, request.segment_id)
        if segment is None:
            raise EvidenceExtractionError(f"Source content segment not found: {request.segment_id}")

        snapshot = segment.snapshot
        if snapshot.research_run_id != request.research_run_id:
            raise EvidenceExtractionError("Segment snapshot belongs to a different research run")

        selected_text, relative_start, relative_end = self._select_text(request, segment)
        absolute_start = segment.char_start + relative_start
        absolute_end = segment.char_start + relative_end
        selection_locator = f"{segment.locator}:chars={relative_start}-{relative_end}"

        if len(selected_text) > self.settings.evidence_excerpt_max_chars:
            return self._persist_failed_extraction(
                request=request,
                segment=segment,
                snapshot=snapshot,
                selected_text=selected_text,
                char_start=absolute_start,
                char_end=absolute_end,
                errors=["selected evidence exceeds maximum excerpt size"],
                selection_locator=selection_locator,
            )

        evidence = self.research_service.register_evidence(
            research_run_id=request.research_run_id,
            source_id=segment.source_id,
            evidence_type=EvidenceType.EXCERPT,
            statement=selected_text,
            source_locator=selection_locator,
            metadata={
                "content_snapshot_id": str(snapshot.id),
                "source_content_segment_id": str(segment.id),
                "selection": {
                    "char_start": absolute_start,
                    "char_end": absolute_end,
                    "relative_char_start": relative_start,
                    "relative_char_end": relative_end,
                },
                "extraction_method_version": self.settings.evidence_extraction_method_version,
                **sanitize_metadata(request.metadata),
            },
        )
        extraction = EvidenceExtractionRecord(
            research_run_id=request.research_run_id,
            source_id=segment.source_id,
            snapshot_id=snapshot.id,
            segment_id=segment.id,
            evidence_id=evidence.id,
            extraction_status=EvidenceExtractionStatus.EXTRACTED,
            extraction_method_version=self.settings.evidence_extraction_method_version,
            selected_text=selected_text,
            selected_text_fingerprint=sha256_text(selected_text),
            selection_locator=selection_locator,
            char_start=absolute_start,
            char_end=absolute_end,
            extraction_metadata=sanitize_metadata(request.metadata),
        )
        self.session.add(extraction)
        self.session.flush()
        return self._extraction_result(extraction)

    def _persist_snapshot(
        self,
        request: SourceFetchRequest,
        fetch_result: FetchResult,
    ) -> SourceContentSnapshot:
        snapshot = SourceContentSnapshot(
            research_run_id=request.research_run_id,
            source_id=request.source_id,
            requested_locator=fetch_result.canonical_locator,
            final_locator=fetch_result.final_locator,
            fetch_status=fetch_result.fetch_status,
            fetched_at=fetch_result.fetched_at,
            content_type=fetch_result.content_type,
            response_status=fetch_result.response_status,
            raw_content_fingerprint=fetch_result.content_fingerprint,
            retrieval_method_version=fetch_result.retrieval_method_version,
            raw_body_size=len(fetch_result.raw_body) if fetch_result.raw_body is not None else None,
            warnings=fetch_result.warnings,
            errors=fetch_result.errors,
            response_metadata=sanitize_metadata(fetch_result.response_metadata),
            request_metadata=sanitize_metadata(request.metadata),
        )
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def _enforce_raw_body_size(self, fetch_result: FetchResult) -> FetchResult:
        if (
            fetch_result.raw_body is None
            or len(fetch_result.raw_body) <= self.settings.source_fetch_max_bytes
        ):
            return fetch_result
        return fetch_result.model_copy(
            update={
                "fetch_status": SourceFetchStatus.TOO_LARGE,
                "raw_body": None,
                "content_fingerprint": None,
                "errors": [*fetch_result.errors, "response exceeded maximum size"],
            }
        )

    def _persist_segments(
        self,
        snapshot: SourceContentSnapshot,
        source: Source,
        normalized_text: str,
    ) -> list[SourceContentSegment]:
        segments: list[SourceContentSegment] = []
        for segment in segment_text(normalized_text, base_locator=snapshot.final_locator):
            model = SourceContentSegment(
                snapshot_id=snapshot.id,
                source_id=source.id,
                segment_identifier=segment.segment_identifier,
                segment_order=segment.segment_order,
                text=segment.text,
                locator=segment.locator,
                char_start=segment.char_start,
                char_end=segment.char_end,
                line_start=segment.line_start,
                line_end=segment.line_end,
                fingerprint=segment.fingerprint,
            )
            self.session.add(model)
            segments.append(model)
        self.session.flush()
        return segments

    def _persist_failed_extraction(
        self,
        *,
        request: SegmentExtractionRequest,
        segment: SourceContentSegment,
        snapshot: SourceContentSnapshot,
        selected_text: str,
        char_start: int,
        char_end: int,
        errors: list[str],
        selection_locator: str,
    ) -> EvidenceExtractionResult:
        extraction = EvidenceExtractionRecord(
            research_run_id=request.research_run_id,
            source_id=segment.source_id,
            snapshot_id=snapshot.id,
            segment_id=segment.id,
            extraction_status=EvidenceExtractionStatus.FAILED,
            extraction_method_version=self.settings.evidence_extraction_method_version,
            selected_text=None,
            selected_text_fingerprint=sha256_text(selected_text),
            selection_locator=selection_locator,
            char_start=char_start,
            char_end=char_end,
            errors=errors,
            extraction_metadata=sanitize_metadata(request.metadata),
        )
        self.session.add(extraction)
        self.session.flush()
        return self._extraction_result(extraction)

    def _select_text(
        self,
        request: SegmentExtractionRequest,
        segment: SourceContentSegment,
    ) -> tuple[str, int, int]:
        if request.char_start is None and request.char_end is None:
            return segment.text, 0, len(segment.text)
        assert request.char_start is not None
        assert request.char_end is not None
        if request.char_end > len(segment.text):
            raise EvidenceExtractionError("Selected span exceeds segment length")
        return segment.text[request.char_start : request.char_end], request.char_start, request.char_end

    def _requested_locator(self, request: SourceFetchRequest, source: Source) -> str:
        if request.canonical_locator is None:
            return source.canonical_locator
        if request.canonical_locator != source.canonical_locator:
            raise UnsupportedSourceLocator("Fetch locator must match the registered Source locator")
        return request.canonical_locator

    def _get_source(self, source_id: uuid.UUID) -> Source:
        source = self.session.get(Source, source_id)
        if source is None:
            raise UnsupportedSourceLocator(f"Source not found: {source_id}")
        return source

    def _extraction_result(self, extraction: EvidenceExtractionRecord) -> EvidenceExtractionResult:
        return EvidenceExtractionResult(
            extraction_id=extraction.id,
            extraction_status=extraction.extraction_status,
            evidence_id=extraction.evidence_id,
            research_run_id=extraction.research_run_id,
            source_id=extraction.source_id,
            snapshot_id=extraction.snapshot_id,
            segment_id=extraction.segment_id,
            selected_text=extraction.selected_text,
            selected_text_fingerprint=extraction.selected_text_fingerprint,
            selection_locator=extraction.selection_locator,
            errors=extraction.errors,
        )
