"""Hash helpers for source content identity."""

from __future__ import annotations

import hashlib


def sha256_text(value: str) -> str:
    """Return a SHA-256 fingerprint for UTF-8 text."""

    return sha256_bytes(value.encode("utf-8"))


def sha256_bytes(value: bytes) -> str:
    """Return a SHA-256 fingerprint for bytes."""

    return f"sha256:{hashlib.sha256(value).hexdigest()}"
