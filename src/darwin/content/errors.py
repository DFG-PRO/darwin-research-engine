"""Errors for source content acquisition and evidence extraction."""

from __future__ import annotations


class SourceContentError(Exception):
    """Base error for source content operations."""


class SourceFetchError(SourceContentError):
    """Fetcher failed before returning a normal fetch result."""


class SourceFetchTimeout(SourceFetchError):
    """Fetcher timed out."""


class UnsupportedSourceLocator(SourceContentError):
    """Source locator is not supported by the configured fetcher."""


class ArtifactStorageError(SourceContentError):
    """Artifact storage failed or attempted an unsafe path."""


class EvidenceExtractionError(SourceContentError):
    """Explicit evidence extraction failed."""
