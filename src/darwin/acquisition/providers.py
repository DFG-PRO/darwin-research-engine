"""External research provider contracts and adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

import httpx

from darwin.acquisition.errors import (
    AcquisitionConfigurationError,
    AcquisitionProviderError,
    AcquisitionProviderTimeout,
)
from darwin.acquisition.schemas import (
    AcquisitionRequest,
    ProviderSearchResult,
    ProviderSourceCandidate,
)
from darwin.config import Settings
from darwin.db.models import AcquisitionStatus, SourceType, utc_now


class ResearchProvider(Protocol):
    """Provider-agnostic boundary for external source discovery."""

    identifier: str

    def search(self, request: AcquisitionRequest) -> ProviderSearchResult:
        """Discover source candidates for an explicit acquisition request."""


class FakeResearchProvider:
    """Deterministic provider for tests and local CLI smoke checks."""

    identifier = "fake"

    def __init__(
        self,
        *,
        status: AcquisitionStatus = AcquisitionStatus.SUCCESS,
        candidates: list[ProviderSourceCandidate] | None = None,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> None:
        self.status = status
        self._candidates = candidates
        self.warnings = warnings or []
        self.errors = errors or []

    def search(self, request: AcquisitionRequest) -> ProviderSearchResult:
        if self.status is AcquisitionStatus.FAILED:
            return ProviderSearchResult(
                provider_id=self.identifier,
                provider_request_id=f"fake-{uuid4().hex}",
                original_query=request.query,
                status=AcquisitionStatus.FAILED,
                candidates=[],
                errors=self.errors or ["fake provider failure"],
                request_count=1,
            )

        candidates = self._candidates
        if candidates is None:
            candidates = [
                ProviderSourceCandidate(
                    canonical_locator=f"https://example.com/research/{_slug(request.query)}",
                    title=f"Fake result for {request.query}",
                    publisher="Example Research",
                    retrieved_at=utc_now(),
                    snippet="Provider-returned snippet for discovery audit only.",
                    provider_rank=1,
                    provider_candidate_id="fake-1",
                    source_type=SourceType.WEB_PAGE,
                    provider_metadata={"provider": "fake"},
                )
            ]

        return ProviderSearchResult(
            provider_id=self.identifier,
            provider_request_id=f"fake-{uuid4().hex}",
            original_query=request.query,
            status=self.status,
            candidates=candidates[: request.result_limit],
            warnings=self.warnings,
            errors=self.errors,
            request_count=1,
        )


class BraveSearchProvider:
    """Small HTTP adapter for Brave Search API source discovery."""

    identifier = "brave"
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, settings: Settings) -> None:
        if settings.brave_search_api_key is None:
            raise AcquisitionConfigurationError("DARWIN_BRAVE_SEARCH_API_KEY is required")
        self.api_key = settings.brave_search_api_key.get_secret_value()
        self.timeout_seconds = settings.external_search_timeout_seconds
        self.max_retries = settings.external_search_max_retries
        self.user_agent = settings.external_search_user_agent

    def search(self, request: AcquisitionRequest) -> ProviderSearchResult:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": self._provider_query(request),
            "count": min(request.result_limit, 20),
        }
        attempts = 0
        last_error: str | None = None

        for attempt in range(self.max_retries + 1):
            attempts = attempt
            try:
                response = httpx.get(
                    self.endpoint,
                    params=params,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                return self._parse_response(request, response, payload, attempts)
            except httpx.TimeoutException as exc:
                last_error = "provider request timed out"
                if attempt >= self.max_retries:
                    raise AcquisitionProviderTimeout(last_error) from exc
            except httpx.HTTPStatusError as exc:
                last_error = f"provider returned HTTP {exc.response.status_code}"
                if exc.response.status_code < 500 or attempt >= self.max_retries:
                    raise AcquisitionProviderError(last_error) from exc
            except (httpx.HTTPError, ValueError) as exc:
                last_error = "provider request failed"
                if attempt >= self.max_retries:
                    raise AcquisitionProviderError(last_error) from exc

        raise AcquisitionProviderError(last_error or "provider request failed")

    def _parse_response(
        self,
        request: AcquisitionRequest,
        response: httpx.Response,
        payload: dict[str, Any],
        retry_attempts: int,
    ) -> ProviderSearchResult:
        web_results = payload.get("web", {}).get("results", [])
        candidates: list[ProviderSourceCandidate] = []
        for rank, item in enumerate(web_results[: request.result_limit], start=1):
            url = item.get("url")
            if not url:
                continue
            candidates.append(
                ProviderSourceCandidate(
                    canonical_locator=url,
                    title=item.get("title"),
                    publisher=item.get("profile", {}).get("name"),
                    retrieved_at=datetime.now(UTC),
                    snippet=item.get("description"),
                    provider_rank=rank,
                    provider_candidate_id=item.get("result_id") or item.get("id"),
                    source_type=SourceType.WEB_PAGE,
                    provider_metadata={
                        "language": item.get("language"),
                        "family_friendly": item.get("family_friendly"),
                    },
                )
            )

        return ProviderSearchResult(
            provider_id=self.identifier,
            provider_request_id=response.headers.get("x-request-id"),
            original_query=request.query,
            executed_at=utc_now(),
            status=AcquisitionStatus.SUCCESS,
            candidates=candidates,
            retry_attempts=retry_attempts,
            request_count=1 + retry_attempts,
            rate_limit_metadata=self._rate_limit_metadata(response.headers),
            provider_metadata={"submitted_query": self._provider_query(request)},
        )

    def _provider_query(self, request: AcquisitionRequest) -> str:
        if not request.domain_constraints:
            return request.query
        domain_clause = " ".join(f"site:{domain}" for domain in request.domain_constraints)
        return f"{request.query} {domain_clause}"

    def _rate_limit_metadata(self, headers: httpx.Headers) -> dict[str, str]:
        return {
            key: value
            for key, value in headers.items()
            if key.lower().startswith("x-ratelimit")
            or key.lower() in {"retry-after", "ratelimit-limit", "ratelimit-remaining"}
        }


def build_provider(settings: Settings) -> ResearchProvider:
    """Build the configured provider without exposing credentials to callers."""

    if settings.external_search_provider == "brave":
        return BraveSearchProvider(settings)
    return FakeResearchProvider()


def _slug(value: str) -> str:
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in cleaned.split("-") if part)[:80] or "query"
