"""Source content acquisition and evidence extraction foundation."""

from darwin.content.errors import (
    ArtifactStorageError,
    EvidenceExtractionError,
    SourceContentError,
    SourceFetchError,
    SourceFetchTimeout,
    UnsupportedSourceLocator,
)
from darwin.content.fetchers import FakeSourceFetcher, HTTPSourceFetcher, SourceFetcher
from darwin.content.schemas import (
    EvidenceExtractionResult,
    FetchResult,
    SegmentExtractionRequest,
    SourceContentSegmentRead,
    SourceContentSnapshotRead,
    SourceFetchRequest,
    SourceFetchServiceResult,
)
from darwin.content.service import SourceContentService

__all__ = [
    "ArtifactStorageError",
    "EvidenceExtractionError",
    "EvidenceExtractionResult",
    "FakeSourceFetcher",
    "FetchResult",
    "HTTPSourceFetcher",
    "SegmentExtractionRequest",
    "SourceContentError",
    "SourceContentSegmentRead",
    "SourceContentService",
    "SourceContentSnapshotRead",
    "SourceFetchError",
    "SourceFetchRequest",
    "SourceFetchServiceResult",
    "SourceFetchTimeout",
    "SourceFetcher",
    "UnsupportedSourceLocator",
]
