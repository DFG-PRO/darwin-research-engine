"""Deterministic source candidate normalization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from darwin.acquisition.schemas import ProviderSourceCandidate
from darwin.db.models import SourceType, utc_now

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "msclkid"}
SECRET_KEY_PARTS = ("secret", "token", "api_key", "apikey", "password", "credential")


@dataclass(frozen=True)
class NormalizedSourceCandidate:
    """Normalized candidate values used for audit and conservative deduplication."""

    canonical_locator: str
    normalized_locator: str
    deduplication_key: str
    publisher: str | None
    normalized_domain: str | None
    retrieved_at: datetime
    source_type: SourceType | None
    provider_metadata: dict[str, Any]


def normalize_candidate(candidate: ProviderSourceCandidate) -> NormalizedSourceCandidate:
    """Return deterministic normalized values without inventing unknown metadata."""

    normalized_locator, normalized_domain = normalize_locator(candidate.canonical_locator)
    source_type = candidate.source_type or infer_source_type(normalized_locator)
    publisher = normalize_publisher(candidate.publisher, normalized_domain)

    return NormalizedSourceCandidate(
        canonical_locator=candidate.canonical_locator.strip(),
        normalized_locator=normalized_locator,
        deduplication_key=f"locator:{normalized_locator}",
        publisher=publisher,
        normalized_domain=normalized_domain,
        retrieved_at=candidate.retrieved_at or utc_now(),
        source_type=source_type,
        provider_metadata=sanitize_metadata(candidate.provider_metadata),
    )


def normalize_locator(locator: str) -> tuple[str, str | None]:
    """Normalize obvious URL variance while preserving the locator's meaning."""

    stripped = locator.strip()
    parts = urlsplit(stripped)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return stripped, None

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    hostname = parts.hostname.lower() if parts.hostname else None
    domain = hostname[4:] if hostname and hostname.startswith("www.") else hostname

    path = quote(parts.path or "/", safe="/:%")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking_query_key(key)
    ]
    query = urlencode(sorted(query_pairs), doseq=True)

    return urlunsplit((scheme, netloc, path, query, "")), domain


def infer_source_type(normalized_locator: str) -> SourceType | None:
    """Infer only source types that are deterministic from the locator itself."""

    parts = urlsplit(normalized_locator)
    if parts.scheme.lower() in {"http", "https"} and parts.netloc:
        return SourceType.WEB_PAGE
    return None


def normalize_publisher(publisher: str | None, normalized_domain: str | None) -> str | None:
    """Normalize publisher/domain only when a value is supplied or safely derivable."""

    if publisher is not None:
        normalized = " ".join(publisher.strip().split())
        return normalized or None
    return normalized_domain


def sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Redact secret-shaped metadata keys before persistence or logging."""

    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        key_text = str(key)
        if _is_secret_key(key_text):
            sanitized[key_text] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key_text] = sanitize_metadata(value)
        elif isinstance(value, list):
            sanitized[key_text] = [
                sanitize_metadata(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            sanitized[key_text] = value
    return sanitized


def _is_tracking_query_key(key: str) -> bool:
    normalized = key.lower()
    return normalized in TRACKING_QUERY_KEYS or normalized.startswith(TRACKING_QUERY_PREFIXES)


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SECRET_KEY_PARTS)
