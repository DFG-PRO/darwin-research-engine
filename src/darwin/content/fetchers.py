"""Source content fetcher contracts and adapters."""

from __future__ import annotations

from typing import Protocol
from urllib.parse import urlsplit

import httpx

from darwin.config import Settings
from darwin.content.hashing import sha256_bytes
from darwin.content.schemas import FetchResult, SourceFetchRequest
from darwin.db.models import SourceFetchStatus, utc_now

SUPPORTED_TEXT_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "application/json",
)


class SourceFetcher(Protocol):
    """Provider-agnostic boundary for source content fetching."""

    retrieval_method_version: str

    def fetch(self, request: SourceFetchRequest) -> FetchResult:
        """Fetch source content for a registered Source."""


class FakeSourceFetcher:
    """Deterministic fetcher for tests and local smoke checks."""

    retrieval_method_version = "fake-source-fetch-1.8g"

    def __init__(
        self,
        *,
        body: bytes = b"<html><body><p>Fake source content.</p></body></html>",
        content_type: str = "text/html; charset=utf-8",
        status: SourceFetchStatus = SourceFetchStatus.SUCCESS,
        response_status: int | None = 200,
        final_locator: str | None = None,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> None:
        self.body = body
        self.content_type = content_type
        self.status = status
        self.response_status = response_status
        self.final_locator = final_locator
        self.warnings = warnings or []
        self.errors = errors or []

    def fetch(self, request: SourceFetchRequest) -> FetchResult:
        raw_body = self.body if self.status is SourceFetchStatus.SUCCESS else None
        return FetchResult(
            source_id=request.source_id,
            canonical_locator=request.canonical_locator or "",
            final_locator=self.final_locator or request.canonical_locator,
            fetched_at=utc_now(),
            fetch_status=self.status,
            content_type=self.content_type,
            response_status=self.response_status,
            raw_body=raw_body,
            response_metadata={"provider": "fake"},
            warnings=self.warnings,
            errors=self.errors,
            content_fingerprint=sha256_bytes(raw_body) if raw_body is not None else None,
            retrieval_method_version=self.retrieval_method_version,
        )


class HTTPSourceFetcher:
    """Small HTTP fetcher for supported text source content."""

    def __init__(self, settings: Settings) -> None:
        self.retrieval_method_version = settings.source_content_retrieval_method_version
        self.timeout_seconds = settings.source_fetch_timeout_seconds
        self.max_retries = settings.source_fetch_max_retries
        self.user_agent = settings.source_fetch_user_agent
        self.max_bytes = settings.source_fetch_max_bytes

    def fetch(self, request: SourceFetchRequest) -> FetchResult:
        locator = request.canonical_locator or ""
        if not _is_http_locator(locator):
            return self._failure(
                request,
                SourceFetchStatus.FAILED,
                errors=["unsupported locator scheme"],
            )

        timeout = request.timeout_seconds or self.timeout_seconds
        attempts = 0
        for attempt in range(self.max_retries + 1):
            attempts = attempt
            try:
                result = self._fetch_once(request, timeout)
                result.response_metadata["retry_attempts"] = attempts
                return result
            except httpx.TimeoutException:
                if attempt >= self.max_retries:
                    return self._failure(
                        request,
                        SourceFetchStatus.FAILED,
                        errors=["source fetch timed out"],
                        metadata={"retry_attempts": attempts},
                    )
            except httpx.HTTPError as exc:
                if attempt >= self.max_retries:
                    return self._failure(
                        request,
                        SourceFetchStatus.FAILED,
                        errors=[f"source fetch failed: {exc.__class__.__name__}"],
                        metadata={"retry_attempts": attempts},
                    )

        return self._failure(
            request,
            SourceFetchStatus.FAILED,
            errors=["source fetch failed"],
            metadata={"retry_attempts": attempts},
        )

    def _fetch_once(self, request: SourceFetchRequest, timeout: float) -> FetchResult:
        headers = {"User-Agent": self.user_agent, "Accept": "text/html,text/plain,application/json"}
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
            with client.stream("GET", request.canonical_locator or "") as response:
                content_type = response.headers.get("content-type")
                final_locator = str(response.url)
                response_metadata = {
                    "headers": _safe_response_headers(response.headers),
                    "redirect_history": [str(item.url) for item in response.history],
                }
                if not _is_safe_redirect_locator(final_locator):
                    return self._failure(
                        request,
                        SourceFetchStatus.FAILED,
                        final_locator=final_locator,
                        response_status=response.status_code,
                        content_type=content_type,
                        errors=["unsafe redirect scheme"],
                        metadata=response_metadata,
                    )
                if response.status_code in {401, 403}:
                    return self._failure(
                        request,
                        SourceFetchStatus.ACCESS_DENIED,
                        final_locator=final_locator,
                        response_status=response.status_code,
                        content_type=content_type,
                        errors=["access denied"],
                        metadata=response_metadata,
                    )
                if response.status_code >= 400:
                    return self._failure(
                        request,
                        SourceFetchStatus.FAILED,
                        final_locator=final_locator,
                        response_status=response.status_code,
                        content_type=content_type,
                        errors=[f"http status {response.status_code}"],
                        metadata=response_metadata,
                    )
                if not _is_supported_content_type(content_type):
                    return self._failure(
                        request,
                        SourceFetchStatus.UNSUPPORTED_CONTENT_TYPE,
                        final_locator=final_locator,
                        response_status=response.status_code,
                        content_type=content_type,
                        errors=["unsupported content type"],
                        metadata=response_metadata,
                    )

                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > self.max_bytes:
                        return self._failure(
                            request,
                            SourceFetchStatus.TOO_LARGE,
                            final_locator=final_locator,
                            response_status=response.status_code,
                            content_type=content_type,
                            errors=["response exceeded maximum size"],
                            metadata=response_metadata,
                        )

        raw_body = bytes(body)
        return FetchResult(
            source_id=request.source_id,
            canonical_locator=request.canonical_locator or "",
            final_locator=final_locator,
            fetched_at=utc_now(),
            fetch_status=SourceFetchStatus.SUCCESS,
            content_type=content_type,
            response_status=response.status_code,
            raw_body=raw_body,
            response_metadata=response_metadata,
            content_fingerprint=sha256_bytes(raw_body),
            retrieval_method_version=self.retrieval_method_version,
        )

    def _failure(
        self,
        request: SourceFetchRequest,
        status: SourceFetchStatus,
        *,
        final_locator: str | None = None,
        response_status: int | None = None,
        content_type: str | None = None,
        errors: list[str] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> FetchResult:
        return FetchResult(
            source_id=request.source_id,
            canonical_locator=request.canonical_locator or "",
            final_locator=final_locator,
            fetched_at=utc_now(),
            fetch_status=status,
            content_type=content_type,
            response_status=response_status,
            raw_body=None,
            response_metadata=metadata or {},
            errors=errors or [],
            retrieval_method_version=self.retrieval_method_version,
        )


def _is_http_locator(locator: str) -> bool:
    parts = urlsplit(locator)
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def _is_safe_redirect_locator(locator: str) -> bool:
    return _is_http_locator(locator)


def _is_supported_content_type(content_type: str | None) -> bool:
    if content_type is None:
        return False
    normalized = content_type.split(";", 1)[0].strip().lower()
    return normalized in SUPPORTED_TEXT_CONTENT_TYPES or normalized.endswith("+json")


def _safe_response_headers(headers: httpx.Headers) -> dict[str, str]:
    allowed = {"content-type", "content-length", "etag", "last-modified"}
    return {key: value for key, value in headers.items() if key.lower() in allowed}
