"""Pydantic contracts for source content acquisition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from darwin.db.models import EvidenceExtractionStatus, SourceFetchStatus, SourceType, utc_now


class SourceFetchRequest(BaseModel):
    """Explicit request to fetch content for a registered Source."""

    model_config = ConfigDict(str_strip_whitespace=True)

    research_run_id: uuid.UUID
    source_id: uuid.UUID
    canonical_locator: str | None = Field(default=None, min_length=1)
    timeout_seconds: float | None = Field(default=None, ge=0.1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FetchResult(BaseModel):
    """Fetcher result before snapshot persistence."""

    source_id: uuid.UUID
    canonical_locator: str
    final_locator: str | None = None
    fetched_at: datetime = Field(default_factory=utc_now)
    fetch_status: SourceFetchStatus
    content_type: str | None = None
    response_status: int | None = None
    raw_body: bytes | None = None
    response_metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    content_fingerprint: str | None = None
    retrieval_method_version: str


class SegmentExtractionRequest(BaseModel):
    """Explicit request to register evidence from a content segment."""

    research_run_id: uuid.UUID
    segment_id: uuid.UUID
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_span(self) -> SegmentExtractionRequest:
        if (self.char_start is None) != (self.char_end is None):
            raise ValueError("char_start and char_end must be supplied together")
        if self.char_start is not None and self.char_end is not None and self.char_start >= self.char_end:
            raise ValueError("char_start must be before char_end")
        return self


class SourceContentSegmentRead(BaseModel):
    """Persisted source content segment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    snapshot_id: uuid.UUID
    source_id: uuid.UUID
    segment_identifier: str
    segment_order: int
    text: str
    locator: str | None
    char_start: int
    char_end: int
    line_start: int
    line_end: int
    fingerprint: str


class SourceContentSnapshotRead(BaseModel):
    """Persisted source content snapshot summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    research_run_id: uuid.UUID
    source_id: uuid.UUID
    requested_locator: str
    final_locator: str | None
    fetch_status: SourceFetchStatus
    fetched_at: datetime
    content_type: str | None
    response_status: int | None
    raw_content_fingerprint: str | None
    normalized_content_fingerprint: str | None
    retrieval_method_version: str
    normalization_method_version: str | None
    raw_body_size: int | None
    normalized_body_size: int | None
    raw_artifact_path: str | None
    normalized_artifact_path: str | None
    segment_count: int
    warnings: list[str]
    errors: list[str]


class SourceFetchServiceResult(BaseModel):
    """Snapshot plus generated segments."""

    snapshot: SourceContentSnapshotRead
    segments: list[SourceContentSegmentRead]


class EvidenceExtractionResult(BaseModel):
    """Result of explicit segment/span evidence extraction."""

    extraction_id: uuid.UUID
    extraction_status: EvidenceExtractionStatus
    evidence_id: uuid.UUID | None
    research_run_id: uuid.UUID
    source_id: uuid.UUID
    snapshot_id: uuid.UUID
    segment_id: uuid.UUID
    selected_text: str | None
    selected_text_fingerprint: str | None
    selection_locator: str | None
    errors: list[str]


def source_type_supported_for_fetch(source_type: SourceType) -> bool:
    """Return whether Phase 1.8G supports fetching this source type."""

    return source_type in {SourceType.WEB_PAGE, SourceType.API, SourceType.OTHER}
